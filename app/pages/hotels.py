"""Hotels and lodging options page."""

import streamlit as st
from app.state.session import get_current_trip


def render_hotels_page() -> None:
    """Render accommodations and lodging alternatives discovered by Hotel Agent."""
    st.title("Hotels & Accommodations")
    st.markdown("Hospitality options, neighborhood proximity, guest capacity, and amenities.")

    st.markdown("---")

    active_trip = get_current_trip()
    travel_state = st.session_state.get("travel_state", {})
    hotel_options = travel_state.get("hotel_options", [])

    if active_trip:
        st.subheader(f"Lodging in: {active_trip.destination}")
        st.caption(
            f"Dates: {active_trip.start_date} to {active_trip.end_date} | "
            f"Guests: {active_trip.travelers} | "
            f"Preference: {active_trip.preferences.accommodation_type.capitalize()}"
        )

    if not hotel_options:
        st.info(
            "ℹ️ **No Accommodations Discovered Yet**: Plan a trip from **New Trip** or **Conversation** to execute the multi-agent workflow and generate candidate hotels."
        )
        return

    st.success(f"🏨 **Hotel Agent Deliverables ({len(hotel_options)} Properties Discovered)**")
    st.caption("⚠️ **DEMO_DATA**: These options are generated deterministically by the mock Hotel Agent for evaluation. Direct booking and real-time inventory will be connected in Phase 7.")

    for idx, hotel in enumerate(hotel_options, 1):
        with st.container():
            c1, c2, c3 = st.columns([3, 2, 2])
            with c1:
                st.markdown(f"### {idx}. {hotel.get('name', 'Property')}")
                stars = hotel.get('stars', 4)
                star_icons = "⭐" * stars
                st.markdown(f"{star_icons} ({hotel.get('rating', 4.5)}/5.0 rating)")
                st.markdown(f"📍 **Neighborhood**: {hotel.get('location', 'Central')}")
                st.markdown(f"🛏️ **Room**: {hotel.get('room_type', 'Standard')}")
            with c2:
                st.markdown("✨ **Amenities & Perks**:")
                amenities = hotel.get("amenities", [])
                for amenity in amenities[:4]:
                    st.markdown(f"• {amenity}")
                st.caption(f"Source: `{hotel.get('source', 'DEMO_DATA')}`")
            with c3:
                curr = hotel.get('currency', 'USD')
                rate = hotel.get('price_per_night', 0.0)
                total = hotel.get('total_price', 0.0)
                st.metric(label="Nightly Rate", value=f"{curr} {rate:,.2f}")
                st.caption(f"Estimated Total: **{curr} {total:,.2f}**")
                st.caption(f"Status: **{hotel.get('availability_status', 'Available')}**")
                st.info("Demo Data Only — Reservation Disabled", icon="🔒")
            st.markdown("---")
