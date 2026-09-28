"""My Trips page displaying saved trips and historical sessions."""

import streamlit as st
from app.state.session import get_current_trip, navigate_to
from app.components.trip_summary_card import render_trip_summary_card


def render_my_trips_page() -> None:
    """Render saved trips list or empty state."""
    st.title("My Trips")
    st.markdown("View current and past saved travel itineraries and replanning histories.")

    st.markdown("---")

    active_trip = get_current_trip()
    recent = st.session_state.get("recent_trips", [])

    if active_trip:
        st.subheader("Current Active Trip")
        render_trip_summary_card(active_trip)
        st.markdown("---")

    if recent:
        st.subheader(f"Recent In-Memory Trip Requests ({len(recent)})")
        for idx, t in enumerate(recent, 1):
            with st.container():
                st.markdown(
                    f"""
                    <div style="
                        border: 1px solid rgba(128, 128, 128, 0.2);
                        border-radius: 6px;
                        padding: 12px 16px;
                        margin-bottom: 10px;
                        background: rgba(255, 255, 255, 0.02);
                    ">
                        <strong>#{idx} {t['origin']} &rarr; {t['destination']}</strong> | 
                        Dates: {t['start_date']} to {t['end_date']} | 
                        Budget: {t['currency']} {t['budget']:,.2f} | 
                        Travelers: {t['travelers']} | 
                        Status: <code>{t['status']}</code>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.info("No saved trips found in active session.")

    st.markdown("---")
    st.info(
        "ℹ️ **Persistent Storage (Phase 3)**: Long-term trip persistence, multi-user isolation, and Row Level Security (RLS) will be connected via Supabase in Phase 3. Currently trips are held in local session state."
    )

    if st.button("➕ Plan Another Trip"):
        navigate_to("New Trip")
        st.rerun()
