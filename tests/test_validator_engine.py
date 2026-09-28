"""Unit and integration tests for the deterministic Validator Engine."""

from models.validation import ValidationSeverity
from models.budget import BudgetItem, BudgetItemCategory
from engines.budget_engine import BudgetEngine
from engines.validator_engine import ValidatorEngine
from graph.workflow import travel_graph
from graph.state import WorkflowStatus, create_initial_state


def create_sample_valid_state():
    """Helper returning a clean, consistent mock state with all deliverables."""
    return {
        "user_id": "test-user-123",
        "origin": "San Francisco",
        "destination": "Tokyo",
        "start_date": "2026-10-15",
        "end_date": "2026-10-22",
        "duration": 7,
        "travelers": 2,
        "budget": 5000.0,
        "currency": "USD",
        "flight_options": [
            {
                "airline": "United Airlines",
                "flight_number": "UA-875",
                "departure": "2026-10-15 08:30",
                "arrival": "2026-10-15 14:45",
                "price": 1200.0,
                "currency": "USD",
                "stops": 0,
                "demo_data": True,
            }
        ],
        "hotel_options": [
            {
                "name": "Tokyo Shinjuku Hotel",
                "price_per_night": 150.0,
                "total_price": 1050.0,
                "currency": "USD",
                "demo_data": True,
            }
        ],
        "activities": [
            {
                "name": "Senso-ji Temple Morning Visit",
                "estimated_cost": 0.0,
                "best_time": "Afternoon (15:30 - 17:30)",
                "currency": "USD",
                "demo_data": True,
            },
            {
                "name": "Shibuya Sky Observation Deck",
                "estimated_cost": 22.0,
                "best_time": "Sunset (17:30 - 19:30)",
                "currency": "USD",
                "demo_data": True,
            },
        ],
        "weather": [
            {"date": "2026-10-15", "temperature": "18°C / 64°F", "condition": "Partly Cloudy", "precipitation_probability": 15}
        ],
        "research_results": {"destination": "Tokyo", "demo_data": True},
        "is_demo": True,
    }


def test_validator_valid_results():
    """Test validation pass when all constraints and logistics are fully consistent."""
    state = create_sample_valid_state()
    budget_summary = BudgetEngine.calculate_from_state(state)
    result = ValidatorEngine.validate_plan(state, budget_summary=budget_summary)

    assert result.valid is True
    assert len(result.errors) == 0
    assert result.status in ["READY_FOR_ITINERARY", "READY_WITH_WARNINGS"]


def test_validator_missing_flight():
    """Test warning when distant trip lacks flight options."""
    state = create_sample_valid_state()
    state["flight_options"] = []
    result = ValidatorEngine.validate_plan(state)

    assert any(i.code == "MISSING_FLIGHT_OPTIONS" for i in result.warnings)
    assert any(i.severity == ValidationSeverity.WARNING for i in result.warnings)


def test_validator_missing_hotel():
    """Test warning when multi-day trip lacks lodging options."""
    state = create_sample_valid_state()
    state["hotel_options"] = []
    result = ValidatorEngine.validate_plan(state)

    assert any(i.code == "MISSING_HOTEL_OPTIONS" for i in result.warnings)


def test_validator_weather_failure():
    """Test that specialized agent weather failure produces a clean warning without fabricating weather."""
    state = create_sample_valid_state()
    state["weather"] = None
    result = ValidatorEngine.validate_plan(state)

    weather_issues = [i for i in result.warnings if i.code == "WEATHER_UNAVAILABLE"]
    assert len(weather_issues) == 1
    assert "No weather claims fabricated" in weather_issues[0].message


def test_validator_duplicate_activity():
    """Test warning when duplicate activity recommendations are present."""
    state = create_sample_valid_state()
    state["activities"].append({
        "name": "Senso-ji Temple Morning Visit",
        "estimated_cost": 10.0,
        "best_time": "Evening",
        "currency": "USD",
        "demo_data": True,
    })
    result = ValidatorEngine.validate_plan(state)

    assert any(i.code == "DUPLICATE_ACTIVITIES" for i in result.warnings)


def test_validator_invalid_dates_order():
    """Test critical error when end date precedes start date."""
    state = create_sample_valid_state()
    state["start_date"] = "2026-10-25"
    state["end_date"] = "2026-10-15"
    result = ValidatorEngine.validate_plan(state)

    assert result.valid is False
    assert result.status == "VALIDATION_FAILED"
    assert any(i.code == "INVALID_DATE_ORDER" for i in result.errors)


def test_validator_invalid_traveler_count():
    """Test critical error when traveler count is non-positive."""
    state = create_sample_valid_state()
    state["travelers"] = 0
    result = ValidatorEngine.validate_plan(state)

    assert result.valid is False
    assert any(i.code == "INVALID_TRAVELER_COUNT" for i in result.errors)


