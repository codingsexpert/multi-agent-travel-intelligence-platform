"""Planner Agent reasoning node for travel requirement extraction and normalization."""

import time
from typing import Dict, Any, List
from graph.state import TravelState, WorkflowStatus
from services.llm_service import llm_service
from utils.logger import logger

MAX_GRAPH_STEPS = 10
MAX_PLANNER_RETRIES = 2


def planner_node(state: TravelState) -> Dict[str, Any]:
    """Execute the Planner Agent reasoning step.

    1. Increment graph step count and enforce loop protection.
    2. Extract travel requirements and detect missing/conflicting parameters.
    3. Update TravelState with normalized specifications.
    4. Record execution metadata in agent_runs.

    Args:
        state: Current TravelState dictionary.

    Returns:
        State updates dictionary for LangGraph state machine.
    """
    start_time = time.time()
    current_step = state.get("graph_step_count", 0) + 1
    logger.info(f"[PlannerAgent] Executing planner step {current_step} for request: {state.get('original_request', '')[:60]}...")

    # Loop protection
    if current_step > MAX_GRAPH_STEPS:
        err_msg = f"Maximum graph execution steps ({MAX_GRAPH_STEPS}) exceeded."
        logger.error(f"[PlannerAgent] {err_msg}")
        return {
            "graph_step_count": current_step,
            "planning_status": WorkflowStatus.FAILED.value,
            "errors": state.get("errors", []) + [err_msg],
            "clarification_required": False,
        }

    original_req = state.get("original_request", "").strip()
    if not original_req:
        err_msg = "Original travel request is empty."
        logger.warning(f"[PlannerAgent] {err_msg}")
        return {
            "graph_step_count": current_step,
            "planning_status": WorkflowStatus.NEEDS_CLARIFICATION.value,
            "clarification_required": True,
            "clarification_questions": ["Please enter your travel details or where you'd like to visit."],
            "warnings": state.get("warnings", []) + [err_msg],
        }

    # Extract structured plan
    planner_result = llm_service.extract_plan(original_req)
    req = planner_result.extracted_requirements

    # Merge warnings
    all_warnings = list(state.get("warnings", []))
    for w in planner_result.warnings:
        if w not in all_warnings:
            all_warnings.append(w)

    for a in planner_result.assumptions:
        if a not in all_warnings:
            all_warnings.append(a)

    # Calculate status
    if planner_result.clarification_required:
        status = WorkflowStatus.PLANNING.value  # Will be routed to clarification node
    else:
        status = WorkflowStatus.READY_FOR_SPECIALIZED_AGENTS.value

    duration_ms = round((time.time() - start_time) * 1000, 2)

    # Record agent run trace
    run_record = {
        "agent_name": "planner",
        "step": current_step,
        "status": "SUCCESS" if not planner_result.conflicts else "NEEDS_CLARIFICATION",
        "duration_ms": duration_ms,
        "is_demo": planner_result.is_demo,
        "clarification_required": planner_result.clarification_required,
    }
    # Return clean state delta
    return {
        "graph_step_count": current_step,
        "origin": req.origin or state.get("origin"),
        "destination": req.destination or state.get("destination"),
        "start_date": req.start_date or state.get("start_date"),
        "end_date": req.end_date or state.get("end_date"),
        "duration": req.duration or state.get("duration"),
        "travelers": req.travelers or state.get("travelers"),
        "budget": req.budget if req.budget is not None else state.get("budget"),
        "currency": req.currency or state.get("currency", "USD"),
        "interests": req.interests or state.get("interests", []),
        "travel_style": req.travel_style or state.get("travel_style"),
        "accommodation_preference": req.accommodation_preference or state.get("accommodation_preference"),
        "food_preferences": req.food_preferences or state.get("food_preferences", []),
        "constraints": req.constraints or state.get("constraints", []),
        "additional_requirements": req.additional_requirements or state.get("additional_requirements"),
        "planning_status": status,
        "clarification_required": planner_result.clarification_required,
        "clarification_questions": planner_result.clarification_questions,
        "planner_result": planner_result.model_dump(),
        "warnings": all_warnings,
        "agent_runs": [run_record],
        "is_demo": planner_result.is_demo,
    }
