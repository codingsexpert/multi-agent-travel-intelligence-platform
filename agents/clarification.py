"""Clarification node for handling incomplete or ambiguous travel requirements."""

import time
from typing import Dict, Any, List
from graph.state import TravelState, WorkflowStatus
from utils.logger import logger
from agents.planner import MAX_GRAPH_STEPS


def clarification_node(state: TravelState) -> Dict[str, Any]:
    """Execute the Clarification step when travel specifications require user input.

    1. Increment graph step count.
    2. Set status to NEEDS_CLARIFICATION.
    3. Ensure questions are cleanly articulated.
    4. Record execution trace in agent_runs.

    Args:
        state: Current TravelState dictionary.

    Returns:
        State updates dictionary.
    """
    start_time = time.time()
    current_step = state.get("graph_step_count", 0) + 1
    logger.info(f"[ClarificationNode] Step {current_step}: requirements require user clarification.")

    if current_step > MAX_GRAPH_STEPS:
        err_msg = f"Maximum graph execution steps ({MAX_GRAPH_STEPS}) exceeded during clarification."
        logger.error(f"[ClarificationNode] {err_msg}")
        return {
            "graph_step_count": current_step,
            "planning_status": WorkflowStatus.FAILED.value,
            "errors": state.get("errors", []) + [err_msg],
        }

    questions: List[str] = state.get("clarification_questions", [])
    if not questions:
        questions = ["Please provide more details regarding your departure city, destination, travel dates, or budget."]

    duration_ms = round((time.time() - start_time) * 1000, 2)
    run_record = {
        "agent_name": "clarification",
        "step": current_step,
        "status": "SUCCESS",
        "duration_ms": duration_ms,
        "questions_count": len(questions),
    }

    agent_runs = list(state.get("agent_runs", [])) + [run_record]

    return {
        "graph_step_count": current_step,
        "planning_status": WorkflowStatus.NEEDS_CLARIFICATION.value,
        "clarification_required": True,
        "clarification_questions": questions,
        "agent_runs": agent_runs,
    }
