"""Actionable empty state component for Travel Command Center.

Phase 17: Production Travel Command Center UI/UX.
Ensures zero meaningless blank screens across all product pages.
"""

from typing import Optional
import streamlit as st
from app.state.session import navigate_to


def render_empty_state(
    title: str,
    description: str,
    icon: str = "✈️",
    action_label: Optional[str] = None,
    target_page: Optional[str] = None,
) -> None:
    """Render an actionable empty state with optional redirect button."""
    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-state-icon">{icon}</div>
            <div class="empty-state-title">{title}</div>
            <div class="empty-state-desc">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if action_label and target_page:
        col_l, col_m, col_r = st.columns([1, 1, 1])
        with col_m:
            if st.button(action_label, type="primary", use_container_width=True):
                navigate_to(target_page)
                st.rerun()
