"""Day-by-day itinerary page layout and placeholders."""

import streamlit as st
from app.state.session import get_current_trip
from app.components.trip_summary_card import render_trip_summary_card


def render_activity_slot(
    time_of_day: str,
    time_range: str,
    title: str,
    location: str,
    cost: str,
    transit: str,
    weather: str,
    source: str,
) -> None:
    """Render a structural placeholder slot for future itinerary items."""
    with st.container():
        st.markdown(
            f"""
            <div style="
                border-left: 3px solid #42A5F5;
                padding: 10px 14px;
                margin-bottom: 12px;
                background-color: rgba(255, 255, 255, 0.02);
                border-radius: 0 6px 6px 0;
            ">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <span style="font-weight: 600; color: #90CAF9; font-size: 0.9rem;">{time_of_day.upper()} ({time_range})</span>
                    <span style="font-size: 0.8rem; color: #81C784;">Estimated Cost: {cost}</span>
                </div>
                <div style="font-weight: 500; font-size: 1.05rem; margin: 4px 0;">{title}</div>
                <div style="display: flex; gap: 16px; font-size: 0.8rem; color: #B0BEC5; flex-wrap: wrap;">
                    <span>📍 <strong>Location:</strong> {location}</span>
                    <span>🚆 <strong>Transit:</strong> {transit}</span>
                    <span>⛅ <strong>Weather:</strong> {weather}</span>
                    <span>📚 <strong>Source:</strong> {source}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_itinerary_page() -> None:
    """Render empty itinerary structure and day-by-day activity placeholders."""
    st.title("Trip Itinerary")
    st.markdown("Chronological, day-by-day schedule with timing, transit buffers, and budget tracking.")

    st.markdown("---")

    active_trip = get_current_trip()

    if not active_trip:
        st.info("ℹ️ No active trip found. Visit the **New Trip** page to submit trip requirements.")
        return

    # Trip Summary
    st.subheader("Trip Summary")
    render_trip_summary_card(active_trip, show_id=False)

    st.markdown("---")

    # Placeholder banner
    st.info(
        "ℹ️ **Empty Itinerary State**: The Itinerary Agent and Activity Agent will synthesize approved activities, verified transit times, and weather windows in Phase 5 & Phase 6. The slots below illustrate the target data structure."
    )

    # Day 1 Structure
    with st.expander("📅 Day 1: Arrival, Neighborhood Exploration & Welcome Dinner", expanded=True):
        st.caption("Theme: Cultural immersion & low-stress orientation")

        render_activity_slot(
            time_of_day="Morning",
            time_range="09:00 - 12:00",
            title="[Slot] Airport Arrival, Transit & Hotel Check-in",
            location="Arrival Terminal & Hotel District",
            cost="Included in Transit / Lodging",
            transit="45 min Express Train",
            weather="Forecast: 18°C, Partly Cloudy",
            source="Flight Agent & OpenWeather API",
        )

        render_activity_slot(
            time_of_day="Afternoon",
            time_range="13:30 - 16:30",
            title="[Slot] Historic District Walking Tour & Local Landmark",
            location="Old Town Center",
            cost="$25.00 / person",
            transit="15 min Walking",
            weather="Forecast: 20°C, Mild",
            source="Activity Agent via Places Tools",
        )

        render_activity_slot(
            time_of_day="Evening",
            time_range="18:30 - 21:00",
            title="[Slot] Traditional Regional Cuisine Experience",
            location="Culinary Arcade",
            cost="$45.00 / person",
            transit="10 min Metro",
            weather="Forecast: 16°C, Clear",
            source="pgvector RAG Dining Guide",
        )

    # Day 2 Structure
    with st.expander("📅 Day 2: Iconic Sights & Immersive Experiences", expanded=True):
        st.caption("Theme: High-priority attractions & cultural highlights")

        render_activity_slot(
            time_of_day="Morning",
            time_range="09:30 - 12:30",
            title="[Slot] Major Architectural Landmark & Gardens",
            location="Central Cultural Quarter",
            cost="$15.00 / person",
            transit="20 min Transit",
            weather="Forecast: 19°C, Sunny",
            source="Activity Agent / Curated Knowledge Base",
        )

        render_activity_slot(
            time_of_day="Afternoon",
            time_range="14:00 - 17:00",
            title="[Slot] Renowned Art Museum & Exhibitions",
            location="Museum District",
            cost="$22.00 / person",
            transit="15 min Walking",
            weather="Forecast: 21°C, Indoor Friendly",
            source="Places API",
        )

        render_activity_slot(
            time_of_day="Evening",
            time_range="19:00 - 21:30",
            title="[Slot] Evening Observation Deck & Sunset Viewpoint",
            location="Skyline Tower",
            cost="$30.00 / person",
            transit="15 min Metro",
            weather="Forecast: 15°C, Good Visibility",
            source="Tavily Live Web Search",
        )
