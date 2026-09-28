"""Session state management for the Streamlit Travel Command Center."""

from typing import Optional, List, Dict, Any
import streamlit as st
from models.travel_request import TravelRequest


def init_session_state() -> None:
    """Initialize default session state keys if not already present."""
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Dashboard"

    if "current_trip_request" not in st.session_state:
        st.session_state.current_trip_request = None

    if "current_trip_id" not in st.session_state:
        st.session_state.current_trip_id = None

    if "workflow_status" not in st.session_state:
        st.session_state.workflow_status = "IDLE"

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "recent_trips" not in st.session_state:
        st.session_state.recent_trips = []


def get_current_trip() -> Optional[TravelRequest]:
    """Retrieve current travel request from session state."""
    init_session_state()
    return st.session_state.get("current_trip_request")


def set_current_trip(request: TravelRequest) -> None:
    """Save active travel request to session state and update workflow status."""
    init_session_state()
    st.session_state.current_trip_request = request
    st.session_state.current_trip_id = request.metadata.trip_id
    st.session_state.workflow_status = "REQUEST_VALIDATED"

    # Maintain recent trips history in memory
    recent = st.session_state.get("recent_trips", [])
    # Deduplicate by trip_id
    recent = [t for t in recent if t.get("trip_id") != request.metadata.trip_id]
    recent.insert(0, {
        "trip_id": request.metadata.trip_id,
        "origin": request.origin,
        "destination": request.destination,
        "start_date": str(request.start_date),
        "end_date": str(request.end_date),
        "budget": request.budget,
        "currency": request.currency,
        "travelers": request.travelers,
        "status": request.metadata.status,
    })
    st.session_state.recent_trips = recent[:5]


def clear_current_trip() -> None:
    """Reset current trip from active state."""
    init_session_state()
    st.session_state.current_trip_request = None
    st.session_state.current_trip_id = None
    st.session_state.workflow_status = "IDLE"


def navigate_to(page: str) -> None:
    """Update current page navigation state."""
    init_session_state()
    st.session_state.current_page = page


def add_message(role: str, content: str) -> None:
    """Append a message to conversational history."""
    init_session_state()
    st.session_state.messages.append({
        "role": role,
        "content": content,
    })
