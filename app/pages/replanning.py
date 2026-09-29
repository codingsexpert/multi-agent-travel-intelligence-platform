"""Changes & Dynamic Replanning Command Center UI.

Phase 17: Production Travel Command Center UI/UX.
Displays:
- Real-time Replanning Timeline (Event -> Impact -> Affected Nodes -> Reused Nodes -> New Version)
- Explicit Node Action Labels (RERUN, REUSED, INVALIDATED, SKIPPED, FAILED)
- Human explanation of why the itinerary changed
- Version history comparison (v1, v2, v3...)
- Interactive Disruption Simulator to test live dynamic replanning on active trips
"""

from typing import Dict, Any, List
import streamlit as st
from app.state.session import get_current_trip, navigate_to
from app.components.styles import inject_custom_styles
from app.components.empty_state import render_empty_state
from models.replanning import ChangeEvent, ChangeEventType, ChangeEventSeverity
from services.replanning_service import replanning_service


def render_replanning_page() -> None:
    """Render the Changes & Replanning timeline and management screen."""
    inject_custom_styles()

    st.markdown(
        """
        <div class="main-header">
            <div class="main-title">🔄 Changes & Dynamic Replanning</div>
            <div class="main-subtitle">Surgical disruption recovery, selective graph execution, and multi-version itinerary history.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    trip = get_current_trip()
    if not trip:
        render_empty_state(
            title="No Active Trip for Replanning",
            description="Replanning operates on active travel requests. Please create a trip first to test or inspect disruption recovery.",
            icon="🔄",
            action_label="➕ Create New Trip",
            target_page="New Trip",
        )
        return

    travel_state: Dict[str, Any] = st.session_state.get("travel_state", {})
    itinerary_ver = travel_state.get("itinerary_version", 1)
    replan_count = travel_state.get("replan_count", 0)
    replan_reasons: List[str] = travel_state.get("replan_reasons", [])
    latest_impact: Dict[str, Any] = travel_state.get("latest_impact_analysis", {})
    exec_modes: Dict[str, str] = travel_state.get("agent_execution_modes", {})
    itinerary_history: List[Dict[str, Any]] = travel_state.get("itinerary_history", [])

    # Overview Metrics Bar
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Current Version", f"v{itinerary_ver}")
    with m2:
        st.metric("Disruptions Handled", str(replan_count))
    with m3:
        latest_trigger = replan_reasons[-1] if replan_reasons else "Initial Synthesis"
        st.metric("Latest Trigger", latest_trigger[:24] + "..." if len(latest_trigger) > 24 else latest_trigger)
    with m4:
        reused_count = sum(1 for m in exec_modes.values() if m == "REUSED")
        st.metric("Reused Nodes", f"{reused_count} Saved")

    st.markdown("---")

    tab_timeline, tab_simulate, tab_history = st.tabs([
        "⚡ Replanning Timeline",
        "🧪 Simulate Disruption Event",
        "📜 Version History",
    ])

    with tab_timeline:
        st.markdown("### 🗺️ Disruption & Recovery Flow")
        if replan_count == 0:
            st.info("ℹ️ **Itinerary is at Initial State (v1)**. No disruption events have occurred yet. You can simulate disruptions in the 'Simulate Disruption Event' tab.")
        else:
            human_expl = latest_impact.get("human_explanation") or (itinerary_history[-1].get("human_explanation") if itinerary_history else None)
            if human_expl:
                st.markdown(
                    f"""
                    <div style="background: rgba(59, 130, 246, 0.08); border-left: 4px solid #3B82F6; padding: 12px 16px; border-radius: 4px; margin-bottom: 20px;">
                        <div style="font-weight: 600; color: #93C5FD; font-size: 0.85rem; text-transform: uppercase;">WHY DID THE ITINERARY CHANGE?</div>
                        <div style="color: #F1F5F9; font-size: 1rem; margin-top: 4px;">{human_expl}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Node execution status badges
            st.markdown("#### Component Execution Matrix (Selective Reuse)")
            st.caption("Verifies affected nodes re-run while unaffected nodes are safely reused without token expenditure:")

            badge_map = {
                "RERUN": ("badge-rerun", "🔄 RERUN"),
                "REUSED": ("badge-reused", "💾 REUSED"),
                "INVALIDATED": ("badge-warning", "⚠️ INVALIDATED"),
                "SKIPPED": ("badge", "⏭️ SKIPPED"),
                "FAILED": ("badge-failed", "❌ FAILED"),
            }

            nodes_display = [
                ("flights", "Flight Agent"),
                ("hotels", "Hotel Agent"),
                ("activities", "Activity Agent"),
                ("weather", "Weather Agent"),
                ("research", "Research Agent"),
                ("budget", "Budget Engine"),
                ("validator", "Validation Engine"),
                ("itinerary", "Itinerary Synthesis"),
            ]

            cols = st.columns(4)
            for idx, (node_key, label) in enumerate(nodes_display):
                mode = exec_modes.get(node_key, "REUSED" if replan_count > 0 else "COMPLETED")
                badge_class, badge_label = badge_map.get(mode, ("badge-completed", "✅ COMPLETED"))
                with cols[idx % 4]:
                    st.markdown(
                        f"""
                        <div class="travel-card" style="padding: 10px 12px; margin-bottom: 8px;">
                            <div style="font-weight: 600; font-size: 0.9rem; color: #F8FAFC;">{label}</div>
                            <div style="margin-top: 4px;"><span class="badge {badge_class}">{badge_label}</span></div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    with tab_simulate:
        st.markdown("### 🧪 Test Live Dynamic Replanning")
        st.markdown("Inject a synthetic disruption event to verify selective graph re-execution and state version advancement.")

        with st.form("simulate_disruption_form"):
            event_type = st.selectbox(
                "Disruption Event Type",
                [
                    "FLIGHT_CANCELLATION",
                    "HOTEL_UNAVAILABLE",
                    "WEATHER_DISRUPTION",
                    "ACTIVITY_CANCELLED",
                    "BUDGET_REDUCED",
                    "DATE_SHIFTED",
                ],
            )
            severity = st.selectbox("Severity Level", ["CRITICAL", "HIGH", "MEDIUM", "LOW"])
            disruption_desc = st.text_input(
                "Disruption Description / Reason",
                value="Severe torrential rain forecast for scheduled outdoor activities.",
            )

            submit_disruption = st.form_submit_button("⚡ Inject Disruption & Replan", type="primary", use_container_width=True)

        if submit_disruption:
            with st.spinner("Analyzing disruption impact and selectively replanning..."):
                try:
                    # Construct ChangeEvent
                    event = ChangeEvent(
                        event_type=ChangeEventType(event_type.lower()),
                        severity=ChangeEventSeverity(severity.lower()),
                        description=disruption_desc,
                        impacted_date=str(trip.start_date),
                    )

                    # Execute replanning through replanning service
                    result_state = replanning_service.handle_change_event(
                        event=event,
                        current_state=travel_state,
                    )

                    # Update session state with new version and telemetry
                    st.session_state["travel_state"] = result_state
                    st.session_state["workflow_status"] = "REPLAN_COMPLETED"

                    st.success(f"✅ Dynamic replanning successful! Advanced to Itinerary v{result_state.get('itinerary_version', itinerary_ver + 1)}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Replanning simulation encountered an error: {str(e)}")

    with tab_history:
        st.markdown("### 📜 Itinerary Version History")
        if not itinerary_history:
            st.info("ℹ️ No historical versions archived yet. When replanning modifies the trip, previous snapshots appear here.")
        else:
            for idx, hist in enumerate(reversed(itinerary_history), start=1):
                ver_num = hist.get("version", idx)
                reason = hist.get("change_reason", "Disruption update")
                timestamp = hist.get("timestamp", "Recent")
                with st.expander(f"📦 Version {ver_num} — {reason[:40]}"):
                    st.markdown(f"**Created At**: `{timestamp}`")
                    st.markdown(f"**Change Reason**: {reason}")
                    if hist.get("human_explanation"):
                        st.markdown(f"**Explanation**: {hist.get('human_explanation')}")
                    if hist.get("days"):
                        st.caption(f"Contained {len(hist.get('days'))} scheduled days.")
