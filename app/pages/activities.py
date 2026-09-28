"""Activities, landmarks, and culinary experiences page."""

import streamlit as st
from app.state.session import get_current_trip


def render_activities_page() -> None:
    """Render curated activities and daily experiences from Activity Agent."""
    st.title("Activities & Experiences")
    st.markdown("Cultural landmarks, dining discoveries, guided experiences, and leisure spots.")

    st.markdown("---")

    active_trip = get_current_trip()
    travel_state = st.session_state.get("travel_state", {})
    activities = travel_state.get("activities", [])

    if active_trip:
        st.subheader(f"Curated for: {active_trip.destination}")
        if active_trip.preferences.interests:
            st.caption(f"Target Interests: {', '.join(active_trip.preferences.interests)}")

    if not activities:
        st.info(
            "ℹ️ **No Activities Curated Yet**: Plan a trip from **New Trip** or **Conversation** to execute the multi-agent workflow and generate candidate experiences."
        )
        return

    st.success(f"🎯 **Activity Agent Deliverables ({len(activities)} Curated Experiences)**")
    st.caption("⚠️ **DEMO_DATA**: These options are generated deterministically by the mock Activity Agent. Full day-by-day itinerary synthesis will be orchestrated in Phase 6.")

    for idx, act in enumerate(activities, 1):
        with st.container():
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"### {idx}. {act.get('name', 'Experience')}")
                st.markdown(f"🏷️ **Category**: `{act.get('category', 'General')}` | 📍 **Location**: {act.get('location', 'Destination')}")
                st.markdown(f"{act.get('description', '')}")
                st.caption(f"Source: `{act.get('source', 'DEMO_DATA')}`")
            with c2:
                curr = act.get('currency', 'USD')
                cost = act.get('estimated_cost', 0.0)
                cost_str = f"{curr} {cost:,.2f}" if cost > 0 else "Free Admission"
                st.metric(label="Estimated Cost", value=cost_str)
                st.markdown(f"⏱️ **Duration**: {act.get('duration', '2h')}")
                st.markdown(f"🌅 **Best Time**: {act.get('best_time', 'Flexible')}")
                st.info("Demo Data Item", icon="ℹ️")
            st.markdown("---")
