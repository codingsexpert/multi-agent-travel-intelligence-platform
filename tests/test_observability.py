"""Tests for Phase 14: LangSmith Observability & Production Tracing."""

import pytest
from unittest.mock import MagicMock, patch
from pydantic import SecretStr

from config.settings import Settings
from services.observability_service import (
    TraceSanitizer,
    WorkflowTelemetryTracker,
    ObservabilityService,
    observability_service,
)
from mcp.client import MCPClient
from rag.retriever import TravelKnowledgeRetriever, mock_knowledge_store
from models.rag import RAGRetrievalQuery
from services.replanning_service import replanning_service
from models.replanning import ChangeEvent, ChangeEventType, ChangeEventSeverity
from services.action_execution_service import action_execution_service
from repositories.approval_repository import approval_repository
from models.approval import ActionProposal, ActionRiskLevel, ApprovalStatus


# =====================================================================
# 1. LangSmith Configuration Tests
# =====================================================================

def test_langsmith_config_defaults():
    """Test default configuration when no environment variables are provided."""
    s = Settings(
        openai_api_key="mock",
        supabase_url="http://mock.supabase.co",
        supabase_anon_key="mock",
        supabase_service_role_key="mock",
    )
    assert s.langsmith_tracing is False
    assert s.langsmith_api_key is None
    assert s.langsmith_project == "travel-intelligence-platform"
    assert s.langsmith_endpoint == "https://api.smith.langchain.com"


def test_langsmith_config_aliases():
    """Test that both LANGSMITH_* and LANGCHAIN_* aliases work seamlessly."""
    s = Settings(
        LANGSMITH_TRACING="true",
        LANGSMITH_API_KEY="lsv2_pt_testkey_12345",
        LANGSMITH_PROJECT="custom-travel-prod",
        LANGSMITH_ENDPOINT="https://eu.api.smith.langchain.com",
        openai_api_key="mock",
        supabase_url="http://mock.supabase.co",
        supabase_anon_key="mock",
        supabase_service_role_key="mock",
    )
    assert s.langsmith_tracing is True
    assert s.langsmith_api_key.get_secret_value() == "lsv2_pt_testkey_12345"
    assert s.langsmith_project == "custom-travel-prod"
    assert s.langsmith_endpoint == "https://eu.api.smith.langchain.com"


# =====================================================================
# 2. Tracing Enabled / Disabled & Fallback
# =====================================================================

def test_tracing_disabled_when_flag_false():
    """ObservabilityService gracefully disables remote client when tracing is False."""
    obs = ObservabilityService()
    obs.settings = Settings(
        langsmith_tracing=False,
        openai_api_key="mock",
        supabase_url="http://mock.supabase.co",
        supabase_anon_key="mock",
        supabase_service_role_key="mock",
    )
    obs._init_langsmith_client()
    assert obs.is_tracing_enabled is False


def test_tracing_disabled_when_key_missing():
    """ObservabilityService falls back safely when tracing is enabled but key is empty."""
    obs = ObservabilityService()
    obs.settings = Settings(
        langsmith_tracing=True,
        langsmith_api_key=None,
        openai_api_key="mock",
        supabase_url="http://mock.supabase.co",
        supabase_anon_key="mock",
        supabase_service_role_key="mock",
    )
    obs._init_langsmith_client()
    assert obs.is_tracing_enabled is False


def test_tracing_enabled_with_valid_key():
    """ObservabilityService activates when both flag and key are present."""
    with patch("langsmith.Client") as mock_client:
        obs = ObservabilityService()
        obs.settings = Settings(
            langsmith_tracing=True,
            langsmith_api_key=SecretStr("lsv2_valid_key_test"),
            langsmith_project="test-project",
            openai_api_key="mock",
            supabase_url="http://mock.supabase.co",
            supabase_anon_key="mock",
            supabase_service_role_key="mock",
        )
        obs._init_langsmith_client()
        assert obs.is_tracing_enabled is True
        assert obs._client is not None


