"""Session state management for the Streamlit Travel Command Center."""

from typing import Optional, List, Dict, Any
import streamlit as st
from models.travel_request import TravelRequest


DEMO_USER = {
    "id": "00000000-0000-0000-0000-000000000001",
    "email": "demo.traveler@example.com",
    "full_name": "Demo Traveler",
    "is_demo": True,
}


def init_session_state() -> None:
    """Initialize default session state keys if not already present."""
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Dashboard"

    if "current_trip_request" not in st.session_state:
        st.session_state.current_trip_request = None

    if "current_trip_id" not in st.session_state:
        st.session_state.current_trip_id = None

    if "current_conversation_id" not in st.session_state:
        st.session_state.current_conversation_id = None

    if "workflow_status" not in st.session_state:
        st.session_state.workflow_status = "IDLE"

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "recent_trips" not in st.session_state:
        st.session_state.recent_trips = []

    if "auth_user" not in st.session_state:
        st.session_state.auth_user = DEMO_USER


def get_current_user() -> Dict[str, Any]:
    """Retrieve current authenticated user from session state or fallback to DEMO_USER."""
    init_session_state()
    return st.session_state.get("auth_user") or DEMO_USER


def set_current_user(user: Optional[Dict[str, Any]]) -> None:
    """Update active user in session state."""
    init_session_state()
    st.session_state.auth_user = user or DEMO_USER


def get_current_trip() -> Optional[TravelRequest]:
    """Retrieve current travel request from session state."""
    init_session_state()
    return st.session_state.get("current_trip_request")


def set_current_trip(request: TravelRequest, trip_id: Optional[str] = None) -> None:
    """Save active travel request to session state and update workflow status."""
    init_session_state()
    st.session_state.current_trip_request = request
    st.session_state.current_trip_id = trip_id or request.metadata.trip_id
    st.session_state.workflow_status = "REQUEST_VALIDATED"

    # Maintain recent trips history in memory
    recent = st.session_state.get("recent_trips", [])
    recent = [t for t in recent if t.get("trip_id") != st.session_state.current_trip_id]
    recent.insert(0, {
        "trip_id": st.session_state.current_trip_id,
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
    st.session_state.current_conversation_id = None
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


def get_current_conversation_id() -> Optional[str]:
    """Retrieve active conversation id."""
    init_session_state()
    return st.session_state.get("current_conversation_id")


def set_current_conversation_id(conv_id: Optional[str]) -> None:
    """Set active conversation id."""
    init_session_state()
    st.session_state.current_conversation_id = conv_id
