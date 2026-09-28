"""Integration tests for LangGraph multi-agent parallel execution, failure isolation, and convergence."""

from unittest.mock import patch
from graph.state import create_initial_state, WorkflowStatus
from graph.workflow import travel_graph


def test_complete_multi_agent_workflow_execution():
    """Verify full workflow from START to Planner to 4 parallel agents to Research to END."""
    req_text = "Delhi se Japan 7 days ka trip plan karo, budget ₹1.5 lakh hai, 2 log hain, food + culture pasand hai."
    initial_state = create_initial_state(
        original_request=req_text,
        user_id="test-user-id",
        trip_id="trip-multi-123",
        is_demo=True,
    )

    final_state = travel_graph.invoke(initial_state)

    # 1. Status verification
    assert final_state["planning_status"] in [
        WorkflowStatus.READY_FOR_ITINERARY.value,
        WorkflowStatus.READY_WITH_WARNINGS.value,
    ]
    assert final_state["clarification_required"] is False

    # 2. Parallel Deliverables verified
    assert len(final_state["flight_options"]) >= 2
    assert all(f["demo_data"] is True for f in final_state["flight_options"])

    assert len(final_state["hotel_options"]) >= 2
    assert all(h["demo_data"] is True for h in final_state["hotel_options"])

    assert len(final_state["activities"]) >= 3
    assert all(a["demo_data"] is True for a in final_state["activities"])

    assert final_state["weather"] is not None
    assert final_state["weather"]["demo_data"] is True

    assert final_state["research_results"] is not None
    assert final_state["research_results"]["demo_data"] is True

    # 3. Agent Runs Telemetry
    executed_agents = [r["agent_name"] for r in final_state["agent_runs"]]
    for expected in ["planner", "flight", "hotel", "activity", "weather", "research", "budget_engine", "validator_engine"]:
        assert expected in executed_agents

    # Verify timing and status
    for run in final_state["agent_runs"]:
        assert run["status"] == "SUCCESS"
        assert run["duration_ms"] >= 0.0


def test_partial_agent_failure_isolation():
    """Verify that when a specialized agent fails, the workflow does not crash and exposes partial/warning results."""
    req_text = "Trip from SFO to Tokyo from 2026-11-01 to 2026-11-10 for 2 people with $5000 budget."
    initial_state = create_initial_state(
        original_request=req_text,
        user_id="test-user-id",
        is_demo=True,
    )

    # Simulate Weather Agent throwing an unhandled exception
    with patch("agents.weather_agent.generate_mock_weather", side_effect=RuntimeError("Weather sensor satellite offline")):
        final_state = travel_graph.invoke(initial_state)

    # Workflow must NOT crash
    assert final_state is not None

    # Status must reflect partial results / ready with warnings
    assert final_state["planning_status"] in [
        WorkflowStatus.PARTIAL_RESULTS.value,
        WorkflowStatus.READY_WITH_WARNINGS.value,
    ]

    # Weather result must not be fabricated
    assert final_state.get("weather") is None

    # Other parallel agents must have completed successfully
    assert len(final_state["flight_options"]) >= 2
    assert len(final_state["hotel_options"]) >= 2
    assert len(final_state["activities"]) >= 2
    assert final_state["research_results"] is not None

    # Warnings must contain isolated failure detail
    warnings = final_state.get("warnings", [])
    assert any("Weather sensor satellite offline" in w for w in warnings)

    # Run record for weather must indicate FAILED
    weather_runs = [r for r in final_state["agent_runs"] if r["agent_name"] == "weather"]
    assert len(weather_runs) == 1
    assert weather_runs[0]["status"] == "FAILED"
    assert "Weather sensor satellite offline" in weather_runs[0]["error"]


def test_clarification_bypasses_specialized_agents():
    """Verify incomplete request routes to clarification node and terminates without running specialized agents."""
    req_text = "Japan trip plan karo."
    initial_state = create_initial_state(
        original_request=req_text,
        user_id="test-user-id",
        is_demo=True,
    )

    final_state = travel_graph.invoke(initial_state)

    assert final_state["planning_status"] == WorkflowStatus.NEEDS_CLARIFICATION.value
    assert final_state["clarification_required"] is True

    # Specialized agents should NOT have been invoked
    assert len(final_state.get("flight_options", [])) == 0
    assert len(final_state.get("hotel_options", [])) == 0
    assert len(final_state.get("activities", [])) == 0
    assert final_state.get("weather") is None
    assert final_state.get("research_results") is None

    executed_agents = [r["agent_name"] for r in final_state["agent_runs"]]
    assert "flight" not in executed_agents
    assert "hotel" not in executed_agents
    assert "activity" not in executed_agents
    assert "weather" not in executed_agents
    assert "research" not in executed_agents
