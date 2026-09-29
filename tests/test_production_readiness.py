"""Production deployment, configuration validation, health checks, and security tests."""

from datetime import date
from pathlib import Path
import pytest
from unittest import mock
import yaml
from pydantic import SecretStr

from config.settings import Settings
from config.validator import validate_environment, ensure_startup_configuration
from services.health_service import get_health_status, get_liveness_status, get_readiness_status
from repositories.trip_repository import TripRepository
from repositories.approval_repository import ApprovalRepository
from repositories.mock_store import mock_store
from models.approval import ActionProposal, classify_action_risk, ActionRiskLevel
from models.replanning import ChangeEvent, ChangeEventType, ChangeEventSeverity
from services.planning_service import run_travel_planning
from services.replanning_service import ReplanningService
from services.action_execution_service import ActionExecutionService


def test_demo_mode_configuration_validity():
    """Verify default demo mode configuration is valid with 0 fatal errors."""
    demo_settings = Settings(demo_mode=True, app_env="development")
    result = validate_environment(demo_settings)
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert result.demo_mode is True
    assert result.environment == "DEMO"
    assert "runtime_mode" in result.provider_status
    assert result.provider_status["runtime_mode"] == "SANDBOXED_MOCK"


def test_production_mode_configuration_missing_credentials():
    """Verify production mode detects missing database and LLM credentials safely."""
    prod_missing = Settings(
        demo_mode=False,
        app_env="production",
        supabase_url=None,
        supabase_key=None,
        openai_api_key=None,
    )
    result = validate_environment(prod_missing)
    assert result.is_valid is False
    assert any("SUPABASE_URL" in err for err in result.errors)
    assert any("SUPABASE_KEY" in err for err in result.errors)
    assert any("OPENAI_API_KEY" in err for err in result.errors)
    # Check that secrets are not leaked in errors or warnings
    for err in result.errors:
        assert "eyJ" not in err
        assert "sk-" not in err


def test_production_mode_configuration_valid():
    """Verify production mode passes when valid endpoints and keys are configured."""
    prod_valid = Settings(
        demo_mode=False,
        app_env="production",
        supabase_url="https://prod-project.supabase.co",
        supabase_key=SecretStr("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy_anon_key"),
        openai_api_key=SecretStr("sk-proj-testkey1234567890"),
    )
    result = validate_environment(prod_valid)
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert result.provider_status["database"] == "CONFIGURED"
    assert result.provider_status["auth"] == "CONFIGURED"
    assert "CONFIGURED" in result.provider_status["llm"]


def test_liveness_probe():
    """Verify application liveness probe indicates running status."""
    liveness = get_liveness_status()
    assert liveness["status"] == "HEALTHY"
    assert liveness["liveness"] is True
    assert liveness["uptime_seconds"] >= 0.0
    assert "timestamp" in liveness


def test_readiness_probe():
    """Verify readiness probe evaluates readiness across dependencies."""
    demo_cfg = Settings(demo_mode=True)
    readiness = get_readiness_status(demo_cfg)
    assert readiness["status"] in ("HEALTHY", "DEGRADED")
    assert readiness["readiness"] is True
    assert "components" in readiness
    assert "application" in readiness["components"]
    assert "database" in readiness["components"]


def test_all_eight_subsystems_in_health_report():
    """Verify all 8 mandatory subsystems are tracked in the health report."""
    health = get_health_status(Settings(demo_mode=True))
    expected_subsystems = {
        "application",
        "database",
        "authentication",
        "llm",
        "mcp",
        "search",
        "rag",
        "langsmith",
    }
    assert expected_subsystems.issubset(set(health.components.keys()))
    for key in expected_subsystems:
        comp = health.components[key]
        assert comp.status in ("HEALTHY", "DEGRADED", "UNAVAILABLE", "NOT_CONFIGURED")
        assert comp.name


def test_no_secrets_in_health_report():
    """Verify health report never exposes secrets, tokens, or private keys."""
    cfg = Settings(
        demo_mode=False,
        supabase_url="https://prod-project.supabase.co",
        supabase_key=SecretStr("secret_token_12345"),
        openai_api_key=SecretStr("sk-secret-llm-key"),
    )
    health = get_health_status(cfg)
    report_json = health.model_dump_json()
    assert "secret_token_12345" not in report_json
    assert "sk-secret-llm-key" not in report_json


