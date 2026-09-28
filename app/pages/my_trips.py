"""My Trips page displaying persisted trips from repository."""

from datetime import datetime
import streamlit as st
from models.travel_request import (
    TravelRequest,
    TravelerPreferences,
    TripConstraints,
)
from app.state.session import (
    get_current_user,
    set_current_trip,
    get_current_trip,
    navigate_to,
)
from app.components.trip_summary_card import render_trip_summary_card
from repositories import trip_repository


def render_my_trips_page() -> None:
    """Render saved trips list for the active user with open/activate support."""
    st.title("My Trips")
    st.markdown("View and manage your travel itineraries, active planning sessions, and historical records.")

    st.markdown("---")

    current_user = get_current_user()
    user_id = current_user["id"]

    # Active Trip Highlight
    active_trip = get_current_trip()
    if active_trip:
        st.subheader("Currently Active Trip")
        render_trip_summary_card(active_trip)
        st.markdown("---")

    # Fetch trips for current user
    try:
        trips = trip_repository.list_user_trips(user_id=user_id)
    except Exception as e:
        st.error(f"Failed to load trips: {str(e)}")
        trips = []

    st.subheader(f"Saved Trips ({len(trips)})")

    if not trips:
        st.info("No saved trips found for your account. Create your first trip using the New Trip form.")
        if st.button("➕ Plan a Trip", type="primary"):
            navigate_to("New Trip")
            st.rerun()
        return

    for idx, trip in enumerate(trips, 1):
        with st.container():
            is_demo = trip.get("is_demo", False)
            demo_badge = '<span style="background: rgba(255, 193, 7, 0.15); color: #FFD54F; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">Demo data — not persisted</span>' if is_demo else '<span style="background: rgba(76, 175, 80, 0.15); color: #81C784; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">Supabase Persisted</span>'

            col_info, col_action = st.columns([4, 1])

            with col_info:
                st.markdown(
                    f"""
                    <div style="border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 6px; padding: 12px 16px; margin-bottom: 8px; background: rgba(255, 255, 255, 0.02);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span style="font-size: 1.1rem; font-weight: 600; color: #64B5F6;">
                                ✈️ {trip['origin']} &rarr; {trip['destination']}
                            </span>
                            <div>
                                {demo_badge}
                                <span style="margin-left: 8px; font-size: 0.8rem; background: rgba(30, 136, 229, 0.2); color: #90CAF9; padding: 2px 8px; border-radius: 4px;">
                                    {trip['status']}
                                </span>
                            </div>
                        </div>
                        <div style="display: flex; gap: 18px; font-size: 0.85rem; color: #B0BEC5;">
                            <span>📅 <strong>Dates:</strong> {trip['start_date']} to {trip['end_date']}</span>
                            <span>👥 <strong>Travelers:</strong> {trip['travelers']}</span>
                            <span>💵 <strong>Budget:</strong> {trip['currency']} {float(trip['budget']):,.2f}</span>
                            <span>🕒 <strong>Created:</strong> {trip.get('created_at', '')[:10]}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col_action:
                st.write("")
                if st.button("📂 Open Trip", key=f"open_trip_{trip['id']}", use_container_width=True):
                    # Reconstruct TravelRequest model to set as current
                    pref_data = trip.get("preferences", {}) or {}
                    reconstructed = TravelRequest(
                        origin=trip["origin"],
                        destination=trip["destination"],
                        start_date=datetime.fromisoformat(str(trip["start_date"])).date() if isinstance(trip["start_date"], str) else trip["start_date"],
                        end_date=datetime.fromisoformat(str(trip["end_date"])).date() if isinstance(trip["end_date"], str) else trip["end_date"],
                        travelers=trip["travelers"],
                        budget=float(trip["budget"]),
                        currency=trip["currency"],
                        preferences=TravelerPreferences(
                            interests=pref_data.get("preferences", []),
                            pace="moderate",
                            accommodation_type=pref_data.get("accommodation_preference", "hotel").lower(),
                        ),
                        constraints=TripConstraints(),
                    )
                    set_current_trip(reconstructed, trip_id=trip["id"])
                    st.success(f"Activated trip {trip['destination']}!")
                    st.rerun()

    st.markdown("---")
    if st.button("➕ Plan Another Trip"):
        navigate_to("New Trip")
        st.rerun()
