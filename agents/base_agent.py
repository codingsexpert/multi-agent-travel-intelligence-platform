"""Base agent execution helper providing standardized telemetry, error handling, and failure isolation."""

import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable, Tuple
from utils.logger import logger


def execute_agent_safely(
    agent_name: str,
    action: Callable[[], Dict[str, Any]],
    step: int = 1,
    is_demo: bool = True,
    engine_type: str = "REASONING",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Execute specialized agent logic wrapped in uniform failure isolation and telemetry.

    Args:
        agent_name: Logical identifier of the agent/engine (e.g. 'flight', 'budget_engine').
        action: Callable executing domain reasoning or deterministic math and returning state delta.
        step: Current graph execution step.
        is_demo: Whether running in DEMO_DATA mode.
        engine_type: Either 'REASONING' for LLM/heuristic agents or 'DETERMINISTIC' for rule/math engines.

    Returns:
        Tuple of (state_delta, agent_run_record).
        If action raises an exception, state_delta will contain warnings/errors rather than crashing.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    start_time = time.time()
    logger.info(f"[{agent_name.capitalize()}] Initiating execution (DEMO_MODE={is_demo}, type={engine_type})")

    try:
        delta = action()
        duration_ms = round((time.time() - start_time) * 1000, 2)
        completed_at = datetime.now(timezone.utc).isoformat()

        run_record = {
            "agent_name": agent_name,
            "step": step,
            "status": "SUCCESS",
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "error": None,
            "is_demo": is_demo,
            "demo_mode": is_demo,
            "engine_type": engine_type,
            "mode": "DETERMINISTIC" if engine_type == "DETERMINISTIC" else ("DEMO" if is_demo else "LIVE"),
        }
        logger.info(f"[{agent_name.capitalize()}] Execution succeeded in {duration_ms}ms")
        from guardrails.security import SecretRedactor
        return delta, SecretRedactor.redact_dict(run_record)


    except Exception as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        completed_at = datetime.now(timezone.utc).isoformat()
        from guardrails.security import SecretRedactor
        safe_err = SecretRedactor.redact_text(str(e))
        err_msg = f"{agent_name.capitalize()} failed: {safe_err}"
        logger.error(f"[{agent_name.capitalize()}] Failure isolated: {err_msg}")

        run_record = {
            "agent_name": agent_name,
            "step": step,
            "status": "FAILED",
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "error": safe_err,
            "is_demo": is_demo,
            "demo_mode": is_demo,
            "engine_type": engine_type,
            "mode": "DETERMINISTIC" if engine_type == "DETERMINISTIC" else ("DEMO" if is_demo else "LIVE"),
        }
        fallback_delta: Dict[str, Any] = {
            "warnings": [f"Specialized agent '{agent_name}' encountered an error: {safe_err}."],
        }
        return fallback_delta, SecretRedactor.redact_dict(run_record)


AGENT_CONTEXT_REQUIREMENTS: Dict[str, List[str]] = {
    "weather": ["destination", "start_date", "end_date", "duration", "is_demo", "trip_id"],
    "flight": ["origin", "destination", "start_date", "end_date", "travelers", "flight_budget", "currency", "is_demo", "trip_id"],
    "hotel": ["destination", "start_date", "end_date", "travelers", "hotel_budget", "currency", "is_demo", "trip_id"],
    "activity": ["destination", "start_date", "end_date", "travelers", "activity_budget", "currency", "is_demo", "trip_id"],
    "research": ["destination", "original_request", "is_demo", "trip_id"],
    "budget_engine": ["budget", "flight_options", "hotel_options", "activity_options", "currency", "is_demo", "trip_id"],
    "validator": ["itinerary", "budget_breakdown", "flight_options", "hotel_options", "activity_options", "is_demo", "trip_id"],
}


def minimize_agent_context(agent_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract strictly necessary state fields for an agent to minimize context size and token overhead."""
    allowed_keys = AGENT_CONTEXT_REQUIREMENTS.get(agent_name)
    if not allowed_keys:
        return dict(state)
    return {k: state[k] for k in allowed_keys if k in state}

