"""LangGraph StateGraph workflow definition for travel intelligence planning."""

from typing import Literal
from langgraph.graph import StateGraph, START, END
from graph.state import TravelState, WorkflowStatus
from agents.planner import planner_node
from agents.clarification import clarification_node
from utils.logger import logger


def route_after_planner(state: TravelState) -> Literal["clarification", "__end__"]:
    """Conditional routing after Planner Agent reasoning step.

    - If execution failed or had fatal errors, route to END.
    - If essential requirements are missing or conflicting, route to clarification node.
    - If all requirements are validated and complete, route to END (READY_FOR_SPECIALIZED_AGENTS).
    """
    if state.get("planning_status") == WorkflowStatus.FAILED.value:
        logger.warning("[GraphRouter] Planner failed, routing to END.")
        return END

    if state.get("clarification_required"):
        logger.info("[GraphRouter] Clarification required, routing to clarification node.")
        return "clarification"

    logger.info("[GraphRouter] Requirements validated and complete, routing to END (ready for specialized agents).")
    return END


def create_travel_graph():
    """Build and compile the Phase 4 LangGraph workflow."""
    workflow = StateGraph(TravelState)

    # Register Nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("clarification", clarification_node)

    # Connect START to Planner
    workflow.add_edge(START, "planner")

    # Conditional Routing from Planner
    workflow.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "clarification": "clarification",
            END: END,
        },
    )

    # Connect Clarification to END
    workflow.add_edge("clarification", END)

    return workflow.compile()


# Compiled Singleton Graph
travel_graph = create_travel_graph()
