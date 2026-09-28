"""Hotels and lodging options page."""

import streamlit as st
from app.state.session import get_current_trip


def render_hotels_page() -> None:
    """Render accommodations and lodging alternatives."""
    st.title("Hotels & Accommodations")
    st.markdown("Hospitality options, neighborhood proximity, guest capacity, and amenities.")

    st.markdown("---")

    active_trip = get_current_trip()
    if active_trip:
        st.subheader(f"Lodging in: {active_trip.destination}")
        st.caption(f"Preference: {active_trip.preferences.accommodation_type.capitalize()} | Guests: {active_trip.travelers}")

    st.info(
        "ℹ️ **Hotel Agent Offline**: Accommodations discovery, proximity scoring to planned activities, and live hotel inventory via MCP will be connected in Phase 5 & Phase 7. No fake hotel data is shown."
    )

    with st.expander("🏨 Target Hotel Search Capabilities (Phase 5 & 7)", expanded=True):
        st.markdown(
            """
            - **Geographic clustering** near target attractions
            - **Star rating & review sentiment analysis**
            - **Free cancellation & refundable rate prioritization**
            - **Budget band adherence** enforced by the Budget Engine
            """
        )
