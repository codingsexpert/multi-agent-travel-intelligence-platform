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


# ------------------------------------------------------------------------------
# Phase 12: Dynamic Replanning StateGraph Nodes & Workflow
# ------------------------------------------------------------------------------

def replan_detect_change_node(state: TravelState) -> Dict[str, Any]:
    """Detect, sanitize, and validate change events before replanning."""
    events_raw = state.get("pending_change_events") or []
    current_guardrail = dict(state.get("guardrail_status") or {})

    # Check loop depth
    if state.get("replan_count", 0) >= 5:
        logger.warning("[GraphReplanner] Max replan depth reached in graph. Aborting replan.")
        return {
            "planning_status": WorkflowStatus.FAILED.value,
            "errors": ["Max replan depth reached. Loop protection engaged."],
        }

    for ev in events_raw:
        desc = ev.get("description") if isinstance(ev, dict) else getattr(ev, "description", None)
        if desc:
            res = InputGuardrail.validate_text(desc)
            if not res.allowed:
                current_guardrail["input"] = {
                    "status": "BLOCKED",
                    "allowed": False,
                    "reason": res.reason,
                }
                return {
                    "planning_status": WorkflowStatus.FAILED.value,
                    "errors": [res.reason or "Change event blocked by input guardrails."],
                    "guardrail_status": current_guardrail,
                }

    current_guardrail["input"] = {"status": "PASSED", "allowed": True}
    return {"guardrail_status": current_guardrail}


def replan_impact_analysis_node(state: TravelState) -> Dict[str, Any]:
    """Run deterministic impact analysis across pending change events."""
    from engines.replanning_engine import ReplanningEngine
    from models.replanning import ChangeEvent

    if state.get("planning_status") == WorkflowStatus.FAILED.value:
        return {}

    events_raw = state.get("pending_change_events") or []
    events = [
        ev if isinstance(ev, ChangeEvent) else ChangeEvent(**ev)
        for ev in events_raw
    ]
    processed_ids = set(state.get("processed_event_ids") or [])

    impact = ReplanningEngine.analyze_impact(events, state, processed_event_ids=processed_ids)
    new_processed = list(processed_ids.union(impact.event_ids))

    return {
        "latest_impact_analysis": impact.model_dump(),
        "processed_event_ids": new_processed,
    }


def replan_selective_execution_node(state: TravelState) -> Dict[str, Any]:
    """Selectively execute only nodes impacted by change events, reusing unaffected results."""
    from engines.replanning_engine import ReplanningEngine
    from models.replanning import ImpactAnalysis, NodeExecutionAction

    if state.get("planning_status") == WorkflowStatus.FAILED.value:
        return {}

    impact_dict = state.get("latest_impact_analysis")
    if not impact_dict:
        return {}

    impact = ImpactAnalysis(**impact_dict)
    rerun_nodes = set(impact.rerun_nodes)

    # Actions map for trace
    actions_map: Dict[str, str] = {}
    for node in ReplanningEngine.ALL_WORKFLOW_NODES:
        actions_map[node] = NodeExecutionAction.RERUN.value if node in rerun_nodes else NodeExecutionAction.REUSE.value

    # Snapshot last valid itinerary
    curr_ver = state.get("itinerary_version", 1)
    prev_valid = state.get("last_valid_itinerary")
    if not prev_valid and state.get("flight_options"):
        prev_valid = {
            "version": curr_ver,
            "flight_options": list(state.get("flight_options", [])),
            "hotel_options": list(state.get("hotel_options", [])),
            "activities": list(state.get("activities", [])),
            "weather": state.get("weather"),
            "budget_breakdown": state.get("budget_breakdown"),
            "validation_results": state.get("validation_results"),
        }

    updates: Dict[str, Any] = {
        "agent_execution_modes": actions_map,
        "last_valid_itinerary": prev_valid,
    }

    # Apply direct event updates to state
    events_raw = state.get("pending_change_events") or []
    for ev in events_raw:
        ev_type = ev.get("event_type") if isinstance(ev, dict) else ev.event_type.value
        new_val = ev.get("new_value") if isinstance(ev, dict) else ev.new_value
        if ev_type == "BUDGET_CHANGED" and new_val is not None:
            updates["budget"] = float(new_val)
        elif ev_type == "TRAVELLER_COUNT_CHANGED" and new_val is not None:
            updates["travelers"] = int(new_val)
        elif ev_type == "DESTINATION_CHANGED" and new_val is not None:
            updates["destination"] = str(new_val)

    temp_state = {**state, **updates}

    # Selective execution
    if "flight" in rerun_nodes:
        flight_res = flight_agent_node(temp_state)
        f_opts = list(flight_res.get("flight_options", []))
        if f_opts and isinstance(f_opts[0], dict):
            f_opts[0]["flight_number"] = f"{f_opts[0].get('flight_number', 'FL')}-ALT"
            f_opts[0]["availability_status"] = "Replan Confirmed"
        updates["flight_options"] = f_opts
        if flight_res.get("agent_runs"):
            updates["agent_runs"] = flight_res["agent_runs"]

    if "hotel" in rerun_nodes:
        hotel_res = hotel_agent_node(temp_state)
        updates["hotel_options"] = hotel_res.get("hotel_options", [])
        if hotel_res.get("agent_runs"):
            updates["agent_runs"] = updates.get("agent_runs", []) + hotel_res["agent_runs"]

    if "activity" in rerun_nodes:
        current_acts = list(temp_state.get("activities", []))
        if current_acts and impact.affected_days:
            updated_acts = []
            for act in current_acts:
                a_copy = dict(act)
                if a_copy.get("day", 1) in impact.affected_days:
                    a_copy["name"] = f"Indoor Cultural Experience: {a_copy.get('name', 'Attraction')}"
                    a_copy["description"] = "Weather-protected indoor venue selected during replanning."
                    a_copy["is_indoor"] = True
                updated_acts.append(a_copy)
            updates["activities"] = updated_acts
        else:
            act_res = activity_agent_node(temp_state)
            updates["activities"] = act_res.get("activities", [])
            if act_res.get("agent_runs"):
                updates["agent_runs"] = updates.get("agent_runs", []) + act_res["agent_runs"]

    if "weather" in rerun_nodes:
        weather_res = weather_agent_node(temp_state)
        updates["weather"] = weather_res.get("weather")

    if "research" in rerun_nodes:
        res_res = research_agent_node(temp_state)
        updates["research_results"] = res_res.get("research_results")

    return updates


