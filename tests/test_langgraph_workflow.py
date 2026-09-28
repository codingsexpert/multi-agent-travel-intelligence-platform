"""Unit tests for LangGraph workflow execution, conditional routing, and loop protection."""

from graph.state import create_initial_state, WorkflowStatus
from graph.workflow import travel_graph
from agents.planner import MAX_GRAPH_STEPS


def test_langgraph_complete_workflow_execution():
    """Verify workflow executes from START to planner to END with READY_FOR_SPECIALIZED_AGENTS."""
    request_text = "Delhi se Japan 7 days ka trip plan karo, budget ₹1.5 lakh hai, 2 log hain, food + culture pasand hai."
    initial_state = create_initial_state(
        original_request=request_text,
        user_id="user-123",
        trip_id="trip-abc",
        is_demo=True,
    )

    final_state = travel_graph.invoke(initial_state)

    assert final_state["planning_status"] == WorkflowStatus.READY_FOR_SPECIALIZED_AGENTS.value
    assert final_state["clarification_required"] is False
    assert final_state["destination"] == "Japan"
    assert final_state["origin"] == "Delhi"
    assert final_state["travelers"] == 2
    assert final_state["budget"] == 150000.0
    assert final_state["currency"] == "INR"
    assert final_state["graph_step_count"] == 1
    assert len(final_state["agent_runs"]) == 1
    assert final_state["agent_runs"][0]["agent_name"] == "planner"


def test_langgraph_clarification_routing():
    """Verify incomplete request routes through planner to clarification node and finishes with NEEDS_CLARIFICATION."""
    request_text = "Japan trip plan karo."
    initial_state = create_initial_state(
        original_request=request_text,
        user_id="user-123",
        is_demo=True,
    )

    final_state = travel_graph.invoke(initial_state)

    assert final_state["planning_status"] == WorkflowStatus.NEEDS_CLARIFICATION.value
    assert final_state["clarification_required"] is True
    assert len(final_state["clarification_questions"]) >= 4
    # Planner executed (step 1), routed to clarification node (step 2)
    assert final_state["graph_step_count"] == 2
    assert len(final_state["agent_runs"]) == 2
    assert final_state["agent_runs"][0]["agent_name"] == "planner"
    assert final_state["agent_runs"][1]["agent_name"] == "clarification"


def test_langgraph_loop_protection():
    """Verify graph terminates safely when step count reaches MAX_GRAPH_STEPS."""
    initial_state = create_initial_state(
        original_request="Trip to London",
        user_id="user-123",
        is_demo=True,
    )
    # Set step count at the limit
    initial_state["graph_step_count"] = MAX_GRAPH_STEPS

    final_state = travel_graph.invoke(initial_state)

    assert final_state["planning_status"] == WorkflowStatus.FAILED.value
    assert any("Maximum graph execution steps" in err for err in final_state["errors"])


def test_empty_request_handling():
    """Verify empty user request triggers immediate clarification request without crashing."""
    initial_state = create_initial_state(
        original_request="   ",
        user_id="user-123",
        is_demo=True,
    )

    final_state = travel_graph.invoke(initial_state)

    assert final_state["clarification_required"] is True
    assert final_state["planning_status"] == WorkflowStatus.NEEDS_CLARIFICATION.value
