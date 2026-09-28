"""Base agent execution helper providing standardized telemetry, error handling, and failure isolation."""

import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, Tuple
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
        return delta, run_record

    except Exception as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        completed_at = datetime.now(timezone.utc).isoformat()
        err_msg = f"{agent_name.capitalize()} failed: {str(e)}"
        logger.error(f"[{agent_name.capitalize()}] Failure isolated: {err_msg}")

        run_record = {
            "agent_name": agent_name,
            "step": step,
            "status": "FAILED",
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "error": str(e),
            "is_demo": is_demo,
            "demo_mode": is_demo,
            "engine_type": engine_type,
            "mode": "DETERMINISTIC" if engine_type == "DETERMINISTIC" else ("DEMO" if is_demo else "LIVE"),
        }
        fallback_delta: Dict[str, Any] = {
            "warnings": [f"Specialized agent '{agent_name}' encountered an error: {str(e)}."],
        }
        return fallback_delta, run_record