# =====================================================================
# 3. Secret Redaction & Metadata Sanitization
# =====================================================================

def test_trace_sanitizer_redacts_keys():
    """Recursively scrub sensitive keys from dictionaries."""
    dirty_data = {
        "user_id": "u-123",
        "api_key": "sk-proj-supersecret1234567890",
        "nested": {
            "password": "my_admin_password",
            "token": "bearer_987654321",
            "safe_field": "Tokyo, Japan",
        },
        "items": [
            {"card_number": "4111-2222-3333-4444", "cvv": "123"},
            {"item_name": "Flight Ticket"},
        ],
    }
    clean = TraceSanitizer.sanitize(dirty_data)
    assert clean["user_id"] == "u-123"
    assert clean["api_key"] == "[REDACTED_SECRET]"
    assert clean["nested"]["password"] == "[REDACTED_SECRET]"
    assert clean["nested"]["token"] == "[REDACTED_SECRET]"
    assert clean["nested"]["safe_field"] == "Tokyo, Japan"
    assert clean["items"][0]["card_number"] == "[REDACTED_SECRET]"
    assert clean["items"][0]["cvv"] == "[REDACTED_SECRET]"
    assert clean["items"][1]["item_name"] == "Flight Ticket"


def test_trace_sanitizer_redacts_url_params():
    """Scrub tokens and API keys embedded in URLs."""
    url = "https://api.travel.com/v1/search?query=flights&api_key=secret_12345&mode=live"
    sanitized = TraceSanitizer.sanitize(url)
    assert "secret_12345" not in sanitized
    assert "api_key=[REDACTED]" in sanitized


def test_trace_sanitizer_redacts_bearer_tokens():
    """Scrub raw Bearer authentication headers."""
    auth_header = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    sanitized = TraceSanitizer.sanitize(auth_header)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized
    assert "Bearer [REDACTED_TOKEN]" in sanitized


# =====================================================================
# 4. Token & Latency Tracking & Cost Estimation
# =====================================================================

def test_workflow_telemetry_token_and_cost():
    """Tracker accurately aggregates token usage and computes exact cost for known models."""
    tracker = WorkflowTelemetryTracker(workflow_run_id="run-test-1", is_demo=False)
    # gpt-4o pricing: $5.00 input, $15.00 output per 1M tokens
    tracker.record_model_usage(model_name="gpt-4o", input_tokens=100_000, output_tokens=20_000)
    # in: 100k / 1M * $5 = $0.50, out: 20k / 1M * $15 = $0.30 -> total = $0.80
    assert tracker.total_tokens == 120_000
    assert tracker.model_calls == 1
    assert round(tracker.estimated_cost, 2) == 0.80

    summary = tracker.to_summary_dict()
    assert summary["estimated_cost"] == "$0.8000"
    assert summary["total_tokens"] == 120_000


def test_cost_unavailable_handling():
    """If unknown model pricing is used in live mode, report UNKNOWN rather than inventing cost."""
    tracker = WorkflowTelemetryTracker(workflow_run_id="run-test-2", is_demo=False)
    tracker.record_model_usage(model_name="unreleased-custom-llm", input_tokens=50_000, output_tokens=10_000)
    assert tracker.estimated_cost is None
    summary = tracker.to_summary_dict()
    assert summary["estimated_cost"] == "UNKNOWN"


def test_tracker_latency_and_spans():
    """Spans record elapsed execution duration accurately."""
    tracker = WorkflowTelemetryTracker(workflow_run_id="run-test-3")
    tracker.add_span(
        span_id="span-1",
        name="Planner Agent",
        span_type="agent",
        duration_ms=45.2,
        status="SUCCESS",
        metadata={"destination": "Paris"},
    )
    assert tracker.total_operations == 1
    assert len(tracker.spans) == 1
    assert tracker.spans[0]["name"] == "Planner Agent"
    assert tracker.spans[0]["duration_ms"] == 45.2


