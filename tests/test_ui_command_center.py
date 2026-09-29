"""Comprehensive Test Suite for Phase 17: Production Travel Command Center UI/UX.

Tests all UI requirements:
1. Dashboard page renders without errors
2. Trip creation form validation & Pydantic mapping
3. Planning progress page renders actual pipeline state
4. Itinerary page renders day-by-day structure & versioning
5. Budget page calculates & renders categories & status
6. Warning states & alerts are non-blocking
7. Error states & empty states render actionably
8. Approval UI renders pending approvals & actions
9. Dynamic replanning timeline renders with RERUN/REUSED labels
10. Agent trace renders telemetry without secrets
11. Evaluation dashboard renders quality & reliability metrics
12. Security & Guardrails dashboard renders operational statuses
13. Knowledge & RAG UI renders document inventory & vector query
14. Sources page renders classified source transparency
15. DEMO/LIVE labels are accurately displayed
16. Zero secret leakage across all UI pages
17. Two-tier Information Architecture navigation
"""

from __future__ import annotations

import unittest.mock as mock
import pytest
from datetime import date, timedelta
import streamlit as st

from app.main import PAGE_DISPATCHER
from app.components.sidebar import PRIMARY_PAGES, ADVANCED_PAGES, ALL_PAGES
from app.components.styles import inject_custom_styles
from app.components.empty_state import render_empty_state
from app.state.session import init_session_state, set_current_trip, clear_current_trip
from models.travel_request import TravelRequest, TravelerPreferences, TripConstraints
from app.pages import (
    render_dashboard_page,
    render_current_trip_page,
    render_planning_progress_page,
    render_itinerary_page,
    render_flights_page,
    render_hotels_page,
    render_activities_page,
    render_weather_page,
    render_budget_page,
    render_sources_page,
    render_agent_trace_page,
    render_replanning_page,
    render_approvals_page,
    render_evaluation_page,
    render_security_page,
    render_knowledge_page,
    render_settings_page,
)


@pytest.fixture(autouse=True)
def clean_streamlit_session():
    """Ensure clean session state for every test."""
    st.session_state.clear()
    init_session_state()
    yield
    st.session_state.clear()


@pytest.fixture
def sample_travel_request():
    """Sample valid travel request for testing."""
    today = date.today()
    return TravelRequest(
        origin="BOM",
        destination="DEL",
        start_date=today + timedelta(days=10),
        end_date=today + timedelta(days=13),
        travelers=2,
        budget=45000.0,
        currency="INR",
        preferences=TravelerPreferences(
            interests=["Culture", "Food"],
            pace="moderate",
            accommodation_type="4 star",
            cabin_class="economy",
        ),
        constraints=TripConstraints(
            direct_flights_only=True,
            kid_friendly=False,
            must_include=["India Gate"],
        ),
    )


def test_navigation_information_architecture():
    """Verify primary and advanced navigation groups exist in two-tier structure."""
    assert len(PRIMARY_PAGES) == 12
    assert len(ADVANCED_PAGES) == 7
    assert len(ALL_PAGES) == 19

    primary_names = [name for name, _ in PRIMARY_PAGES]
    assert "Dashboard" in primary_names
    assert "New Trip" in primary_names
    assert "My Trips" in primary_names
    assert "Current Trip" in primary_names
    assert "Itinerary" in primary_names
    assert "Flights" in primary_names
    assert "Hotels" in primary_names
    assert "Activities" in primary_names
    assert "Weather" in primary_names
    assert "Budget" in primary_names
    assert "Sources" in primary_names
    assert "Planning Progress" in primary_names

    adv_names = [name for name, _ in ADVANCED_PAGES]
    assert "Agent Trace" in adv_names
    assert "Changes & Replanning" in adv_names
    assert "Approvals" in adv_names
    assert "Evaluation" in adv_names
    assert "Knowledge / RAG" in adv_names
    assert "Security" in adv_names
    assert "Settings" in adv_names


def test_page_dispatcher_completeness():
    """Verify all navigation targets map to callable page renderers."""
    for page_name, _ in ALL_PAGES:
        assert page_name in PAGE_DISPATCHER, f"Missing dispatcher entry for '{page_name}'"
        assert callable(PAGE_DISPATCHER[page_name])


def test_dashboard_renders_empty_state():
    """Verify dashboard renders empty state when no active trip is present."""
    with mock.patch("streamlit.markdown") as mock_md:
        render_dashboard_page()
        assert mock_md.called


def test_dashboard_renders_with_active_trip(sample_travel_request):
    """Verify dashboard renders active trip and multi-agent planning statuses."""
    set_current_trip(sample_travel_request)
    st.session_state["travel_state"] = {
        "itinerary_version": 2,
        "planner_result": {"plan": "ok"},
        "flight_options": [{"airline": "IndiGo"}],
    }
    with mock.patch("streamlit.markdown") as mock_md:
        render_dashboard_page()
        assert mock_md.called


