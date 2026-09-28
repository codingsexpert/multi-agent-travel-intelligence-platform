"""LangGraph node wrapping the deterministic Budget Engine."""

from typing import Dict, Any
from graph.state import TravelState
from engines.budget_engine import BudgetEngine
from agents.base_agent import execute_agent_safely


def budget_agent_node(state: TravelState) -> Dict[str, Any]:
    """Execute deterministic budget calculations and append telemetry.

    Calculates category costs, food/transport allowances, and adherence to total budget cap.
    """
    def _action() -> Dict[str, Any]:
        from mcp.client import MCPClient
        prior_calls = len(MCPClient.get_recent_calls())
        budget_summary = BudgetEngine.calculate_from_state(dict(state))
        new_calls = [
            c.model_dump()
            for c in MCPClient.get_recent_calls()[prior_calls:]
            if c.agent_name == "budget"
        ]
        return {
            "budget_breakdown": budget_summary.model_dump(),
            "warnings": [w for w in budget_summary.warnings if "OVER_BUDGET" in w or "Currency mismatch" in w],
            "tool_calls": new_calls,
        }

    delta, run_record = execute_agent_safely(
        agent_name="budget_engine",
        action=_action,
        step=state.get("graph_step_count", 2) + 1,
        is_demo=state.get("is_demo", True),
        engine_type="DETERMINISTIC",
    )

    return {
        "budget_breakdown": delta.get("budget_breakdown"),
        "warnings": delta.get("warnings", []),
        "agent_runs": [run_record],
        "tool_calls": delta.get("tool_calls", []),
    }