# =====================================================================
# 5. Parent & Child Traces / LangSmith RunTree Mirroring
# =====================================================================

def test_parent_child_run_tree_mirroring():
    """When RunTree is present, child spans post without errors."""
    mock_root = MagicMock()
    mock_child = MagicMock()
    mock_root.create_child.return_value = mock_child

    tracker = WorkflowTelemetryTracker(
        workflow_run_id="run-root-1",
        root_run_tree=mock_root,
    )
    tracker.add_span(
        span_id="c-1",
        name="MCP: search_flights",
        span_type="tool",
        duration_ms=120.5,
        status="SUCCESS",
    )
    mock_root.create_child.assert_called_once()
    mock_child.post.assert_called_once()

    tracker.finish(status="SUCCESS")
    mock_root.patch.assert_called_once()


# =====================================================================
# 6. MCP Observability
# =====================================================================

def test_mcp_client_tracing():
    """Executing an MCP tool automatically triggers observability telemetry."""
    tracker = observability_service.create_workflow_tracker(workflow_run_id="mcp-test-run")

    result = MCPClient.call_tool(
        agent_name="flight",
        tool_name="search_flights",
        arguments={"origin": "SFO", "destination": "HND", "departure_date": "2026-10-01"},
        is_demo=True,
    )
    assert result.success is True
    assert tracker.mcp_calls >= 1

    # Verify recorded span in tracker
    matching_spans = [s for s in tracker.spans if "search_flights" in s["name"]]
    assert len(matching_spans) >= 1
    assert matching_spans[0]["type"] == "tool"
    assert matching_spans[0]["metadata"]["agent_name"] == "flight"
    assert matching_spans[0]["status"] == "SUCCESS"


# =====================================================================
# 7. RAG Observability
# =====================================================================

def test_rag_retrieval_tracing():
    """RAG queries record query, chunks, source IDs, and execution latency."""
    tracker = observability_service.create_workflow_tracker(workflow_run_id="rag-test-run")
    retriever = TravelKnowledgeRetriever()

    q = RAGRetrievalQuery(query="Best ramen in Tokyo", destination="Tokyo")
    res = retriever.retrieve(q)

    assert tracker.rag_calls >= 1
    rag_spans = [s for s in tracker.spans if s["type"] == "retriever"]
    assert len(rag_spans) >= 1
    assert rag_spans[0]["metadata"]["destination"] == "Tokyo"
    assert "query" in rag_spans[0]["metadata"]


# =====================================================================
# 8. Web Search Observability
# =====================================================================

def test_web_search_tracing():
    """Search MCP traces web search query, provider, and result count."""
    tracker = observability_service.create_workflow_tracker(workflow_run_id="search-test-run")

    observability_service.trace_web_search(
        query="Kyoto cultural events October",
        provider="Mock Search Service",
        result_count=4,
        duration_ms=15.0,
        recency="7d",
    )
    assert tracker.search_calls >= 1
    search_spans = [s for s in tracker.spans if "Web Search" in s["name"]]
    assert len(search_spans) == 1
    assert search_spans[0]["metadata"]["result_count"] == 4


# =====================================================================
# 9. Retries & Error Observability
# =====================================================================

def test_retry_observability():
    """Retry events are tracked with attempt, reason, and delay."""
    tracker = WorkflowTelemetryTracker(workflow_run_id="retry-test")
    tracker.record_retry(reason="API Rate Limit 429", attempt=1, component="Flight Adapter", delay_ms=100.0)
    tracker.record_retry(reason="API Rate Limit 429", attempt=2, component="Flight Adapter", delay_ms=200.0)

    assert tracker.retries == 2
    assert len(tracker.retry_events) == 2
    assert tracker.retry_events[0]["attempt"] == 1
    assert tracker.retry_events[1]["delay_ms"] == 200.0


