"""Dashboard page for Travel Command Center."""

import streamlit as st
from config.settings import get_settings
from services.health_service import get_health_status
from app.state.session import get_current_trip, navigate_to
from app.components.trip_summary_card import render_trip_summary_card


def render_dashboard_page() -> None:
    """Render main platform dashboard."""
    settings = get_settings()
    health = get_health_status(settings)
    active_trip = get_current_trip()

    # Header
    st.title("Travel Intelligence Command Center")
    st.markdown(
        "A multi-agent autonomous system for stateful travel planning, deterministic budget optimization, and real-time disruption replanning."
    )

    st.markdown("---")

    # Top Status Bar
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Platform Status**")
        if health.overall_status == "HEALTHY":
            st.success("🟢 Operating (Healthy)")
        elif health.overall_status == "DEGRADED":
            st.warning("🟡 Degraded")
        else:
            st.error("🔴 Unhealthy")

    with col2:
        st.markdown("**Execution Mode**")
        if health.demo_mode:
            st.info("🟢 DEMO_MODE (Offline & Mock Tools)")
        else:
            st.info(f"🔵 {health.environment} (Live APIs)")

    with col3:
        st.markdown("**Workflow State**")
        st.write(f"`{st.session_state.get('workflow_status', 'IDLE')}`")

    # Quick Action Banner
    st.markdown("---")
    qa_col1, qa_col2 = st.columns([3, 1])
    with qa_col1:
        if active_trip:
            st.markdown(f"**Active Session:** Currently planning trip to **{active_trip.destination}** ({active_trip.duration_days} days).")
        else:
            st.markdown("**Ready for new requirements:** Configure a new destination, dates, budget, and travel preferences to start.")
    with qa_col2:
        if st.button("➕ Create New Trip", type="primary", use_container_width=True):
            navigate_to("New Trip")
            st.rerun()

    # Active Trip Card if available
    if active_trip:
        st.markdown("### Active Trip Overview")
        render_trip_summary_card(active_trip)

    # Architecture Status
    st.markdown("### Architecture Component Readiness")
    st.caption("Live status of subsystems across implementation phases:")

    a1, a2, a3, a4, a5 = st.columns(5)
    with a1:
        st.markdown("**LangGraph**")
        st.caption("Orchestration")
        st.info("Foundation Ready (Phase 4)")

    with a2:
        st.markdown("**MCP Protocol**")
        st.caption("Tools Integration")
        st.warning("Not Initialized (Phase 7)")

    with a3:
        st.markdown("**pgvector RAG**")
        st.caption("Domain Knowledge")
        st.warning("Not Initialized (Phase 9)")

    with a4:
        st.markdown("**Supabase**")
        st.caption("Persistence & Auth")
        if health.supabase_status == "Connected":
            st.success("Configured")
        else:
            st.caption("Not Configured (Phase 3)")

    with a5:
        st.markdown("**LangSmith**")
        st.caption("Observability")
        if health.langsmith_status == "Configured":
            st.success("Configured")
        else:
            st.caption("Not Configured (Phase 14)")

    st.markdown("---")

    # Recent Trips Placeholder
    st.markdown("### Recent Trips & History")
    recent = st.session_state.get("recent_trips", [])
    if recent:
        for t in recent:
            with st.container():
                st.write(
                    f"✈️ **{t['origin']} &rarr; {t['destination']}** | {t['start_date']} to {t['end_date']} | {t['currency']} {t['budget']:,.0f} | Status: `{t['status']}`"
                )
    else:
        st.info("No recent trips found in session memory. Create your first trip using the New Trip form.")
