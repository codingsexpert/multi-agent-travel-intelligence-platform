"""Sidebar navigation and environment indicator for Travel Command Center."""

import streamlit as st
from config.settings import get_settings
from services.health_service import get_health_status
from app.state.session import get_current_trip


PAGES = [
    ("Dashboard", "📊"),
    ("New Trip", "📝"),
    ("My Trips", "📂"),
    ("Approvals", "🛡️"),
    ("Conversation", "💬"),
    ("Itinerary", "🗓️"),
    ("Flights", "✈️"),
    ("Hotels", "🏨"),
    ("Activities", "🎯"),
    ("Weather", "⛅"),
    ("Budget", "💰"),
    ("Sources", "📚"),
    ("Agent Trace", "🔍"),
    ("Settings", "⚙️"),
]


def render_sidebar() -> str:
    """Render application sidebar and return the currently selected page name."""
    settings = get_settings()
    health = get_health_status(settings)

    with st.sidebar:
        st.markdown("## ✈️ Travel Command")
        st.caption("Multi-Agent Intelligence Platform")

        # Environment Badge
        if health.demo_mode:
            st.markdown(
                """
                <div style="
                    background: rgba(76, 175, 80, 0.15);
                    border: 1px solid rgba(76, 175, 80, 0.4);
                    color: #81C784;
                    padding: 6px 12px;
                    border-radius: 6px;
                    font-size: 0.8rem;
                    font-weight: 600;
                    margin-bottom: 12px;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                ">
                    <span>🟢</span> <span>DEMO MODE (Offline)</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style="
                    background: rgba(33, 150, 243, 0.15);
                    border: 1px solid rgba(33, 150, 243, 0.4);
                    color: #64B5F6;
                    padding: 6px 12px;
                    border-radius: 6px;
                    font-size: 0.8rem;
                    font-weight: 600;
                    margin-bottom: 12px;
                ">
                    🔵 {health.environment}
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Active Trip Indicator
        active_trip = get_current_trip()
        if active_trip:
            st.markdown(
                f"""
                <div style="
                    background: rgba(255, 255, 255, 0.04);
                    border-left: 3px solid #1E88E5;
                    padding: 8px 10px;
                    border-radius: 4px;
                    margin-bottom: 16px;
                    font-size: 0.85rem;
                ">
                    <div style="font-weight: 600; color: #E0E0E0;">Active Trip</div>
                    <div style="color: #90CAF9;">{active_trip.origin} &rarr; {active_trip.destination}</div>
                    <div style="font-size: 0.75rem; color: #9E9E9E;">{active_trip.duration_days} Days | {active_trip.currency} {active_trip.budget:,.0f}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("### Navigation")

        # Page selection
        page_labels = [name for name, _ in PAGES]
        current_page = st.session_state.get("current_page", "Dashboard")
        default_index = page_labels.index(current_page) if current_page in page_labels else 0

        selected_page = st.radio(
            "Go to",
            options=page_labels,
            index=default_index,
            format_func=lambda name: f"{dict(PAGES)[name]} {name}",
            label_visibility="collapsed",
        )

        st.session_state.current_page = selected_page

        st.markdown("---")
        user = st.session_state.get("auth_user", {}) or {}
        user_email = user.get("email", "guest")
        is_demo = user.get("is_demo", True)
        user_label = f"👤 {user_email} (Demo)" if is_demo else f"👤 {user_email}"
        st.caption(user_label)
        st.caption(f"Workflow: `{st.session_state.get('workflow_status', 'IDLE')}`")
        st.caption("Phase 3: Supabase & Persistence")

    return selected_page
