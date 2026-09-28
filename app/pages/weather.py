"""Weather forecast and seasonal climate intelligence page."""

import streamlit as st
from app.state.session import get_current_trip


def render_weather_page() -> None:
    """Render destination climate analysis and 14-day forecasts."""
    st.title("Weather & Climate Intelligence")
    st.markdown("Forecasts, precipitation probabilities, and seasonal weather hazard detection.")

    st.markdown("---")

    active_trip = get_current_trip()
    if active_trip:
        st.subheader(f"Destination: {active_trip.destination}")
        st.caption(f"Travel Window: {active_trip.start_date} to {active_trip.end_date}")

    st.info(
        "ℹ️ **Weather Agent Offline**: Real-time 14-day forecasts via OpenWeather API, historical climate modeling, and outdoor hazard detection will be connected in Phase 5 & Phase 8. No fake weather data is shown."
    )

    with st.expander("⛅ Target Weather Intelligence Capabilities (Phase 5 & 8)", expanded=True):
        st.markdown(
            """
            - **14-day daily forecast breakdowns** with temperature and precipitation likelihood
            - **Outdoor hazard radar**: Automatically alerts the Planner to shift outdoor hikes indoors during stormy days
            - **Packing recommendations**: Context-aware clothing advice based on temperature swings
            """
        )