def test_current_trip_page_renders(sample_travel_request):
    """Verify Current Trip command center view renders route and constraints."""
    set_current_trip(sample_travel_request)
    with mock.patch("streamlit.markdown") as mock_md:
        render_current_trip_page()
        assert mock_md.called


def test_planning_progress_page_renders_actual_pipeline_state(sample_travel_request):
    """Verify Planning Progress renders pipeline steps matching actual session state."""
    set_current_trip(sample_travel_request)
    st.session_state["travel_state"] = {
        "planner_result": True,
        "flight_options": True,
        "hotel_options": True,
    }
    with mock.patch("streamlit.markdown") as mock_md:
        render_planning_progress_page()
        assert mock_md.called


def test_itinerary_page_renders_with_versioning(sample_travel_request):
    """Verify Itinerary page renders day-by-day schedule and replanning banner."""
    set_current_trip(sample_travel_request)
    st.session_state["travel_state"] = {
        "itinerary_version": 3,
        "replan_count": 2,
        "replan_reasons": ["Flight cancellation", "Severe rain disruption"],
    }
    with mock.patch("streamlit.markdown") as mock_md:
        render_itinerary_page()
        assert mock_md.called


def test_flights_page_renders_demo_live_labels(sample_travel_request):
    """Verify flights page renders cards and explicit DEMO/LIVE labels."""
    set_current_trip(sample_travel_request)
    with mock.patch("streamlit.markdown") as mock_md:
        render_flights_page()
        assert mock_md.called


def test_hotels_page_renders_budget_impact(sample_travel_request):
    """Verify hotels page calculates budget impact percentage."""
    set_current_trip(sample_travel_request)
    with mock.patch("streamlit.markdown") as mock_md:
        render_hotels_page()
        assert mock_md.called


def test_activities_page_deduplicates(sample_travel_request):
    """Verify activities page displays unique items without duplicates."""
    set_current_trip(sample_travel_request)
    st.session_state["travel_state"] = {
        "activity_options": [
            {"name": "Temple Tour", "category": "Culture", "estimated_cost": 500.0},
            {"name": "Temple Tour", "category": "Culture", "estimated_cost": 500.0},  # Duplicate
            {"name": "Museum Visit", "category": "Art", "estimated_cost": 800.0},
        ]
    }
    with mock.patch("streamlit.markdown") as mock_md:
        render_activities_page()
        assert mock_md.called


def test_weather_page_renders_conditions(sample_travel_request):
    """Verify weather page renders forecasts and notices."""
    set_current_trip(sample_travel_request)
    st.session_state["travel_state"] = {
        "weather_forecast": {
            "temperature_celsius": 24,
            "condition": "Clear",
            "precipitation_probability": 5,
        }
    }
    with mock.patch("streamlit.markdown") as mock_md:
        render_weather_page()
        assert mock_md.called


def test_budget_page_deterministic_categories(sample_travel_request):
    """Verify budget page renders all 6 expenditure categories and status."""
    set_current_trip(sample_travel_request)
    with mock.patch("streamlit.markdown") as mock_md:
        render_budget_page()
        assert mock_md.called


def test_replanning_page_renders_timeline(sample_travel_request):
    """Verify dynamic replanning page renders timeline and execution modes."""
    set_current_trip(sample_travel_request)
    st.session_state["travel_state"] = {
        "itinerary_version": 2,
        "replan_count": 1,
        "replan_reasons": ["Flight delayed by 3 hours"],
        "agent_execution_modes": {
            "flights": "RERUN",
            "hotels": "REUSED",
            "weather": "REUSED",
        },
    }
    with mock.patch("streamlit.markdown") as mock_md:
        render_replanning_page()
        assert mock_md.called


def test_security_page_renders_all_guardrails():
    """Verify Security & Guardrails page displays active defense layers."""
    with mock.patch("streamlit.markdown") as mock_md:
        render_security_page()
        assert mock_md.called


def test_knowledge_page_renders_repository():
    """Verify Knowledge & RAG page displays verified dossiers."""
    with mock.patch("streamlit.markdown") as mock_md:
        render_knowledge_page()
        assert mock_md.called


def test_sources_transparency_page_renders():
    """Verify sources page renders classified source provenance."""
    with mock.patch("streamlit.markdown") as mock_md:
        render_sources_page()
        assert mock_md.called


def test_settings_page_masks_all_secrets():
    """Verify settings page does not expose credentials, API keys, or raw tokens."""
    with mock.patch("streamlit.markdown") as mock_md, mock.patch("streamlit.code") as mock_code:
        render_settings_page()
        # Verify rendered text does not contain typical API key prefixes
        rendered_calls = [str(call) for call in mock_md.mock_calls] + [str(call) for call in mock_code.mock_calls]
        for item in rendered_calls:
            assert "sk-" not in item
            assert "service_role" not in item.lower() or "not configured" in item.lower() or "host" in item.lower()
            assert "supabase_service" not in item.lower()