def test_dockerfile_and_config_exist():
    """Verify production Dockerfile and Streamlit config exist and are properly configured."""
    base_dir = Path(__file__).parent.parent
    dockerfile = base_dir / "Dockerfile"
    dockerignore = base_dir / ".dockerignore"
    st_config = base_dir / ".streamlit" / "config.toml"

    assert dockerfile.exists()
    df_content = dockerfile.read_text()
    assert "FROM python:3.11-slim" in df_content
    assert "USER appuser" in df_content  # Non-root user
    assert "HEALTHCHECK" in df_content

    assert dockerignore.exists()
    di_content = dockerignore.read_text()
    assert ".env" in di_content
    assert ".git" in di_content

    assert st_config.exists()
    st_content = st_config.read_text()
    assert "headless = true" in st_content
    assert "showErrorDetails = false" in st_content


def test_ci_workflow_valid():
    """Verify GitHub Actions CI workflow exists and is valid YAML without secrets."""
    base_dir = Path(__file__).parent.parent
    ci_file = base_dir / ".github" / "workflows" / "ci.yml"
    assert ci_file.exists()
    content = ci_file.read_text()
    data = yaml.safe_load(content)
    assert "jobs" in data
    assert "test" in data["jobs"]
    assert "sk-" not in content
    assert "eyJ" not in content


def test_user_data_isolation_and_rls_integrity():
    """Verify strict tenant isolation: User A cannot read or mutate User B data."""
    mock_store.clear()
    trip_repo = TripRepository(settings=Settings(demo_mode=True))

    user_a = "user-uuid-1111"
    user_b = "user-uuid-2222"

    trip_a = trip_repo.create_trip(
        user_id=user_a,
        trip_data={
            "origin": "San Francisco",
            "destination": "Kyoto",
            "start_date": "2026-10-01",
            "end_date": "2026-10-08",
            "budget": 4500.0,
        },
    )

    # User A can retrieve their trip
    fetched_a = trip_repo.get_trip(trip_a["id"], user_id=user_a)
    assert fetched_a is not None
    assert fetched_a["destination"] == "Kyoto"

    # User B CANNOT retrieve User A's trip (returns None)
    unauthorized_fetch = trip_repo.get_trip(trip_a["id"], user_id=user_b)
    assert unauthorized_fetch is None

    # User B trip listing should not contain User A's trips
    user_b_trips = trip_repo.list_user_trips(user_id=user_b)
    assert len(user_b_trips) == 0

    # User B cannot update User A's trip status
    update_res = trip_repo.update_trip_status(trip_a["id"], user_id=user_b, status="CANCELLED")
    assert update_res is None


def test_e2e_safe_production_pipeline_smoke():
    """Execute a complete, non-mutating end-to-end trip planning and HITL lifecycle."""
    replanning_svc = ReplanningService()
    exec_svc = ActionExecutionService()

    # 1. Plan Trip via LangGraph
    prompt = "Plan a 5-day cultural trip from Delhi to Tokyo with a budget of $5000 for 2 travelers"
    state = run_travel_planning(user_request=prompt, user_id="e2e-user")
    assert isinstance(state, dict)
    assert state.get("planning_status") in ("READY_WITH_WARNINGS", "COMPLETED", "READY_FOR_ITINERARY")
    assert len(state.get("flight_options", [])) > 0
    assert len(state.get("hotel_options", [])) > 0
    assert len(state.get("activities", [])) > 0
    assert state.get("budget_breakdown") is not None
    trip_id = state.get("trip_id") or "test-trip-e2e"

    # 2. Dynamic Replanning Event
    event = ChangeEvent(
        event_type=ChangeEventType.WEATHER_ALERT,
        severity=ChangeEventSeverity.HIGH,
        description="Typhoon warning for Day 2 afternoon activities.",
        affected_components=["activities"],
    )
    new_state_dict, version, impact = replanning_svc.trigger_dynamic_replan(
        change_event=event,
        current_state=state,
        user_id="e2e-user",
        trip_id=trip_id,
    )
    assert version.version >= 2
    assert "activity" in impact.affected_components or "activities" in impact.affected_components

    # 3. Action Proposal & Risk Evaluation
    risk = classify_action_risk("book_flight")
    assert risk == ActionRiskLevel.HIGH

    proposal = ActionProposal(
        trip_id=trip_id,
        user_id="e2e-user",
        action_type="book_flight",
        description="Book selected ANA roundtrip flight from Delhi to Tokyo",
        estimated_cost=800.0,
        risk_level=risk,
        state_version=2,
    )
    assert proposal.requires_approval is True
    assert proposal.estimated_cost == 800.0
    assert proposal.state_version == 2

    # 4. Safe Mock Transactional Execution
    from mcp.transactional_providers import MockFlightBookingProvider
    provider = MockFlightBookingProvider()
    book_result = provider.book_flight(
        flight_number="ANA-101",
        passenger_name="Traveler 1",
        departure_date="2026-11-01",
        origin="DEL",
        destination="HND",
    )
    assert book_result.get("status") == "CONFIRMED"
    assert book_result.get("is_mock") is True
    assert book_result.get("confirmation_code") is not None
