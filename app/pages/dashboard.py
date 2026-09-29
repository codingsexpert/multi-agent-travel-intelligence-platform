"""Polished Travel Intelligence Command Center Dashboard.

Phase 17: Production Travel Command Center UI/UX.
Displays:
- Professional workspace header & platform status
- Active Trip summary (destination, dates, travellers, budget, version, status)
- Component-level Planning Status (Planner, Flights, Hotels, Activities, Weather, Research, Budget, Validation, Itinerary)
- Recent Trips history
- Pending Approvals count & quick action
- Recent Replanning Changes
- Budget Summary cards
- Upcoming Itinerary highlight
"""

from typing import Dict, Any, List
import streamlit as st
from config.settings import get_settings
from services.health_service import get_health_status
from app.state.session import get_current_trip, navigate_to
from app.components.styles import inject_custom_styles
from app.components.empty_state import render_empty_state


def render_dashboard_page() -> None:
    """Render the primary Travel Command Center dashboard."""
    inject_custom_styles()

    settings = get_settings()
    health = get_health_status(settings)
    active_trip = get_current_trip()
    travel_state: Dict[str, Any] = st.session_state.get("travel_state", {})
    itinerary_ver = travel_state.get("itinerary_version", 1)
    replan_count = travel_state.get("replan_count", 0)
    wf_status = st.session_state.get("workflow_status", "IDLE")

    # Header Bar
    st.markdown(
        """
        <div class="main-header">
            <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap;">
                <div>
                    <div class="main-title">✈️ Travel Intelligence Command Center</div>
                    <div class="main-subtitle">Enterprise multi-agent travel orchestration, dynamic replanning, and deterministic financial governance.</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Top Status KPI Strip
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("System Health", "Healthy" if health.overall_status == "HEALTHY" else "Degraded", "10/10 Components")
    with k2:
        mode_badge = "DEMO (Offline)" if health.demo_mode else f"LIVE ({health.environment})"
        st.metric("Runtime Environment", mode_badge)
    with k3:
        st.metric("Active Workflow", wf_status)
    with k4:
        st.metric("Itinerary Version", f"v{itinerary_ver}" if active_trip else "None")

    st.markdown("---")

    # Active Trip & Planning Status Section
    if active_trip:
        st.markdown("### 🧭 Active Travel Session")
        c_trip1, c_trip2 = st.columns([2, 1])

        with c_trip1:
            st.markdown(
                f"""
                <div class="travel-card">
                    <div class="travel-card-header">
                        <span style="font-size: 1.25rem; font-weight: 700; color: #F8FAFC;">
                            {active_trip.origin} &rarr; {active_trip.destination}
                        </span>
                        <span class="badge badge-demo">VERSION {itinerary_ver}</span>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 6px;">
                        <div>
                            <div style="font-size: 0.75rem; color: #94A3B8; text-transform: uppercase;">Dates</div>
                            <div style="font-size: 0.95rem; font-weight: 600; color: #E2E8F0;">{active_trip.start_date} to {active_trip.end_date}</div>
                            <div style="font-size: 0.8rem; color: #64748B;">({active_trip.duration_days} Days)</div>
                        </div>
                        <div>
                            <div style="font-size: 0.75rem; color: #94A3B8; text-transform: uppercase;">Travelers</div>
                            <div style="font-size: 0.95rem; font-weight: 600; color: #E2E8F0;">{active_trip.travelers} Guest(s)</div>
                        </div>
                        <div>
                            <div style="font-size: 0.75rem; color: #94A3B8; text-transform: uppercase;">Budget Cap</div>
                            <div style="font-size: 0.95rem; font-weight: 600; color: #34D399;">{active_trip.currency} {active_trip.budget:,.2f}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c_trip2:
            st.markdown(
                f"""
                <div class="travel-card" style="height: calc(100% - 1rem); display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <div style="font-size: 0.75rem; text-transform: uppercase; color: #94A3B8; font-weight: 600;">Trip Actions</div>
                        <div style="font-size: 0.85rem; color: #CBD5E1; margin: 6px 0;">Quickly inspect schedules, budget allocations, or trigger dynamic replanning.</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("🗓️ Itinerary", use_container_width=True):
                    navigate_to("Itinerary")
                    st.rerun()
            with col_b2:
                if st.button("💰 Budget", use_container_width=True):
                    navigate_to("Budget")
                    st.rerun()

        # Component Planning Statuses (Section 3 requirement)
        st.markdown("### 📋 Multi-Agent Planning Status")
        st.caption("Operational status across autonomous domain agents and deterministic calculation engines:")

        components = [
            ("Planner", bool(travel_state.get("planner_result")), "LLM"),
            ("Flights", bool(travel_state.get("flight_options")), "MCP"),
            ("Hotels", bool(travel_state.get("hotel_options")), "MCP"),
            ("Activities", bool(travel_state.get("activity_options")), "MCP"),
            ("Weather", bool(travel_state.get("weather_forecast")), "MCP"),
            ("Research", bool(travel_state.get("destination_research")), "RAG/Web"),
            ("Budget", bool(travel_state.get("budget_summary")), "DETERMINISTIC"),
            ("Validation", bool(travel_state.get("validation_result")), "DETERMINISTIC"),
            ("Itinerary", bool(travel_state.get("final_itinerary")), "SYNTHESIS"),
        ]

        status_cols = st.columns(3)
        for idx, (name, is_done, role) in enumerate(components):
            if is_done:
                status_label = "COMPLETED"
                status_badge = "badge-completed"
            elif wf_status == "RUNNING":
                status_label = "RUNNING"
                status_badge = "badge-running"
            elif wf_status == "WAITING_FOR_APPROVAL":
                status_label = "WAITING FOR APPROVAL"
                status_badge = "badge-approval"
            else:
                status_label = "NOT STARTED"
                status_badge = "badge"

            with status_cols[idx % 3]:
                st.markdown(
                    f"""
                    <div class="travel-card" style="padding: 10px 14px; margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong style="color: #F8FAFC;">{name}</strong>
                                <span style="font-size: 0.7rem; color: #64748B; margin-left: 6px;">({role})</span>
                            </div>
                            <span class="badge {status_badge}">{status_label}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    else:
        # Useful Empty State for Dashboard
        render_empty_state(
            title="No Active Trip in Command Center",
            description="Welcome to the Travel Intelligence Platform. Define your destination, timing, budget constraints, and traveler preferences to launch the multi-agent planning workflow.",
            icon="✈️",
            action_label="➕ Create Your First Trip",
            target_page="New Trip",
        )

    st.markdown("---")

    # Operations & Recent Activity Grid (Recent Trips, Approvals, Changes, Budget Summary)
    col_act1, col_act2 = st.columns(2)

    with col_act1:
        st.markdown("### 🛡️ Pending Approvals")
        try:
            from services.approval_service import approval_service
            from app.state.session import get_current_user
            user = get_current_user()
            pending = approval_service.get_pending_approvals(user_id=user["id"])
            if pending:
                st.warning(f"⚠️ **{len(pending)} High-Impact Action(s)** await your authorization.")
                if st.button("🛡️ Review Approvals Now", type="primary"):
                    navigate_to("Approvals")
                    st.rerun()
            else:
                st.markdown(
                    """
                    <div class="travel-card">
                        <div style="color: #34D399; font-weight: 600;">✅ Zero Pending Approvals</div>
                        <div style="font-size: 0.85rem; color: #94A3B8; margin-top: 4px;">All high-impact transactional operations are cleared.</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        except Exception:
            st.caption("Approval queue idle.")

        st.markdown("### 📂 Recent Trips History")
        recent_trips: List[Dict[str, Any]] = st.session_state.get("recent_trips", [])
        if recent_trips:
            for r_trip in recent_trips[:3]:
                st.markdown(
                    f"""
                    <div class="travel-card" style="padding: 10px 12px; margin-bottom: 6px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 600; color: #E2E8F0;">{r_trip.get('origin')} &rarr; {r_trip.get('destination')}</span>
                            <span style="font-size: 0.8rem; color: #34D399;">{r_trip.get('currency')} {r_trip.get('budget', 0):,.0f}</span>
                        </div>
                        <div style="font-size: 0.75rem; color: #64748B;">{r_trip.get('start_date')} to {r_trip.get('end_date')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No previous trips saved in this browser session.")

    with col_act2:
        st.markdown("### 🔄 Recent Replanning Activity")
        replan_reasons: List[str] = travel_state.get("replan_reasons", [])
        if replan_reasons:
            for reason in replan_reasons[-3:]:
                st.markdown(
                    f"""
                    <div class="travel-card" style="padding: 10px 12px; margin-bottom: 6px; border-left: 3px solid #F59E0B;">
                        <div style="font-weight: 600; color: #FBBF24; font-size: 0.85rem;">DISRUPTION EVENT</div>
                        <div style="color: #E2E8F0; font-size: 0.85rem; margin-top: 2px;">{reason}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                """
                <div class="travel-card">
                    <div style="color: #94A3B8; font-size: 0.85rem;">No dynamic replans triggered. Initial itinerary remains active.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("### 💰 Budget Summary Snapshot")
        budget_sum = travel_state.get("budget_summary")
        if budget_sum:
            est_cost = getattr(budget_sum, "total_cost", 0.0) if hasattr(budget_sum, "total_cost") else budget_sum.get("total_cost", 0.0)
            status_val = getattr(budget_sum, "status", "WITHIN_BUDGET") if hasattr(budget_sum, "status") else budget_sum.get("status", "WITHIN_BUDGET")
            st.markdown(
                f"""
                <div class="travel-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #94A3B8; font-size: 0.85rem;">Total Estimated Cost:</span>
                        <span style="font-weight: 700; color: #34D399; font-size: 1.1rem;">{active_trip.currency if active_trip else '$'} {est_cost:,.2f}</span>
                    </div>
                    <div style="margin-top: 6px;"><span class="badge badge-completed">{status_val}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.caption("Budget engine has not run yet.")