def test_error_observability_safe_message():
    """Errors are captured safely without exposing sensitive data."""
    tracker = WorkflowTelemetryTracker(workflow_run_id="error-test")
    tracker.record_error(
        error_type="ProviderAuthenticationError",
        safe_message="Failed auth on endpoint https://api.hotel.com?key=supersecret123",
        component="Hotel Adapter",
        tool="search_hotels",
    )
    assert len(tracker.errors) == 1
    err = tracker.errors[0]
    assert err["error_type"] == "ProviderAuthenticationError"
    assert "supersecret123" not in err["message"]
    assert "key=[REDACTED]" in err["message"]


# =====================================================================
# 10. Dynamic Replanning & HITL Tracing
# =====================================================================

def test_dynamic_replanning_trace():
    """Dynamic replan events track affected, reused, and rerun nodes."""
    tracker = observability_service.create_workflow_tracker(workflow_run_id="replan-test")

    observability_service.trace_replanning_event(
        event_type="FLIGHT_DELAY",
        reason="Flight delayed by 5 hours",
        affected_nodes=["flight", "activity", "budget_engine"],
        reused_nodes=["hotel", "weather"],
        rerun_nodes=["flight", "activity", "budget_engine", "validator"],
        duration_ms=45.0,
        status="SUCCESS",
    )

    replan_spans = [s for s in tracker.spans if "Dynamic Replan" in s["name"]]
    assert len(replan_spans) == 1
    meta = replan_spans[0]["metadata"]
    assert meta["event_type"] == "FLIGHT_DELAY"
    assert "hotel" in meta["reused_nodes"]
    assert "flight" in meta["rerun_nodes"]


def test_hitl_action_trace():
    """Human-in-the-loop lifecycle events are traced with risk and confirmation code."""
    tracker = observability_service.create_workflow_tracker(workflow_run_id="hitl-test")

    observability_service.trace_hitl_action(
        proposal_id="prop-888",
        action_type="BOOK_FLIGHT",
        risk_level="HIGH",
        status="COMPLETED",
        duration_ms=250.0,
        confirmation_code="CONF-MOCK-12345",
    )

    hitl_spans = [s for s in tracker.spans if "HITL Action" in s["name"]]
    assert len(hitl_spans) == 1
    meta = hitl_spans[0]["metadata"]
    assert meta["proposal_id"] == "prop-888"
    assert meta["confirmation_code"] == "CONF-MOCK-12345"


# =====================================================================
# 11. Failure Isolation
# =====================================================================

def test_failure_isolation_does_not_break_app():
    """Even if LangSmith raises unexpected network/auth exceptions, operations continue seamlessly."""
    obs = ObservabilityService()
    obs._tracing_enabled = True
    obs._client = MagicMock()

    # Simulate LangSmith network/auth failure on RunTree
    with patch("langsmith.run_trees.RunTree", side_effect=Exception("LangSmith connection timeout")):
        tracker = obs.create_workflow_tracker(trip_id="trip-fail-safe", is_demo=True)
        assert tracker is not None
        assert tracker.workflow_run_id is not None
        assert tracker.langsmith_url == "Tracing unavailable"

        # Recording spans still functions in-memory
        tracker.add_span("s-1", "Planner", "agent", 10.0)
        assert tracker.total_operations == 1


# =====================================================================
# 12. End-to-End Planning Workflow Observability
# =====================================================================

def test_full_travel_planning_observability():
    """Executing full planning workflow populates workflow_telemetry in final state."""
    from services.planning_service import run_travel_planning
    final_state = run_travel_planning(
        user_request="Plan a 5-day cultural trip to Kyoto with a $3,000 budget for 2 adults",
        user_id="test-obs-user",
    )
    assert "workflow_telemetry" in final_state
    telemetry = final_state["workflow_telemetry"]
    assert telemetry["workflow_run_id"] is not None
    assert telemetry["duration_ms"] > 0
    assert telemetry["total_operations"] >= 1
    assert "spans" in telemetry
    assert len(telemetry["spans"]) >= 1

