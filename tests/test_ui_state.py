"""Unit tests for UI session state management."""

from datetime import date
import streamlit as st
from app.state.session import (
    init_session_state,
    get_current_trip,
    set_current_trip,
    clear_current_trip,
    navigate_to,
    add_message,
)
from models.travel_request import (
    TravelRequest,
    TravelerPreferences,
    TripConstraints,
)


def test_session_state_initialization():
    """Verify that init_session_state populates all default session keys."""
    # Ensure fresh state
    st.session_state.clear()
    init_session_state()

    assert st.session_state.current_page == "Dashboard"
    assert st.session_state.current_trip_request is None
    assert st.session_state.current_trip_id is None
    assert st.session_state.workflow_status == "IDLE"
    assert st.session_state.messages == []
    assert st.session_state.recent_trips == []


def test_set_and_get_current_trip():
    """Verify storing and retrieving a TravelRequest in session state."""
    st.session_state.clear()
    init_session_state()

    req = TravelRequest(
        origin="SFO",
        destination="Tokyo",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 10),
        travelers=2,
        budget=4000.0,
        currency="USD",
        preferences=TravelerPreferences(interests=["Culinary"], pace="moderate"),
        constraints=TripConstraints(direct_flights_only=True),
    )

    set_current_trip(req)

    current = get_current_trip()
    assert current is not None
    assert current.origin == "SFO"
    assert current.destination == "Tokyo"
    assert current.budget == 4000.0
    assert st.session_state.workflow_status == "REQUEST_VALIDATED"
    assert st.session_state.current_trip_id == req.metadata.trip_id

    # Verify added to recent trips
    assert len(st.session_state.recent_trips) == 1
    assert st.session_state.recent_trips[0]["destination"] == "Tokyo"


def test_clear_current_trip():
    """Verify resetting the current trip restores IDLE workflow state."""
    st.session_state.clear()
    init_session_state()

    req = TravelRequest(
        origin="JFK",
        destination="Paris",
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 12),
        travelers=1,
        budget=2500.0,
    )
    set_current_trip(req)
    assert get_current_trip() is not None

    clear_current_trip()
    assert get_current_trip() is None
    assert st.session_state.current_trip_id is None
    assert st.session_state.workflow_status == "IDLE"


def test_navigation_and_messaging():
    """Verify navigation routing and message appending."""
    st.session_state.clear()
    init_session_state()

    navigate_to("Itinerary")
    assert st.session_state.current_page == "Itinerary"

    add_message("user", "Hello there")
    add_message("assistant", "How can I help?")

    assert len(st.session_state.messages) == 2
    assert st.session_state.messages[0]["role"] == "user"
    assert st.session_state.messages[1]["role"] == "assistant"
