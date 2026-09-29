"""Visual Multi-Agent Planning Pipeline Progress Screen.

Phase 17: Production Travel Command Center UI/UX.
Displays actual execution progress across all 10 specialized agent and engine stages:
Trip Request -> Requirements -> Planner -> Flights -> Hotels -> Activities -> Weather -> Research -> Budget -> Validation -> Itinerary.
Uses real session workflow state — zero fabricated progress.
"""

from typing import Dict, Any, List, Tuple
import streamlit as st
from app.state.session import get_current_trip, navigate_to
from app.components.styles import inject_custom_styles
from app.components.empty_state import render_empty_state


PIPELINE_STAGES: List[Tuple[str, str, str, str]] = [
    ("Trip Request", "Core travel requirement ingestion and normalization", "Pydantic", "input"),
    ("Requirements Intake", "Schema validation, boundary checks, and PII masking", "Guardrails", "security"),
    ("Planner Agent", "Strategic travel decomposition & multi-city routing", "LLM", "planner_result"),
    ("Flight Agent", "Aviation inventory discovery & multi-leg flight comparisons", "MCP", "flight_options"),
    ("Hotel Agent", "Hospitality filtering matching budget & star rating", "MCP", "hotel_options"),
    ("Activity Agent", "Curated cultural tours & landmark pacing", "MCP", "activity_options"),
    ("Weather Agent", "Meteorological forecasts & seasonal warnings", "MCP", "weather_forecast"),
    ("Research Agent", "RAG vector retrieval & live web advisory search", "RAG/Web", "destination_research"),
    ("Budget Engine", "Deterministic financial math & category aggregation", "Python", "budget_summary"),
    ("Validation Engine", "Temporal feasibility & logical sequence verification", "Python", "validation_result"),
    ("Itinerary Agent", "Final narrative synthesis & chronological schedule", "LLM", "final_itinerary"),
]


def render_planning_progress_page() -> None:
    """Render the live planning progress visualizer."""
    inject_custom_styles()

    st.markdown(
        """
        <div class="main-header">
            <div class="main-title">⏳ Multi-Agent Planning Progress</div>
            <div class="main-subtitle">Live execution telemetry across autonomous reasoning agents and deterministic engines.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    trip = get_current_trip()
    if not trip:
        render_empty_state(
            title="No Active Planning Session",
            description="Start a new travel plan to observe the autonomous multi-agent pipeline in real-time.",
            icon="⏳",
            action_label="➕ Plan a New Trip",
            target_page="New Trip",
        )
        return

    travel_state: Dict[str, Any] = st.session_state.get("travel_state", {})
    wf_status = st.session_state.get("workflow_status", "IDLE")

    # Status Overview Header
    total_stages = len(PIPELINE_STAGES)
    completed_stages = 0
    stage_statuses = []

    for name, desc, tech, state_key in PIPELINE_STAGES:
        if state_key in ("input", "security"):
            is_done = trip is not None
        else:
            is_done = bool(travel_state.get(state_key))
        if is_done:
            completed_stages += 1
            stage_statuses.append((name, desc, tech, "COMPLETED", "#34D399"))
        elif wf_status == "RUNNING" and completed_stages == len(stage_statuses):
            stage_statuses.append((name, desc, tech, "RUNNING", "#60A5FA"))
        else:
            stage_statuses.append((name, desc, tech, "PENDING", "#64748B"))

    progress_percent = int((completed_stages / total_stages) * 100)

    # Top Metrics Bar
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Pipeline Progress", f"{progress_percent}%")
    with m2:
        st.metric("Stages Completed", f"{completed_stages}/{total_stages}")
    with m3:
        st.metric("Workflow State", wf_status)
    with m4:
        replan_count = travel_state.get("replan_count", 0)
        st.metric("Replanning Iterations", f"v{replan_count + 1}")

    st.progress(progress_percent / 100.0)

    st.markdown("---")
    st.markdown("### 📋 Stage-by-Stage Agent Telemetry")

    # Render Visual Timeline
    for idx, (name, desc, tech, status, color) in enumerate(stage_statuses, start=1):
        with st.container():
            badge_class = {
                "COMPLETED": "badge-completed",
                "RUNNING": "badge-running",
                "PENDING": "badge",
            }.get(status, "badge")

            status_icon = "✅" if status == "COMPLETED" else ("🔄" if status == "RUNNING" else "⏳")

            st.markdown(
                f"""
                <div class="travel-card" style="border-left: 3px solid {color}; padding: 12px 16px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-weight: 700; color: #F8FAFC; font-size: 1rem;">
                                {idx}. {name}
                            </span>
                            <span class="badge" style="background: #1E293B; color: #94A3B8; margin-left: 8px;">{tech}</span>
                        </div>
                        <div>
                            <span class="badge {badge_class}">{status_icon} {status}</span>
                        </div>
                    </div>
                    <div style="font-size: 0.85rem; color: #94A3B8; margin-top: 4px;">
                        {desc}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Warnings & Validation Issues
    val_result = travel_state.get("validation_result", {})
    issues = val_result.get("issues", []) if isinstance(val_result, dict) else getattr(val_result, "issues", [])
    if issues:
        st.markdown("---")
        st.markdown("### ⚠️ Non-Blocking Pipeline Warnings")
        for iss in issues:
            msg = iss.get("message", str(iss)) if isinstance(iss, dict) else getattr(iss, "message", str(iss))
            st.markdown(
                f"""
                <div class="system-warning">
                    <strong>Validation Warning:</strong> {msg}
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Action navigation
    st.markdown("---")
    nav1, nav2 = st.columns(2)
    with nav1:
        if st.button("🗓️ Inspect Current Itinerary", use_container_width=True, type="primary"):
            navigate_to("Itinerary")
            st.rerun()
    with nav2:
        if st.button("🔍 View Detailed Agent Traces", use_container_width=True):
            navigate_to("Agent Trace")
            st.rerun()
