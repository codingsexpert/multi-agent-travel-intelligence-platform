"""Activities, landmarks, and culinary experiences page."""

import streamlit as st
from app.state.session import get_current_trip


def render_activities_page() -> None:
    """Render curated activities and daily experiences."""
    st.title("Activities & Experiences")
    st.markdown("Cultural landmarks, dining discoveries, guided experiences, and leisure spots.")

    st.markdown("---")

    active_trip = get_current_trip()
    if active_trip:
        st.subheader(f"Experiences for: {active_trip.destination}")
        if active_trip.preferences.interests:
            st.caption(f"Interests: {', '.join(active_trip.preferences.interests)}")

    st.info(
        "ℹ️ **Activity Agent Offline**: Daily activity curation, opening hours verification, and fatigue score balancing will be connected in Phase 5. No fake activity data is shown."
    )

    with st.expander("🎯 Target Activity Curation Capabilities (Phase 5)", expanded=True):
        st.markdown(
            """
            - **Interest-aligned curation** (culinary, historical, outdoors, photography)
            - **Travel pacing adjustment** (relaxed vs. fast-paced fatigue management)
            - **Temporal scheduling** avoiding midday heat or overcrowded peak hours
            - **Grounded recommendations** from curated pgvector RAG guides and Places APIs
            """
        )
