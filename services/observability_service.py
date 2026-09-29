"""LangSmith Observability & Production Tracing Service.

Provides:
- Non-blocking distributed tracing with graceful offline/demo fallback
- Recursive secret scrubbing & PII sanitization for all trace payloads
- Real-time token usage, duration, and model cost attribution
- Hierarchical run trees (Workflow -> Guardrail / Agents -> MCP Tools -> Providers)
- Dedicated telemetry tracking for LangGraph nodes, RAG, Web Search, Dynamic Replanning, and HITL
"""

from __future__ import annotations

import logging
import os
import re
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

from config.settings import get_settings
from guardrails.security import SecretRedactor

logger = logging.getLogger("travel_platform.observability")

# Known model token pricing per 1,000,000 tokens (USD)
MODEL_PRICING_PER_1M = {
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "text-embedding-3-small": {"input": 0.02, "output": 0.00},
    "text-embedding-3-large": {"input": 0.13, "output": 0.00},
}


class TraceSanitizer:
    """Centralized sanitization utility redacting secrets and sensitive information from traces."""

    SENSITIVE_FIELD_NAMES = {
        "api_key", "apikey", "secret", "password", "token", "access_token",
        "service_role_key", "service_key", "supabase_key", "anon_key",
        "authorization", "auth", "private_key", "cookie", "payment",
        "credit_card", "card_number", "cvv", "credential", "passwd",
        "bearer", "refresh_token", "secret_key", "session_secret",
    }

    URL_SECRET_PATTERN = re.compile(r"([?&](?:api[_-]?key|token|auth|key|secret)=)[^&]+", re.IGNORECASE)
    BEARER_PATTERN = re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE)

    @classmethod
    def sanitize(cls, data: Any) -> Any:
        """Recursively scrub secrets from dictionaries, lists, strings, and tuples."""
        if data is None:
            return None

        if isinstance(data, (int, float, bool)):
            return data

        from enum import Enum
        if isinstance(data, Enum):
            return data.value

        if isinstance(data, str):
            # Sanitize Bearer tokens
            data = cls.BEARER_PATTERN.sub(r"\1[REDACTED_TOKEN]", data)
            # Sanitize URL queries if text resembles a URL
            if "http://" in data or "https://" in data:
                data = cls.URL_SECRET_PATTERN.sub(r"\1[REDACTED]", data)
            return SecretRedactor.redact_text(data)

        if isinstance(data, dict):
            sanitized_dict = {}
            for k, v in data.items():
                k_str = str(k).lower()
                if any(sensitive in k_str for sensitive in cls.SENSITIVE_FIELD_NAMES):
                    sanitized_dict[k] = "[REDACTED_SECRET]"
                else:
                    sanitized_dict[k] = cls.sanitize(v)
            return sanitized_dict

        if isinstance(data, list):
            return [cls.sanitize(item) for item in data]

        if isinstance(data, tuple):
            return tuple(cls.sanitize(item) for item in data)

        if isinstance(data, set):
            return {cls.sanitize(item) for item in data}

        # For Pydantic models or objects with dict conversion
        if hasattr(data, "model_dump"):
            return cls.sanitize(data.model_dump())
        if hasattr(data, "__dict__"):
            return cls.sanitize(vars(data))

        return str(data)


