"""Conversational travel planning interface connected to conversation & message repositories."""

import streamlit as st
from app.state.session import (
    get_current_user,
    get_current_trip,
    get_current_conversation_id,
    set_current_conversation_id,
)
from repositories import conversation_repository, message_repository
from services.planning_service import run_travel_planning


def render_conversation_page() -> None:
    """Render conversational interface backed by repository persistence."""
    st.title("Travel Planning Assistant")
    st.markdown(
        "Chat with the conversational multi-agent interface to refine requirements, ask destination questions, or adjust constraints."
    )

    st.markdown("---")

    current_user = get_current_user()
    active_trip = get_current_trip()
    current_trip_id = st.session_state.get("current_trip_id")

    # Ensure conversation exists
    conv_id = get_current_conversation_id()
    if not conv_id:
        title = f"Planning: {active_trip.destination}" if active_trip else "General Travel Inquiries"
        conv = conversation_repository.create_conversation(
            user_id=current_user["id"],
            trip_id=current_trip_id,
            title=title,
        )
        conv_id = conv["id"]
        set_current_conversation_id(conv_id)

        # Welcome message
        welcome = (
            "Hello! I am your AI Travel Intelligence Assistant. "
            "In later phases, I will help you formulate trip requirements, explore flight and hotel trade-offs, "
            "and dynamically replan your itinerary when conditions change. How can I help you today?"
        )
        message_repository.create_message(
            conversation_id=conv_id,
            role="assistant",
            content=welcome,
        )

    # Context Header
    c1, c2 = st.columns([3, 1])
    with c1:
        if active_trip:
            st.caption(
                f"Context: **{active_trip.origin} &rarr; {active_trip.destination}** "
                f"({active_trip.start_date} to {active_trip.end_date}, budget: {active_trip.currency} {active_trip.budget:,.0f})"
            )
        else:
            st.caption("Context: No active trip selected. You can plan a new trip or ask general questions.")
    with c2:
        st.caption(f"Thread ID: `{conv_id[:8]}...`")

    st.info(
        "ℹ️ **LangGraph Multi-Agent Conversation Active**: Prompts are analyzed by the LangGraph Planner Agent to extract requirements, identify missing parameters, and guide planning."
    )

    # Load messages from repository
    try:
        messages = message_repository.list_messages_for_conversation(conv_id)
    except Exception as e:
        st.error(f"Error loading conversation messages: {e}")
        messages = []

    # Render message history
    chat_container = st.container()
    with chat_container:
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                st.caption(f"Sent at: {msg.get('created_at', '')[:19].replace('T', ' ')}")

    # Input Box
    user_input = st.chat_input("Ask a question, enter requirements, or answer clarification questions...")

    if user_input:
        with st.spinner("Analyzing requirements with Planner Agent..."):
            run_travel_planning(
                user_request=user_input,
                user_id=current_user["id"],
                trip_id=current_trip_id,
                conversation_id=conv_id,
                session_state=st.session_state,
            )
        st.rerun()
