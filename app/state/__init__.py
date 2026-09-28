"""Session state module for the Streamlit UI."""

from app.state.session import (
    init_session_state,
    get_current_trip,
    set_current_trip,
    clear_current_trip,
    navigate_to,
    add_message,
    get_current_user,
    set_current_user,
    get_current_conversation_id,
    set_current_conversation_id,
    DEMO_USER,
)

__all__ = [
    "init_session_state",
    "get_current_trip",
    "set_current_trip",
    "clear_current_trip",
    "navigate_to",
    "add_message",
    "get_current_user",
    "set_current_user",
    "get_current_conversation_id",
    "set_current_conversation_id",
    "DEMO_USER",
]
