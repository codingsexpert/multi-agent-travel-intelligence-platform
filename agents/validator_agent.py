"""LangGraph node wrapping the deterministic Validator Engine."""

from typing import Dict, Any, List
from graph.state import TravelState, WorkflowStatus
from engines.validator_engine import ValidatorEngine
from models.budget import BudgetSummary
from models.validation import ValidationSeverity
from agents.base_agent import execute_agent_safely


def validator_agent_node(state: TravelState) -> Dict[str, Any]:
    """Execute deterministic constraint and feasibility checks on TravelState.

    Inspects budget, dates, traveler counts, flight/hotel logistics, travel-time conflicts,
    and agent deliverables to derive final workflow status.
    """
    def _action() -> Dict[str, Any]:
        budget_summary = None
        raw_budget = state.get("budget_breakdown")
        if raw_budget and isinstance(raw_budget, dict):
            try:
                budget_summary = BudgetSummary(**raw_budget)
            except Exception:
                budget_summary = None

        result = ValidatorEngine.validate_plan(dict(state), budget_summary=budget_summary)

        # Extract textual warnings and errors to propagate into state
        new_warnings: List[str] = [
            f"[{issue.component.upper()}] {issue.message}"
            for issue in result.warnings
        ]
        new_errors: List[str] = [
            f"[{issue.component.upper()}] {issue.message}"
            for issue in result.errors
        ]

        return {
            "validation_results": result.model_dump(),
            "planning_status": result.status,
            "warnings": new_warnings,
            "errors": new_errors,
        }

    delta, run_record = execute_agent_safely(
        agent_name="validator_engine",
        action=_action,
        step=state.get("graph_step_count", 3) + 1,
        is_demo=state.get("is_demo", True),
        engine_type="DETERMINISTIC",
    )

    return {
        "validation_results": delta.get("validation_results"),
        "planning_status": delta.get("planning_status", WorkflowStatus.VALIDATION_FAILED.value),
        "warnings": delta.get("warnings", []),
        "errors": delta.get("errors", []),
        "agent_runs": [run_record],
    }
