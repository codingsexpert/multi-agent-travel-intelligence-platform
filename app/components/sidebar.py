"""Sidebar navigation and environment indicator for Travel Command Center.

Phase 17: Production Travel Command Center UI/UX.
Implements two-tier Information Architecture:
- Primary Navigation (Travel Intelligence & Trip Management)
- Developer / Advanced Operations (Tracing, Replanning, Security, Approvals, RAG)
"""

from typing import List, Tuple
import streamlit as st
from config.settings import get_settings
from services.health_service import get_health_status
from app.state.session import get_current_trip


PRIMARY_PAGES: List[Tuple[str, str]] = [
    ("Dashboard", "📊"),
    ("New Trip", "📝"),
    ("My Trips", "📂"),
    ("Current Trip", "🧭"),
    ("Itinerary", "🗓️"),
    ("Flights", "✈️"),
    ("Hotels", "🏨"),
    ("Activities", "🎯"),
    ("Weather", "⛅"),
    ("Budget", "💰"),
    ("Sources", "📚"),
    ("Planning Progress", "⏳"),
]

ADVANCED_PAGES: List[Tuple[str, str]] = [
    ("Agent Trace", "🔍"),
    ("Changes & Replanning", "🔄"),
    ("Approvals", "🛡️"),
    ("Evaluation", "🧪"),
    ("Knowledge / RAG", "🧠"),
    ("Security", "🔐"),
    ("Settings", "⚙️"),
]

ALL_PAGES = PRIMARY_PAGES + ADVANCED_PAGES
PAGE_ICONS = dict(ALL_PAGES)


def render_sidebar() -> str:
    """Render structured sidebar navigation and return currently active page name."""
    settings = get_settings()
    health = get_health_status(settings)

    with st.sidebar:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                <span style="font-size: 1.5rem;">✈️</span>
                <span style="font-size: 1.25rem; font-weight: 700; color: #F8FAFC;">Travel Command</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Autonomous Multi-Agent Intelligence Platform")

        # Environment & Mode Badge
        if health.demo_mode:
            st.markdown(
                """
                <div class="badge badge-demo" style="margin: 8px 0 16px 0; width: 100%; justify-content: center; padding: 4px 8px;">
                    <span>🟢</span> <span>DEMO MODE (Offline & Mock Tools)</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="badge badge-live" style="margin: 8px 0 16px 0; width: 100%; justify-content: center; padding: 4px 8px;">
                    <span>🔵</span> <span>LIVE ENVIRONMENT ({health.environment})</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Active Trip Mini-Summary Card
        active_trip = get_current_trip()
        if active_trip:
            st.markdown(
                f"""
                <div style="
                    background: #1E293B;
                    border: 1px solid #334155;
                    border-left: 3px solid #3B82F6;
                    padding: 10px 12px;
                    border-radius: 6px;
                    margin-bottom: 16px;
                ">
                    <div style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: #94A3B8; font-weight: 600;">ACTIVE TRIP</div>
                    <div style="font-weight: 600; color: #F8FAFC; font-size: 0.95rem; margin: 2px 0;">{active_trip.origin} &rarr; {active_trip.destination}</div>
                    <div style="font-size: 0.8rem; color: #CBD5E1;">{active_trip.duration_days} Days &bull; {active_trip.currency} {active_trip.budget:,.0f}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("---")

        current_page = st.session_state.get("current_page", "Dashboard")
        all_labels = [name for name, _ in ALL_PAGES]
        if current_page not in all_labels:
            current_page = "Dashboard"

        # View Mode Toggle: Travel Intelligence vs Developer / Operations
        is_advanced_current = any(name == current_page for name, _ in ADVANCED_PAGES)
        nav_mode = st.radio(
            "Navigation Scope",
            options=["Travel Intelligence", "Developer & Ops"],
            index=1 if is_advanced_current else 0,
            horizontal=True,
            label_visibility="collapsed",
        )

        st.markdown(f"**{'Travel Planner' if nav_mode == 'Travel Intelligence' else 'Platform Operations'}**")

        if nav_mode == "Travel Intelligence":
            options = [name for name, _ in PRIMARY_PAGES]
            default_idx = options.index(current_page) if current_page in options else 0
            selected = st.radio(
                "Primary Navigation",
                options=options,
                index=default_idx,
                format_func=lambda n: f"{PAGE_ICONS.get(n, '•')} {n}",
                label_visibility="collapsed",
            )
        else:
            options = [name for name, _ in ADVANCED_PAGES]
            default_idx = options.index(current_page) if current_page in options else 0
            selected = st.radio(
                "Advanced Navigation",
                options=options,
                index=default_idx,
                format_func=lambda n: f"{PAGE_ICONS.get(n, '•')} {n}",
                label_visibility="collapsed",
            )

        st.session_state.current_page = selected

        st.markdown("---")
        # System Footer details
        user = st.session_state.get("auth_user", {}) or {}
        user_email = user.get("email", "guest")
        st.caption(f"👤 **Operator**: `{user_email}`")
        wf_status = st.session_state.get("workflow_status", "IDLE")
        st.caption(f"⚙️ **Workflow**: `{wf_status}`")
        st.caption("🛡️ **HITL & Guardrails**: Active")

    return selected
