"""Conversational travel planning interface foundation."""

import streamlit as st
from app.state.session import add_message, get_current_trip


def render_conversation_page() -> None:
    """Render conversational interaction interface foundation."""
    st.title("Travel Planning Assistant")
    st.markdown(
        "Chat with the conversational multi-agent interface to refine requirements, ask destination questions, or adjust constraints."
    )

    st.markdown("---")

    # Informational notice as requested
    st.info(
        "ℹ️ **Conversational Engine Offline**: The conversational planning engine and LangGraph streaming agents will be connected in Phase 4. Messages entered here are stored in session state for UI verification only. No live LLM calls are executed."
    )

    active_trip = get_current_trip()
    if active_trip:
        st.caption(
            f"Context: Planning trip to **{active_trip.destination}** ({active_trip.start_date} to {active_trip.end_date}, budget: {active_trip.currency} {active_trip.budget:,.0f})"
        )

    # Initialize sample messages if empty
    messages = st.session_state.get("messages", [])
    if not messages:
        messages = [
            {
                "role": "assistant",
                "content": (
                    "Hello! I am your AI Travel Intelligence Assistant. "
                    "In later phases, I will help you formulate trip requirements, explore flight and hotel trade-offs, "
                    "and dynamically replan your itinerary when conditions change. How can I help you today?"
                ),
            }
        ]
        st.session_state.messages = messages

    # Render conversation area
    chat_container = st.container()
    with chat_container:
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    # Input Box and Send
    user_input = st.chat_input("Ask a question or adjust your trip requirements (e.g. 'Add a day trip to Kamakura')...")

    if user_input:
        add_message("user", user_input)
        # Placeholder response
        placeholder_reply = (
            f"[Phase 2 Placeholder] Received: '{user_input}'. "
            "In Phase 4, the Planner Agent will parse this prompt, trigger specialized domain agents, "
            "and update your itinerary state."
        )
        add_message("assistant", placeholder_reply)
        st.rerun()