class WorkflowTelemetryTracker:
    """Aggregates metrics, token counts, costs, and span trees for a single workflow run."""

    def __init__(
        self,
        workflow_run_id: str,
        trip_id: Optional[str] = None,
        user_id: Optional[str] = None,
        is_demo: bool = True,
        root_run_tree: Optional[Any] = None,
    ):
        self.workflow_run_id = workflow_run_id
        self.trip_id = trip_id
        self.user_id = user_id
        self.is_demo = is_demo
        self.root_run_tree = root_run_tree
        self.status = "RUNNING"
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.total_duration_ms: float = 0.0

        # Operation counts
        self.total_operations: int = 0
        self.model_calls: int = 0
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.total_tokens: int = 0
        self.estimated_cost: Optional[float] = 0.0  # None when unknown
        self.mcp_calls: int = 0
        self.search_calls: int = 0
        self.rag_calls: int = 0
        self.retries: int = 0
        self.cache_hits: int = 0
        self.cache_misses: int = 0

        # Detailed breakdown spans and events
        self.spans: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        self.retry_events: List[Dict[str, Any]] = []

        # LangSmith integration
        self.langsmith_run_id: Optional[str] = None
        self.langsmith_url: Optional[str] = None

    def finish(self, status: str = "SUCCESS") -> None:
        """Mark workflow completion and compute total elapsed duration."""
        self.end_time = time.time()
        self.total_duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        self.status = status

        if self.root_run_tree:
            try:
                self.root_run_tree.end(outputs={
                    "status": self.status,
                    "duration_ms": self.total_duration_ms,
                    "total_operations": self.total_operations,
                    "total_tokens": self.total_tokens,
                })
                self.root_run_tree.patch()
            except Exception as e:
                logger.debug(f"[WorkflowTelemetryTracker] Non-blocking root run tree patch error: {e}")

    def add_span(
        self,
        span_id: str,
        name: str,
        span_type: str,
        duration_ms: float,
        status: str = "SUCCESS",
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """Append an observable child execution span and mirror to LangSmith if active."""
        self.total_operations += 1
        safe_meta = TraceSanitizer.sanitize(metadata or {})
        safe_error = TraceSanitizer.sanitize(error) if error else None

        span_data = {
            "span_id": span_id,
            "name": name,
            "type": span_type,
            "duration_ms": round(duration_ms, 2),
            "status": status,
            "metadata": safe_meta,
            "error": safe_error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.spans.append(span_data)

        # Mirror child span to LangSmith RunTree if available
        if self.root_run_tree:
            try:
                run_type_map = {
                    "tool": "tool",
                    "retriever": "retriever",
                    "llm": "llm",
                    "agent": "chain",
                    "chain": "chain",
                    "engine": "chain",
                    "approval": "chain",
                }
                child = self.root_run_tree.create_child(
                    name=name,
                    run_type=run_type_map.get(span_type, "chain"),
                    inputs=safe_meta,
                    extra={"metadata": safe_meta},
                )
                if safe_error:
                    child.end(error=safe_error)
                else:
                    child.end(outputs={"status": status, "duration_ms": round(duration_ms, 2)})
                child.post()
            except Exception as e:
                logger.debug(f"[WorkflowTelemetryTracker] Non-blocking child span post error: {e}")

    def record_retry(
        self,
        reason: str,
        attempt: int,
        component: str,
        delay_ms: float = 0.0,
    ) -> None:
        """Track retry events to prevent and observe retry loops."""
        self.retries += 1
        retry_record = {
            "attempt": attempt,
            "reason": TraceSanitizer.sanitize(reason),
            "component": component,
            "delay_ms": delay_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.retry_events.append(retry_record)

    def record_error(
        self,
        error_type: str,
        safe_message: str,
        component: str,
        node: Optional[str] = None,
        tool: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> None:
        """Capture structured, sanitized error telemetry."""
        err_entry = {
            "error_type": error_type,
            "message": TraceSanitizer.sanitize(safe_message),
            "component": component,
            "node": node,
            "tool": tool,
            "provider": provider,
            "workflow_run_id": self.workflow_run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.errors.append(err_entry)

    def record_model_usage(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Record model token expenditure and compute estimated cost if pricing known."""
        self.model_calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens += (input_tokens + output_tokens)

        # Cost computation
        pricing = MODEL_PRICING_PER_1M.get(model_name.lower())
        if pricing and self.estimated_cost is not None:
            in_cost = (input_tokens / 1_000_000.0) * pricing["input"]
            out_cost = (output_tokens / 1_000_000.0) * pricing["output"]
            self.estimated_cost += round(in_cost + out_cost, 6)
        elif not self.is_demo:
            # Live run with unknown model -> mark cost unavailable rather than fabricating
            self.estimated_cost = None

    def to_summary_dict(self) -> Dict[str, Any]:
        """Generate a sanitized summary for UI rendering and telemetry logs."""
        cost_str = f"${self.estimated_cost:.4f}" if self.estimated_cost is not None else "UNKNOWN"
        return {
            "workflow_run_id": self.workflow_run_id,
            "trip_id": self.trip_id,
            "user_id": self.user_id,
            "status": self.status,
            "duration_ms": self.total_duration_ms,
            "duration_seconds": round(self.total_duration_ms / 1000.0, 2),
            "total_operations": self.total_operations,
            "model_calls": self.model_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost": cost_str,
            "mcp_calls": self.mcp_calls,
            "search_calls": self.search_calls,
            "rag_calls": self.rag_calls,
            "retries": self.retries,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "is_demo": self.is_demo,
            "langsmith_url": self.langsmith_url or "Tracing unavailable",
            "spans_count": len(self.spans),
            "errors_count": len(self.errors),
            "retry_events_count": len(self.retry_events),
        }


class ObservabilityService:
    """Production LangSmith observability coordinator with strict non-blocking fallback."""

    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[Any] = None
        self._tracing_enabled: bool = False
        self._active_trackers: Dict[str, WorkflowTelemetryTracker] = {}
        self._latest_tracker: Optional[WorkflowTelemetryTracker] = None
        self._init_langsmith_client()

    def _init_langsmith_client(self) -> None:
        """Initialize LangSmith client and environment variables if enabled."""
        if not self.settings.langsmith_tracing:
            self._tracing_enabled = False
            return

        api_key = self.settings.langsmith_api_key
        if not api_key:
            logger.warning("[ObservabilityService] langsmith_tracing=True but no API key configured. Running in local fallback.")
            self._tracing_enabled = False
            return

        raw_key = api_key.get_secret_value()
        try:
            # Set standard LangChain / LangSmith environment variables
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = raw_key
            os.environ["LANGCHAIN_PROJECT"] = self.settings.langsmith_project
            os.environ["LANGCHAIN_ENDPOINT"] = self.settings.langsmith_endpoint

            from langsmith import Client
            self._client = Client(
                api_key=raw_key,
                api_url=self.settings.langsmith_endpoint,
            )
            self._tracing_enabled = True
            logger.info(f"[ObservabilityService] LangSmith tracing active for project '{self.settings.langsmith_project}'")
        except Exception as e:
            logger.warning(f"[ObservabilityService] Failed to initialize LangSmith client: {str(e)}. Non-blocking fallback active.")
            self._client = None
            self._tracing_enabled = False

    @property
    def is_tracing_enabled(self) -> bool:
        """Check whether LangSmith distributed tracing is operational."""
        return self._tracing_enabled

    def get_latest_tracker(self) -> Optional[WorkflowTelemetryTracker]:
        """Fetch the most recently created or active workflow tracker."""
        return self._latest_tracker

    def create_workflow_tracker(
        self,
        trip_id: Optional[str] = None,
        user_id: Optional[str] = None,
        workflow_run_id: Optional[str] = None,
        is_demo: bool = True,
    ) -> WorkflowTelemetryTracker:
        """Create a new WorkflowTelemetryTracker instance with optional LangSmith RunTree."""
        run_id = workflow_run_id or str(uuid.uuid4())
        root_run_tree = None
        langsmith_url = None

        # Setup LangSmith run tree if enabled
        if self._tracing_enabled and self._client:
            try:
                from langsmith.run_trees import RunTree
                root_run_tree = RunTree(
                    name="Travel Planning Workflow",
                    run_type="chain",
                    id=run_id,
                    project_name=self.settings.langsmith_project,
                    inputs=TraceSanitizer.sanitize({
                        "trip_id": trip_id,
                        "user_id": user_id,
                        "is_demo": is_demo,
                    }),
                    extra={"metadata": {"workflow_run_id": run_id, "trip_id": trip_id}},
                )
                root_run_tree.post()
                langsmith_url = f"https://smith.langchain.com/o/default/projects/p/{self.settings.langsmith_project}/r/{root_run_tree.id}"
            except Exception as exc:
                logger.warning(f"[ObservabilityService] Failed to post root run to LangSmith: {str(exc)}")
                root_run_tree = None
                langsmith_url = "Tracing unavailable"
        else:
            langsmith_url = "Tracing unavailable"

        tracker = WorkflowTelemetryTracker(
            workflow_run_id=run_id,
            trip_id=trip_id,
            user_id=user_id,
            is_demo=is_demo,
            root_run_tree=root_run_tree,
        )
        tracker.langsmith_run_id = str(root_run_tree.id) if root_run_tree else None
        tracker.langsmith_url = langsmith_url

        self._active_trackers[run_id] = tracker
        self._latest_tracker = tracker
        return tracker

    def get_tracker(self, workflow_run_id: str) -> Optional[WorkflowTelemetryTracker]:
        """Fetch active tracker by workflow run ID."""
        return self._active_trackers.get(workflow_run_id)

    @contextmanager
    def trace_span(
        self,
        name: str,
        span_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        tracker: Optional[WorkflowTelemetryTracker] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Context manager to trace execution of a node, tool, or calculation."""
        t = tracker or self.get_latest_tracker()
        span_id = str(uuid.uuid4())
        start = time.time()
        span_context: Dict[str, Any] = {
            "span_id": span_id,
            "name": name,
            "type": span_type,
            "status": "SUCCESS",
            "metadata": metadata or {},
            "error": None,
        }

        try:
            yield span_context
        except Exception as e:
            span_context["status"] = "FAILED"
            span_context["error"] = str(e)
            if t:
                t.record_error(
                    error_type=type(e).__name__,
                    safe_message=str(e),
                    component=name,
                )
            raise
        finally:
            duration_ms = (time.time() - start) * 1000
            if t:
                t.add_span(
                    span_id=span_id,
                    name=name,
                    span_type=span_type,
                    duration_ms=duration_ms,
                    status=span_context["status"],
                    metadata=span_context["metadata"],
                    error=span_context.get("error"),
                )

    def trace_mcp_tool(
        self,
        tool_name: str,
        agent_name: str = "mcp",
        arguments: Optional[Dict[str, Any]] = None,
        duration_ms: float = 0.0,
        success: bool = True,
        provider: Optional[str] = None,
        retries: int = 0,
        cache_hit: bool = False,
        error: Optional[str] = None,
        tracker: Optional[WorkflowTelemetryTracker] = None,
    ) -> None:
        """Record an MCP tool invocation trace."""
        t = tracker or self.get_latest_tracker()
        if t:
            t.mcp_calls += 1
            if cache_hit:
                t.cache_hits += 1
            else:
                t.cache_misses += 1
            if retries > 0:
                t.retries += retries

            status = "SUCCESS" if success else "FAILED"
            t.add_span(
                span_id=str(uuid.uuid4()),
                name=f"MCP: {tool_name}",
                span_type="tool",
                duration_ms=duration_ms,
                status=status,
                metadata={
                    "tool_name": tool_name,
                    "agent_name": agent_name,
                    "provider": provider or ("demo" if t.is_demo else "live"),
                    "arguments": TraceSanitizer.sanitize(arguments or {}),
                    "retries": retries,
                    "cache_hit": cache_hit,
                },
                error=error,
            )

    def trace_rag_retrieval(
        self,
        query: str,
        destination: Optional[str] = None,
        retrieved_count: int = 0,
        source_ids: Optional[List[str]] = None,
        top_score: float = 0.0,
        duration_ms: float = 0.0,
        similarity_threshold: Optional[float] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
        mode: str = "DEMO",
        tracker: Optional[WorkflowTelemetryTracker] = None,
    ) -> None:
        """Record RAG knowledge retrieval telemetry."""
        t = tracker or self.get_latest_tracker()
        if t:
            t.rag_calls += 1
            t.add_span(
                span_id=str(uuid.uuid4()),
                name="RAG Knowledge Retrieval",
                span_type="retriever",
                duration_ms=duration_ms,
                status="SUCCESS",
                metadata={
                    "query": TraceSanitizer.sanitize(query),
                    "destination": destination,
                    "retrieved_count": retrieved_count,
                    "source_ids": source_ids or [],
                    "similarity_threshold": similarity_threshold,
                    "metadata_filters": TraceSanitizer.sanitize(metadata_filters or {}),
                    "top_score": round(top_score, 3),
                    "mode": mode,
                },
            )

    def trace_web_search(
        self,
        query: str,
        provider: str = "Search Provider",
        result_count: int = 0,
        duration_ms: float = 0.0,
        recency: Optional[str] = None,
        domains: Optional[List[str]] = None,
        status: str = "SUCCESS",
        error: Optional[str] = None,
        tracker: Optional[WorkflowTelemetryTracker] = None,
    ) -> None:
        """Record Web Search telemetry."""
        t = tracker or self.get_latest_tracker()
        if t:
            t.search_calls += 1
            t.add_span(
                span_id=str(uuid.uuid4()),
                name=f"Web Search: {provider}",
                span_type="tool",
                duration_ms=duration_ms,
                status=status,
                metadata={
                    "query": TraceSanitizer.sanitize(query),
                    "provider": provider,
                    "result_count": result_count,
                    "recency": recency,
                    "domains": domains or [],
                },
                error=error,
            )

    def trace_replanning_event(
        self,
        event_type: str,
        reason: str = "",
        affected_nodes: Optional[List[str]] = None,
        reused_nodes: Optional[List[str]] = None,
        rerun_nodes: Optional[List[str]] = None,
        duration_ms: float = 0.0,
        status: str = "SUCCESS",
        tracker: Optional[WorkflowTelemetryTracker] = None,
    ) -> None:
        """Record Dynamic Replanning impact analysis and selective execution trace."""
        t = tracker or self.get_latest_tracker()
        if t:
            t.add_span(
                span_id=str(uuid.uuid4()),
                name=f"Dynamic Replan: {event_type}",
                span_type="chain",
                duration_ms=duration_ms,
                status=status,
                metadata={
                    "event_type": event_type,
                    "reason": TraceSanitizer.sanitize(reason),
                    "affected_nodes": affected_nodes or [],
                    "reused_nodes": reused_nodes or [],
                    "rerun_nodes": rerun_nodes or [],
                },
            )

    def trace_hitl_action(
        self,
        proposal_id: str,
        action_type: str,
        risk_level: str = "HIGH",
        status: str = "PENDING",
        approval_id: Optional[str] = None,
        duration_ms: float = 0.0,
        waiting_duration_sec: float = 0.0,
        confirmation_code: Optional[str] = None,
        error: Optional[str] = None,
        tracker: Optional[WorkflowTelemetryTracker] = None,
    ) -> None:
        """Record Human-in-the-Loop approval/execution lifecycle event."""
        t = tracker or self.get_latest_tracker()
        if t:
            t.add_span(
                span_id=str(uuid.uuid4()),
                name=f"HITL Action: {action_type}",
                span_type="approval",
                duration_ms=duration_ms,
                status=status,
                metadata={
                    "proposal_id": proposal_id,
                    "approval_id": approval_id,
                    "action_type": action_type,
                    "risk_level": risk_level,
                    "waiting_duration_sec": waiting_duration_sec,
                    "confirmation_code": confirmation_code,
                },
                error=error,
            )


# Global singleton instance
observability_service = ObservabilityService()
