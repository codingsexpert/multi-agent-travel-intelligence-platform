"""Main entrypoint for the Multi-Agent Travel Intelligence Platform."""

import streamlit as st
from app.state.session import init_session_state
from app.components.sidebar import render_sidebar
from app.pages import (
    render_dashboard_page,
    render_new_trip_page,
    render_my_trips_page,
    render_conversation_page,
    render_itinerary_page,
    render_flights_page,
    render_hotels_page,
    render_activities_page,
    render_weather_page,
    render_budget_page,
    render_sources_page,
    render_agent_trace_page,
    render_settings_page,
    render_approvals_page,
    render_evaluation_page,
)


PAGE_DISPATCHER = {
    "Dashboard": render_dashboard_page,
    "New Trip": render_new_trip_page,
    "My Trips": render_my_trips_page,
    "Approvals": render_approvals_page,
    "Conversation": render_conversation_page,
    "Itinerary": render_itinerary_page,
    "Flights": render_flights_page,
    "Hotels": render_hotels_page,
    "Activities": render_activities_page,
    "Weather": render_weather_page,
    "Budget": render_budget_page,
    "Sources": render_sources_page,
    "Agent Trace": render_agent_trace_page,
    "Evaluation": render_evaluation_page,
    "Settings": render_settings_page,
}


def main():
    """Application main runner and page router."""
    st.set_page_config(
        page_title="Travel Command Center | Multi-Agent AI",
        page_icon="✈️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize session state keys
    init_session_state()

    # Render sidebar navigation
    selected_page = render_sidebar()

    # Dispatch to target page
    render_func = PAGE_DISPATCHER.get(selected_page, render_dashboard_page)
    render_func()


if __name__ == "__main__":
    main()