def test_validator_activity_flight_time_conflict():
    """Test detection of time conflict when activity is scheduled too soon after flight landing."""
    state = create_sample_valid_state()
    # Flight lands at 11:45
    state["flight_options"][0]["arrival"] = "2026-10-15 11:45"
    # Activity scheduled at 12:00 (insufficient transit buffer of 15 minutes)
    state["activities"][0]["best_time"] = "12:00"
    result = ValidatorEngine.validate_plan(state)

    assert any(i.code == "POSSIBLE_TIME_CONFLICT" for i in result.warnings)


def test_validator_budget_exceeded():
    """Test warning produced when budget calculation exceeds limit."""
    state = create_sample_valid_state()
    state["budget"] = 1000.0  # Tight budget below 1200 flight
    budget_summary = BudgetEngine.calculate_from_state(state)
    result = ValidatorEngine.validate_plan(state, budget_summary=budget_summary)

    assert any(i.code == "BUDGET_EXCEEDED" for i in result.warnings)


def test_validator_multiple_warnings():
    """Test that multiple non-fatal warnings accumulate without halting the workflow."""
    state = create_sample_valid_state()
    state["weather"] = None  # Warning 1: weather unavailable
    state["budget"] = 500.0  # Warning 2: budget exceeded
    budget_summary = BudgetEngine.calculate_from_state(state)
    result = ValidatorEngine.validate_plan(state, budget_summary=budget_summary)

    assert result.valid is True
    assert result.status == "READY_WITH_WARNINGS"
    assert len(result.warnings) >= 2


def test_validator_critical_failure_invalid_dates_and_travelers():
    """Test that fatal errors immediately transition status to VALIDATION_FAILED."""
    state = create_sample_valid_state()
    state["travelers"] = -2
    state["start_date"] = "2026-10-30"
    state["end_date"] = "2026-10-10"
    result = ValidatorEngine.validate_plan(state)

    assert result.valid is False
    assert result.status == "VALIDATION_FAILED"
    assert len(result.errors) >= 2


# ==============================================================================
# LangGraph End-to-End Integration Tests
# ==============================================================================

def test_full_workflow_integration_ready_for_itinerary():
    """Test complete LangGraph pipeline running through Planner -> 5 Agents -> Budget -> Validator."""
    initial_state = create_initial_state(
        original_request=(
            "Trip from San Francisco to Tokyo from 2026-10-15 to 2026-10-22 for 2 travelers with $15000 budget."
        ),
        user_id="integration-user-001",
        is_demo=True,
    )

    final_state = travel_graph.invoke(initial_state)

    # Verify workflow executed through Validator
    assert final_state["planning_status"] in [
        WorkflowStatus.READY_FOR_ITINERARY.value,
        WorkflowStatus.READY_WITH_WARNINGS.value,
    ]
    assert final_state["budget_breakdown"] is not None
    assert final_state["validation_results"] is not None
    assert final_state["validation_results"]["valid"] is True

    # Verify telemetry records for both deterministic engines
    runs = final_state.get("agent_runs", [])
    agent_names = [r["agent_name"] for r in runs]
    assert "budget_engine" in agent_names
    assert "validator_engine" in agent_names

    budget_run = next(r for r in runs if r["agent_name"] == "budget_engine")
    assert budget_run["engine_type"] == "DETERMINISTIC"


def test_full_workflow_integration_over_budget_warning():
    """Test complete pipeline where low budget triggers READY_WITH_WARNINGS."""
    initial_state = create_initial_state(
        original_request=(
            "Trip from San Francisco to Tokyo from 2026-10-15 to 2026-10-22 for 2 travelers with $800 budget."
        ),
        user_id="integration-user-002",
        is_demo=True,
    )

    final_state = travel_graph.invoke(initial_state)

    assert final_state["planning_status"] == WorkflowStatus.READY_WITH_WARNINGS.value
    assert final_state["budget_breakdown"]["within_budget"] is False
    assert final_state["budget_breakdown"]["status"] == "OVER_BUDGET"
    assert any("OVER_BUDGET" in w for w in final_state["warnings"])


def test_full_workflow_integration_clarification_skips_deterministic_engines():
    """Test that ambiguous input directs to clarification and bypasses budget & validator."""
    initial_state = create_initial_state(
        original_request="I want to go somewhere sunny next month.",
        user_id="integration-user-003",
        is_demo=True,
    )

    final_state = travel_graph.invoke(initial_state)

    assert final_state["clarification_required"] is True
    assert final_state["budget_breakdown"] is None
    assert final_state["validation_results"] is None