def replan_itinerary_version_node(state: TravelState) -> Dict[str, Any]:
    """Finalize new ItineraryVersion, manage version increment, and rollback if invalid."""
    from models.replanning import ItineraryVersion

    if state.get("planning_status") == WorkflowStatus.FAILED.value:
        return {}

    curr_ver = state.get("itinerary_version", 1)
    next_ver = curr_ver + 1
    val_res = state.get("validation_results") or {}
    is_valid = val_res.get("valid", True)
    warnings = val_res.get("warnings", [])

    impact_dict = state.get("latest_impact_analysis") or {}
    replan_reason = impact_dict.get("replan_reason", "Dynamic replan")
    human_expl = impact_dict.get("human_explanation", "")

    new_version = ItineraryVersion(
        version=next_ver,
        change_reason=replan_reason,
        human_explanation=human_expl,
        flight_options=state.get("flight_options", []),
        hotel_options=state.get("hotel_options", []),
        activities=state.get("activities", []),
        weather=state.get("weather"),
        research_results=state.get("research_results"),
        budget_breakdown=state.get("budget_breakdown"),
        validation_results=val_res,
        is_valid=is_valid,
        warnings=warnings,
        sources=state.get("sources", []),
        node_execution_actions=state.get("agent_execution_modes", {}),
    )

    history = list(state.get("itinerary_history") or [])
    history.append(new_version.model_dump())
    reasons = list(state.get("replan_reasons") or [])
    reasons.append(replan_reason)

    return {
        "itinerary_version": next_ver,
        "itinerary_history": history,
        "replan_count": state.get("replan_count", 0) + 1,
        "replan_reasons": reasons,
        "pending_change_events": [],
    }


def create_replanning_graph():
    """Build and compile the Phase 12 Dynamic Replanning LangGraph workflow."""
    replan_wf = StateGraph(TravelState)

    # 1. Register Nodes
    replan_wf.add_node("detect_change", replan_detect_change_node)
    replan_wf.add_node("impact_analysis", replan_impact_analysis_node)
    replan_wf.add_node("selective_execution", replan_selective_execution_node)
    replan_wf.add_node("budget_engine", budget_agent_node)
    replan_wf.add_node("validator", validator_agent_node)
    replan_wf.add_node("itinerary_version", replan_itinerary_version_node)
    replan_wf.add_node("output_guardrail", output_guardrail_node)

    # 2. Pipeline Sequence
    replan_wf.add_edge(START, "detect_change")
    replan_wf.add_edge("detect_change", "impact_analysis")
    replan_wf.add_edge("impact_analysis", "selective_execution")
    replan_wf.add_edge("selective_execution", "budget_engine")
    replan_wf.add_edge("budget_engine", "validator")
    replan_wf.add_edge("validator", "itinerary_version")
    replan_wf.add_edge("itinerary_version", "output_guardrail")
    replan_wf.add_edge("output_guardrail", END)

    return replan_wf.compile()


# Compiled Singleton Graphs
travel_graph = create_travel_graph()
replanning_graph = create_replanning_graph()

