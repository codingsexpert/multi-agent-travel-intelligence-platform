"""Centralized Intelligent Cache and Duplicate Call Prevention Engine.

Provides:
- Configurable domain-specific TTLs (currency, weather, places, web search, flights, hotels, RAG)
- Deterministic normalized request fingerprinting (SHA-256 hashing excluding secrets)
- Strict non-caching of transactional operations (bookings, payments, cancellations, approvals)
- Performance and efficiency telemetry: cache hits, misses, duplicate calls prevented, estimated savings
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple

from config.settings import Settings, get_settings

logger = logging.getLogger("travel_platform.cache")

SENSITIVE_PARAM_KEYS = {
    "api_key", "apikey", "secret", "password", "token", "access_token",
    "authorization", "auth", "private_key", "cookie", "payment",
    "card_number", "cvv", "credential", "bearer",
}

# Transactional operations that MUST NEVER be cached
TRANSACTIONAL_OPERATIONS = {
    "book_flight",
    "book_hotel",
    "purchase_activity",
    "cancel_booking",
    "cancel_flight",
    "process_payment",
    "authorize_payment",
    "decide_approval",
    "execute_proposal",
    "approve_action",
    "approve",
    "approval",
    "booking",
    "payment",
    "cancellation",
}


class IntelligentCache:
    """Thread-safe multi-domain intelligent cache with strict transactional protection."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._lock = threading.Lock()
        self._store: Dict[str, Tuple[Any, float]] = {}  # key -> (data, expire_timestamp)
        self._hits: int = 0
        self._misses: int = 0
        self._duplicates_prevented: int = 0
        self._tokens_saved: int = 0
        self._cost_saved: float = 0.0

    @staticmethod
    def is_transactional(domain: str, operation: str) -> bool:
        """Verify whether an operation is transactional and forbidden from being cached."""
        target = f"{domain.lower()}_{operation.lower()}"
        return any(tx_term in target for tx_term in TRANSACTIONAL_OPERATIONS)

    def get_ttl_for_domain(self, domain: str) -> int:
        """Resolve configured TTL in seconds for a specific operational domain."""
        dom = domain.lower()
        if "currency" in dom or "fx" in dom:
            return self.settings.cache_ttl_currency
        elif "weather" in dom:
            return self.settings.cache_ttl_weather
        elif "place" in dom or "map" in dom:
            return self.settings.cache_ttl_places
        elif "search" in dom or "web" in dom:
            return self.settings.cache_ttl_search
        elif "flight" in dom or "hotel" in dom:
            return self.settings.cache_ttl_flight_hotel
        elif "rag" in dom:
            return self.settings.cache_ttl_rag
        return 600  # Default 10 minutes

    def generate_fingerprint(
        self,
        domain: str,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> str:
        # Normalize data structure for stable serialization and strip sensitive parameters
        def _normalize(val: Any) -> Any:
            if isinstance(val, dict):
                return {
                    str(k).lower(): _normalize(v)
                    for k, v in sorted(val.items())
                    if not any(s in str(k).lower() for s in SENSITIVE_PARAM_KEYS)
                }
            elif isinstance(val, list):
                return [_normalize(i) for i in val]
            elif isinstance(val, str):
                return val.strip().lower()
            return val

        normalized = _normalize(params or {})
        try:
            serialized = json.dumps(normalized, sort_keys=True, default=str)
        except Exception:
            serialized = str(sorted(str(normalized)))

        hash_digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
        return f"{domain.lower()}:{operation.lower()}:{hash_digest}"

    def get(
        self,
        domain: str,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None,
    ) -> Optional[Any]:
        """Retrieve cached result if valid and not expired. Returns None on miss or transactional ops."""
        if self.is_transactional(domain, operation):
            logger.debug(f"[IntelligentCache] Transactional operation '{operation}' will not be cached.")
            return None

        key = self.generate_fingerprint(domain, operation, params)
        now = time.time()

        with self._lock:
            entry = self._store.get(key)
            if not entry:
                self._misses += 1
                return None

            data, expire_at = entry
            if now > expire_at:
                del self._store[key]
                self._misses += 1
                return None

            # Cache hit: record efficiency metrics
            self._hits += 1
            self._duplicates_prevented += 1

            # Estimate savings
            est_tokens = 450 if "llm" in domain or "extract" in operation else 50
            est_cost = 0.002 if "llm" in domain else 0.0005
            self._tokens_saved += est_tokens
            self._cost_saved += est_cost

            # Register in centralized cost tracker if workflow_id provided
            if workflow_id:
                from utils.cost import cost_tracker
                cost_tracker.record_savings(
                    workflow_id=workflow_id,
                    tokens_saved=est_tokens,
                    cost_saved=est_cost,
                    operations_avoided=1,
                    reason=f"cache_hit_{domain}_{operation}",
                )

            logger.info(f"[IntelligentCache] Cache HIT for key '{key}' ({domain}:{operation})")
            return data

    def set(
        self,
        domain: str,
        operation: str,
        params: Optional[Dict[str, Any]],
        value: Any,
        ttl_seconds: Optional[int] = None,
        custom_ttl_seconds: Optional[int] = None,
    ) -> bool:
        """Store result with TTL. Strictly rejects transactional operations. Returns True if cached."""
        if self.is_transactional(domain, operation):
            return False

        if value is None:
            return False

        ttl_override = custom_ttl_seconds if custom_ttl_seconds is not None else ttl_seconds
        effective_ttl = ttl_override if ttl_override is not None else self.get_ttl_for_domain(domain)
        if effective_ttl <= 0:
            return False

        key = self.generate_fingerprint(domain, operation, params)
        expire_at = time.time() + effective_ttl

        with self._lock:
            self._store[key] = (value, expire_at)
            # Periodic cleanup if cache size exceeds ceiling
            if len(self._store) > 1000:
                self._cleanup_expired()

        return True

    def _cleanup_expired(self) -> None:
        """Evict stale items from cache store."""
        now = time.time()
        expired_keys = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired_keys:
            self._store.pop(k, None)

    def clear(self) -> None:
        """Flush all cache entries and reset counters."""
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0
            self._duplicates_prevented = 0
            self._tokens_saved = 0
            self._cost_saved = 0.0

    def get_stats(self) -> Dict[str, Any]:
        """Return cache telemetry and optimization impact."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = round((self._hits / total_requests) * 100, 1) if total_requests > 0 else 0.0
            return {
                "active_entries": len(self._store),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_percentage": hit_rate,
                "duplicates_prevented": self._duplicates_prevented,
                "estimated_tokens_saved": self._tokens_saved,
                "estimated_cost_saved": round(self._cost_saved, 4),
            }


# Global singleton instance
intelligent_cache = IntelligentCache()
