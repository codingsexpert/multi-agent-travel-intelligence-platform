"""Thread-safe in-memory TTL cache for external provider responses."""

import time
import json
import threading
from typing import Any, Optional, Dict, Tuple
from utils.logger import logger


class ProviderCache:
    """Thread-safe in-memory cache with per-item TTL expiration."""

    _lock = threading.Lock()
    _cache: Dict[str, Tuple[Any, float]] = {}  # key -> (data, expire_timestamp)
    _hits: int = 0
    _misses: int = 0

    def __init__(self, default_ttl_seconds: int = 300):
        self.default_ttl_seconds = default_ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        return self.__class__.get(key)

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        self.__class__.set(key, value, ttl_seconds=ttl_seconds or self.default_ttl_seconds)

    @classmethod
    def generate_key(cls, provider: str, tool_name: str, params: Dict[str, Any]) -> str:
        """Create a deterministic cache key from provider, tool name, and arguments."""
        try:
            # Sort keys to ensure deterministic serialization
            serialized_params = json.dumps(params, sort_keys=True, default=str)
        except Exception:
            serialized_params = str(sorted(params.items()))
        return f"{provider}:{tool_name}:{serialized_params}"

    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        """Retrieve cached value if present and not expired."""
        with cls._lock:
            entry = cls._cache.get(key)
            if not entry:
                cls._misses += 1
                return None

            data, expire_at = entry
            if time.time() > expire_at:
                del cls._cache[key]
                cls._misses += 1
                return None

            cls._hits += 1
            return data

    @classmethod
    def set(cls, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Store value with TTL in seconds."""
        if ttl_seconds <= 0:
            return

        with cls._lock:
            expire_at = time.time() + ttl_seconds
            cls._cache[key] = (value, expire_at)

            # Evict expired entries if cache grows large
            if len(cls._cache) > 500:
                cls._cleanup_expired()

    @classmethod
    def _cleanup_expired(cls) -> None:
        """Evict expired items from cache."""
        now = time.time()
        expired_keys = [k for k, (_, exp) in cls._cache.items() if now > exp]
        for k in expired_keys:
            cls._cache.pop(k, None)

    @classmethod
    def clear(cls) -> None:
        """Clear all cached entries and reset statistics."""
        with cls._lock:
            cls._cache.clear()
            cls._hits = 0
            cls._misses = 0

    @classmethod
    def get_stats(cls) -> Dict[str, int]:
        """Retrieve cache hit/miss statistics and entry count."""
        with cls._lock:
            return {
                "entries": len(cls._cache),
                "hits": cls._hits,
                "misses": cls._misses,
            }
