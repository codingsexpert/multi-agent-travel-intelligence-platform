"""Centralized Cost Tracker and Token Attribution Engine.

Provides:
- Configuration-driven per-model token pricing (input / output per 1M tokens)
- Per-workflow, per-model, and per-agent token and cost aggregation
- Unknown pricing handling (returns None / 'UNKNOWN' rather than fabricating costs)
- Workflow cost budget enforcement (halts runaway expenses safely)
- Optimization savings tracking (tokens saved, cost saved, calls avoided via caching/replanning)
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

from config.settings import Settings, get_settings

logger = logging.getLogger("travel_platform.cost")

# Default published pricing per 1,000,000 tokens (USD)
DEFAULT_MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "text-embedding-3-small": {"input": 0.02, "output": 0.00},
    "text-embedding-3-large": {"input": 0.13, "output": 0.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
}


class CostTracker:
    """Thread-safe centralized cost and token tracking manager."""

    def __init__(
        self,
        pricing_table: Optional[Dict[str, Dict[str, float]]] = None,
        settings: Optional[Settings] = None,
    ):
        self._lock = threading.RLock()
        self._settings = settings or get_settings()
        self._pricing: Dict[str, Dict[str, float]] = dict(pricing_table or DEFAULT_MODEL_PRICING)

        # In-memory tracking aggregates
        self._model_usage: Dict[str, Dict[str, Any]] = {}
        self._agent_usage: Dict[str, Dict[str, Any]] = {}
        self._workflow_usage: Dict[str, Dict[str, Any]] = {}
        self._savings: Dict[str, Dict[str, Any]] = {}

    def reset(self) -> None:
        """Reset all in-memory counters."""
        self.clear()

    def register_pricing(self, model_name: str, input_cost_per_1m: float, output_cost_per_1m: float) -> None:
        """Dynamically configure or override pricing for a model."""
        with self._lock:
            self._pricing[model_name.lower()] = {
                "input": input_cost_per_1m,
                "output": output_cost_per_1m,
            }

    def calculate_cost(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
    ) -> Optional[float]:
        """Calculate dollar cost for tokens based on configured pricing.
        
        Returns None when pricing is unconfigured (never invent fake pricing).
        """
        pricing = self._pricing.get(model_name.lower())
        if not pricing:
            return None

        in_cost = (input_tokens / 1_000_000.0) * pricing["input"]
        out_cost = (output_tokens / 1_000_000.0) * pricing["output"]
        return round(in_cost + out_cost, 6)

    def record_usage(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        agent_name: Optional[str] = None,
        workflow_id: Optional[str] = None,
        task_type: Optional[str] = None,
        latency_ms: float = 0.0,
        success: bool = True,
        is_fallback: bool = False,
    ) -> Optional[float]:
        """Record a model invocation and aggregate metrics across model, agent, and workflow."""
        total_tokens = input_tokens + output_tokens
        cost = self.calculate_cost(model_name, input_tokens, output_tokens)

        with self._lock:
            # 1. Model breakdown
            m_key = model_name.lower()
            if m_key not in self._model_usage:
                self._model_usage[m_key] = {
                    "model": model_name,
                    "calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "estimated_cost": 0.0 if cost is not None else None,
                    "total_latency_ms": 0.0,
                    "fallback_count": 0,
                    "fallbacks": 0,
                }

            m_entry = self._model_usage[m_key]
            m_entry["calls"] += 1
            if success:
                m_entry["successful_calls"] += 1
            else:
                m_entry["failed_calls"] += 1
            m_entry["input_tokens"] += input_tokens
            m_entry["output_tokens"] += output_tokens
            m_entry["total_tokens"] += total_tokens
            m_entry["total_latency_ms"] += latency_ms
            if is_fallback:
                m_entry["fallback_count"] += 1
                m_entry["fallbacks"] = m_entry["fallback_count"]

            if cost is not None and m_entry["estimated_cost"] is not None:
                m_entry["estimated_cost"] += cost
            elif cost is None:
                m_entry["estimated_cost"] = None

            # 2. Agent breakdown
            if agent_name:
                a_key = agent_name.lower()
                if a_key not in self._agent_usage:
                    self._agent_usage[a_key] = {
                        "agent": agent_name,
                        "model": model_name,
                        "calls": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0,
                        "estimated_cost": 0.0 if cost is not None else None,
                        "total_latency_ms": 0.0,
                    }
                a_entry = self._agent_usage[a_key]
                a_entry["calls"] += 1
                a_entry["input_tokens"] += input_tokens
                a_entry["output_tokens"] += output_tokens
                a_entry["total_tokens"] += total_tokens
                a_entry["total_latency_ms"] += latency_ms
                if cost is not None and a_entry["estimated_cost"] is not None:
                    a_entry["estimated_cost"] += cost
                elif cost is None:
                    a_entry["estimated_cost"] = None

            # 3. Workflow breakdown
            if workflow_id:
                if workflow_id not in self._workflow_usage:
                    self._workflow_usage[workflow_id] = {
                        "workflow_id": workflow_id,
                        "calls": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0,
                        "estimated_cost": 0.0 if cost is not None else None,
                        "total_latency_ms": 0.0,
                    }
                w_entry = self._workflow_usage[workflow_id]
                w_entry["calls"] += 1
                w_entry["input_tokens"] += input_tokens
                w_entry["output_tokens"] += output_tokens
                w_entry["total_tokens"] += total_tokens
                w_entry["total_latency_ms"] += latency_ms
                if cost is not None and w_entry["estimated_cost"] is not None:
                    w_entry["estimated_cost"] += cost
                elif cost is None:
                    w_entry["estimated_cost"] = None

        return cost

    def check_budget(
        self,
        workflow_id: Optional[str] = None,
        max_cost: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_calls: Optional[int] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Verify whether workflow remains within configured cost, token, and call ceilings.
        
        Returns (True, None) if within budget, or (False, reason) if exceeded.
        """
        cost_limit = max_cost if max_cost is not None else getattr(self._settings, "max_workflow_cost", 1.00)
        tokens_limit = max_tokens if max_tokens is not None else getattr(self._settings, "max_total_tokens", 50000)
        calls_limit = max_calls if max_calls is not None else getattr(self._settings, "max_model_calls", 10)

        with self._lock:
            if workflow_id and workflow_id in self._workflow_usage:
                calls = self._workflow_usage[workflow_id]["calls"]
                tokens = self._workflow_usage[workflow_id]["total_tokens"]
                cost = self._workflow_usage[workflow_id].get("estimated_cost")
            else:
                calls = sum(m["calls"] for m in self._model_usage.values())
                tokens = sum(m["total_tokens"] for m in self._model_usage.values())
                costs = [m["estimated_cost"] for m in self._model_usage.values() if m.get("estimated_cost") is not None]
                cost = sum(costs) if costs else 0.0

            if calls >= calls_limit:
                return False, f"Workflow model call limit reached ({calls}/{calls_limit})"

            if tokens >= tokens_limit:
                return False, f"Workflow total token limit exceeded ({tokens}/{tokens_limit})"

            if cost is not None and cost >= cost_limit:
                return False, f"Workflow cost budget exceeded (${cost:.4f}/${cost_limit:.2f})"

        return True, None

    def record_savings(
        self,
        calls_avoided: int = 1,
        tokens_saved: int = 0,
        cost_saved: float = 0.0,
        latency_ms_saved: float = 0.0,
        nodes_reused: int = 0,
        workflow_id: Optional[str] = None,
        reason: str = "cache_hit",
        operations_avoided: Optional[int] = None,
    ) -> None:
        """Record optimization efficiency metrics (tokens/cost saved via cache or replanning)."""
        ops = operations_avoided if operations_avoided is not None else calls_avoided
        w_id = workflow_id or "global"
        with self._lock:
            if w_id not in self._savings:
                self._savings[w_id] = {
                    "workflow_id": w_id,
                    "tokens_saved": 0,
                    "cost_saved": 0.0,
                    "operations_avoided": 0,
                    "latency_ms_saved": 0.0,
                    "nodes_reused": 0,
                    "reasons": [],
                }
            s = self._savings[w_id]
            s["tokens_saved"] += tokens_saved
            s["cost_saved"] += round(cost_saved, 6)
            s["operations_avoided"] += ops
            s["latency_ms_saved"] += latency_ms_saved
            s["nodes_reused"] += nodes_reused
            if reason not in s["reasons"]:
                s["reasons"].append(reason)

    def get_model_metrics(self, model_name: str) -> Dict[str, Any]:
        """Fetch metrics for a specific model."""
        with self._lock:
            data = self._model_usage.get(model_name.lower())
            if data:
                return dict(data)
            return {
                "model": model_name,
                "calls": 0,
                "fallbacks": 0,
                "fallback_count": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "estimated_cost": 0.0,
            }

    def get_workflow_summary(self, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate high-level aggregated cost & performance summary."""
        with self._lock:
            total_calls = sum(m["calls"] for m in self._model_usage.values())
            total_in = sum(m["input_tokens"] for m in self._model_usage.values())
            total_out = sum(m["output_tokens"] for m in self._model_usage.values())
            total_tokens = sum(m["total_tokens"] for m in self._model_usage.values())
            cost_vals = [m["estimated_cost"] for m in self._model_usage.values()]
            if any(c is None for c in cost_vals):
                cost_str = "UNKNOWN"
            else:
                cost_str = f"${sum(cost_vals):.4f}"

            return {
                "total_model_calls": total_calls,
                "input_tokens": total_in,
                "output_tokens": total_out,
                "total_tokens": total_tokens,
                "estimated_cost_formatted": cost_str,
                "model_breakdown": self.get_model_breakdown(),
                "agent_breakdown": self.get_agent_breakdown(),
            }

    def get_efficiency_metrics(self, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate savings & optimization efficiency metrics."""
        with self._lock:
            total_tokens_saved = sum(s["tokens_saved"] for s in self._savings.values())
            total_cost_saved = sum(s["cost_saved"] for s in self._savings.values())
            total_ops_avoided = sum(s["operations_avoided"] for s in self._savings.values())
            total_nodes_reused = sum(s.get("nodes_reused", 0) for s in self._savings.values())
            return {
                "tokens_saved": total_tokens_saved,
                "cost_saved": total_cost_saved,
                "calls_avoided": total_ops_avoided,
                "nodes_reused_during_replanning": total_nodes_reused,
            }

    def get_workflow_cost(self, workflow_id: str) -> Dict[str, Any]:
        """Fetch consolidated telemetry for a specific workflow."""
        with self._lock:
            usage = self._workflow_usage.get(workflow_id, {
                "workflow_id": workflow_id,
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "estimated_cost": 0.0,
                "total_latency_ms": 0.0,
            })
            savings = self._savings.get(workflow_id, {
                "tokens_saved": 0,
                "cost_saved": 0.0,
                "operations_avoided": 0,
                "reasons": [],
            })
            cost_val = usage.get("estimated_cost")
            cost_str = f"${cost_val:.4f}" if cost_val is not None else "UNKNOWN"
            return {
                **usage,
                "estimated_cost_display": cost_str,
                "savings": savings,
            }

    def get_model_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Return breakdown per model for UI and audit logs."""
        with self._lock:
            result = {}
            for k, v in self._model_usage.items():
                v_copy = dict(v)
                c = v_copy.get("estimated_cost")
                v_copy["estimated_cost_display"] = f"${c:.4f}" if c is not None else "UNKNOWN"
                result[k] = v_copy
            return result

    def get_agent_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Return breakdown per agent for UI and audit logs."""
        with self._lock:
            result = {}
            for k, v in self._agent_usage.items():
                v_copy = dict(v)
                c = v_copy.get("estimated_cost")
                v_copy["estimated_cost_display"] = f"${c:.4f}" if c is not None else "UNKNOWN"
                result[k] = v_copy
            return result

    def get_summary(self) -> Dict[str, Any]:
        """Generate high-level aggregated cost & performance summary."""
        with self._lock:
            total_calls = sum(m["calls"] for m in self._model_usage.values())
            total_tokens = sum(m["total_tokens"] for m in self._model_usage.values())
            total_cost_vals = [m["estimated_cost"] for m in self._model_usage.values()]

            if any(c is None for c in total_cost_vals):
                total_cost_str = "UNKNOWN"
            else:
                total_cost_str = f"${sum(total_cost_vals):.4f}"

            total_tokens_saved = sum(s["tokens_saved"] for s in self._savings.values())
            total_cost_saved = sum(s["cost_saved"] for s in self._savings.values())
            total_ops_avoided = sum(s["operations_avoided"] for s in self._savings.values())

            return {
                "total_model_calls": total_calls,
                "total_tokens": total_tokens,
                "estimated_cost": total_cost_str,
                "tokens_saved": total_tokens_saved,
                "cost_saved": f"${total_cost_saved:.4f}",
                "operations_avoided": total_ops_avoided,
                "models_tracked": len(self._model_usage),
                "agents_tracked": len(self._agent_usage),
            }

    def clear(self) -> None:
        """Reset in-memory counters (useful for unit tests)."""
        with self._lock:
            self._model_usage.clear()
            self._agent_usage.clear()
            self._workflow_usage.clear()
            self._savings.clear()


# Global singleton instance
cost_tracker = CostTracker()
