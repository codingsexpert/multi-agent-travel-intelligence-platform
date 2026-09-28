"""Flight options and aviation routing page."""

import streamlit as st
from app.state.session import get_current_trip


def render_flights_page() -> None:
    """Render flight search results and candidate routing."""
    st.title("Flights & Transit Routing")
    st.markdown("Aviation routing, airline options, transit durations, and baggage policies.")

    st.markdown("---")

    active_trip = get_current_trip()
    if active_trip:
        st.subheader(f"Route: {active_trip.origin} &rarr; {active_trip.destination}")
        st.caption(f"Dates: {active_trip.start_date} to {active_trip.end_date} | Class: {active_trip.preferences.cabin_class.replace('_', ' ').capitalize()}")

    st.info(
        "ℹ️ **Flight Agent Offline**: Flight search, corridor analysis, and live Amadeus API / mock MCP flight servers will be connected in Phase 5 & Phase 7. No fake flight results are shown."
    )

    with st.expander("✈️ Target Flight Search Capabilities (Phase 5 & 7)", expanded=True):
        st.markdown(
            """
            - **Non-stop vs. Layover filtering** based on user constraints
            - **Baggage allowance & cabin class comparison**
            - **Total elapsed transit duration & layover risk scoring**
            - **Amadeus Flight API integration** with offline mock fallback
            """
        )
