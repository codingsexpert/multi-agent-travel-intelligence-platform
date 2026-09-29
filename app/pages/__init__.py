"""Streamlit page renderers for Travel Command Center."""

from app.pages.dashboard import render_dashboard_page
from app.pages.new_trip import render_new_trip_page
from app.pages.my_trips import render_my_trips_page
from app.pages.conversation import render_conversation_page
from app.pages.itinerary import render_itinerary_page
from app.pages.flights import render_flights_page
from app.pages.hotels import render_hotels_page
from app.pages.activities import render_activities_page
from app.pages.weather import render_weather_page
from app.pages.budget import render_budget_page
from app.pages.sources import render_sources_page
from app.pages.agent_trace import render_agent_trace_page
from app.pages.settings import render_settings_page
from app.pages.approvals import render_approvals_page

__all__ = [
    "render_dashboard_page",
    "render_new_trip_page",
    "render_my_trips_page",
    "render_conversation_page",
    "render_itinerary_page",
    "render_flights_page",
    "render_hotels_page",
    "render_activities_page",
    "render_weather_page",
    "render_budget_page",
    "render_sources_page",
    "render_agent_trace_page",
    "render_settings_page",
    "render_approvals_page",
]
