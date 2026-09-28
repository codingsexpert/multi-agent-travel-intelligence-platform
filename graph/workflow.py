"""LangGraph StateGraph workflow definition for multi-agent travel intelligence platform."""

from typing import Union, List, Literal
from langgraph.graph import StateGraph, START, END
from graph.state import TravelState, WorkflowStatus
from agents.planner import planner_node
from agents.clarification import clarification_node
from agents.flight_agent import flight_agent_node
from agents.hotel_agent import hotel_agent_node
from agents.activity_agent import activity_agent_node
from agents.weather_agent import weather_agent_node
from agents.research_agent import research_agent_node
from utils.logger import logger


def route_after_planner(
    state: TravelState,
) -> Union[str, List[str]]:
    """Conditional routing after Planner Agent reasoning step.

    - If execution failed or had fatal errors, route directly to END.
    - If essential requirements are missing or conflicting, route to clarification node.
    - If all requirements are validated and complete, fan-out in parallel to specialized agents:
      [flight, hotel, activity, weather].
    """
    if state.get("planning_status") == WorkflowStatus.FAILED.value:
        logger.warning("[GraphRouter] Planner failed, routing to END.")
        return END

    if state.get("clarification_required"):
        logger.info("[GraphRouter] Clarification required, routing to clarification node.")
        return "clarification"

    logger.info("[GraphRouter] Requirements validated. Fanning out to specialized agents [flight, hotel, activity, weather].")
    return ["flight", "hotel", "activity", "weather"]


def create_travel_graph():
    """Build and compile the Phase 5 multi-agent LangGraph workflow."""
    workflow = StateGraph(TravelState)

    # 1. Register Nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("clarification", clarification_node)
    workflow.add_node("flight", flight_agent_node)
    workflow.add_node("hotel", hotel_agent_node)
    workflow.add_node("activity", activity_agent_node)
    workflow.add_node("weather", weather_agent_node)
    workflow.add_node("research", research_agent_node)

    # 2. Connect START to Planner
    workflow.add_edge(START, "planner")

    # 3. Conditional Routing from Planner
    workflow.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "clarification": "clarification",
            "flight": "flight",
            "hotel": "hotel",
            "activity": "activity",
            "weather": "weather",
            END: END,
        },
    )

    # 4. Clarification routes to END
    workflow.add_edge("clarification", END)

    # 5. Parallel Fan-In: specialized agents converge into Research node
    workflow.add_edge("flight", "research")
    workflow.add_edge("hotel", "research")
    workflow.add_edge("activity", "research")
    workflow.add_edge("weather", "research")

    # 6. Research node assesses completion and routes to END
    workflow.add_edge("research", END)

    return workflow.compile()


# Compiled Singleton Graph
travel_graph = create_travel_graph()
