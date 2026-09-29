"""LangGraph StateGraph workflow definition for multi-agent travel intelligence platform."""

from typing import Union, List, Literal, Dict, Any
from langgraph.graph import StateGraph, START, END
from graph.state import TravelState, WorkflowStatus
from guardrails.input import InputGuardrail
from guardrails.output import OutputGuardrail
from guardrails.security import SecretRedactor
from agents.planner import planner_node
from agents.clarification import clarification_node
from agents.flight_agent import flight_agent_node
from agents.hotel_agent import hotel_agent_node
from agents.activity_agent import activity_agent_node
from agents.weather_agent import weather_agent_node
from agents.research_agent import research_agent_node
from agents.budget_agent import budget_agent_node
from agents.validator_agent import validator_agent_node
from utils.logger import logger


def input_guardrail_node(state: TravelState) -> Dict[str, Any]:
    """Validate user input against length, prompt injection, and PII before planner reasoning."""
    req = state.get("original_request", "")
    res = InputGuardrail.validate_text(req)

    current_guardrail = dict(state.get("guardrail_status") or {})

    if not res.allowed:
        current_guardrail["input"] = {
            "status": "BLOCKED",
            "allowed": False,
            "reason": res.reason,
            "category": res.category,
            "severity": res.severity,
        }
        return {
            "planning_status": WorkflowStatus.FAILED.value,
            "errors": [res.reason or "Input blocked by security guardrails."],
            "guardrail_status": current_guardrail,
            "security_events": [
                {
                    "event_type": res.category,
                    "severity": res.severity,
                    "message": res.reason,
                    "user_id": state.get("user_id"),
                }
            ],
        }

    current_guardrail["input"] = {
        "status": "PASSED",
        "allowed": True,
    }
    return {
        "original_request": res.sanitized_input if res.sanitized_input else req,
        "guardrail_status": current_guardrail,
    }


def output_guardrail_node(state: TravelState) -> Dict[str, Any]:
    """Validate final itinerary deliverable and validation results before returning to user."""
    current_guardrail = dict(state.get("guardrail_status") or {})
    val_res = state.get("validation_results")
    out_val = OutputGuardrail.validate_agent_output("validator", val_res) if val_res else None

    current_guardrail["output"] = {
        "status": "VALIDATED" if (out_val is None or out_val.valid) else "FAILED",
        "valid": out_val.valid if out_val else True,
        "errors": out_val.errors if out_val else [],
    }
    current_guardrail["runtime"] = {"status": "WITHIN_LIMITS"}

    return {
        "guardrail_status": current_guardrail,
    }



def route_after_input_guardrail(state: TravelState) -> str:
    """Route to planner if input passed guardrails, otherwise terminate immediately."""
    if state.get("planning_status") == WorkflowStatus.FAILED.value:
        logger.warning("[GraphRouter] Input guardrail failed; routing directly to END.")
        return END
    return "planner"


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
    """Build and compile the multi-agent LangGraph workflow with full input and output guardrails."""
    workflow = StateGraph(TravelState)

    # 1. Register Guardrail Nodes
    workflow.add_node("input_guardrail", input_guardrail_node)
    workflow.add_node("output_guardrail", output_guardrail_node)

    # 2. Register Reasoning & Specialized Nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("clarification", clarification_node)
    workflow.add_node("flight", flight_agent_node)
    workflow.add_node("hotel", hotel_agent_node)
    workflow.add_node("activity", activity_agent_node)
    workflow.add_node("weather", weather_agent_node)
    workflow.add_node("research", research_agent_node)

    # 3. Register Deterministic Engine Nodes
    workflow.add_node("budget_engine", budget_agent_node)
    workflow.add_node("validator", validator_agent_node)

    # 4. Connect START to Input Guardrail
    workflow.add_edge(START, "input_guardrail")

    # 5. Conditional Routing from Input Guardrail
    workflow.add_conditional_edges(
        "input_guardrail",
        route_after_input_guardrail,
        {
            "planner": "planner",
            END: END,
        },
    )

    # 6. Conditional Routing from Planner
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

    # 7. Clarification routes to END
    workflow.add_edge("clarification", END)

    # 8. Parallel Fan-In: specialized agents converge into Research node
    workflow.add_edge("flight", "research")
    workflow.add_edge("hotel", "research")
    workflow.add_edge("activity", "research")
    workflow.add_edge("weather", "research")

    # 9. Convergence Pipeline: Research -> Budget Engine -> Validator -> Output Guardrail -> END
    workflow.add_edge("research", "budget_engine")
    workflow.add_edge("budget_engine", "validator")
    workflow.add_edge("validator", "output_guardrail")
    workflow.add_edge("output_guardrail", END)

    return workflow.compile()


# Compiled Singleton Graph
travel_graph = create_travel_graph()

