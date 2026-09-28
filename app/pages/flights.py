"""Flight options and aviation routing page."""

import streamlit as st
from app.state.session import get_current_trip


def render_flights_page() -> None:
    """Render structured flight search results and candidate routing from Flight Agent."""
    st.title("Flights & Transit Routing")
    st.markdown("Aviation routing, candidate airlines, flight durations, layovers, and pricing.")

    st.markdown("---")

    active_trip = get_current_trip()
    travel_state = st.session_state.get("travel_state", {})
    flight_options = travel_state.get("flight_options", [])

    if active_trip:
        st.subheader(f"Route: {active_trip.origin} &rarr; {active_trip.destination}")
        st.caption(
            f"Dates: {active_trip.start_date} to {active_trip.end_date} | "
            f"Travelers: {active_trip.travelers} | "
            f"Budget Limit: {active_trip.currency} {active_trip.budget:,.2f}"
        )

    if not flight_options:
        st.info(
            "ℹ️ **No Flights Discovered Yet**: Plan a trip from **New Trip** or **Conversation** to execute the multi-agent workflow and generate candidate flight options."
        )
        return

    st.success(f"✈️ **Flight Agent Deliverables ({len(flight_options)} Options Found)**")
    st.caption("⚠️ **DEMO_DATA**: These options are generated deterministically by the mock Flight Agent for evaluation. Booking and live API purchasing will be connected in Phase 7.")

    for idx, flight in enumerate(flight_options, 1):
        with st.container():
            c1, c2, c3 = st.columns([3, 2, 2])
            with c1:
                st.markdown(f"### Option {idx}: {flight.get('airline', 'Airline')}")
                st.markdown(f"**Flight Number**: `{flight.get('flight_number')}` ({flight.get('cabin_class', 'Economy')})")
                st.markdown(f"🛫 **Departure**: {flight.get('departure_airport')} at `{flight.get('departure_time')}`")
                st.markdown(f"🛬 **Arrival**: {flight.get('arrival_airport')} at `{flight.get('arrival_time')}`")
            with c2:
                st.markdown(f"⏱️ **Duration**: {flight.get('duration', 'N/A')}")
                stops = flight.get('stops', 0)
                stops_text = "Nonstop Direct" if stops == 0 else f"{stops} Stop(s)"
                st.markdown(f"🔄 **Routing**: {stops_text}")
                st.caption(f"Source: `{flight.get('source', 'DEMO_DATA')}`")
            with c3:
                curr = flight.get('currency', 'USD')
                price = flight.get('price', 0.0)
                st.metric(label="Total Fare (All Travelers)", value=f"{curr} {price:,.2f}")
                st.caption(f"Status: **{flight.get('availability_status', 'Available')}**")
                st.info("Demo Data Only — Booking Disabled", icon="🔒")
            st.markdown("---")
