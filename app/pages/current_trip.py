"""Current Active Trip Command Center View.

Phase 17: Production Travel Command Center UI/UX.
Provides comprehensive inspection of the currently loaded travel request,
route geometry, constraints, budget caps, traveler preferences, and quick links.
"""

import streamlit as st
from app.state.session import get_current_trip, navigate_to
from app.components.empty_state import render_empty_state
from app.components.styles import inject_custom_styles


def render_current_trip_page() -> None:
    """Render the detailed view of the currently active trip."""
    inject_custom_styles()

    st.markdown(
        """
        <div class="main-header">
            <div class="main-title">🧭 Current Trip Overview</div>
            <div class="main-subtitle">Active travel session parameters, route profile, constraints, and intelligence status.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    trip = get_current_trip()
    if not trip:
        render_empty_state(
            title="No Active Trip in Session",
            description="You do not currently have a trip loaded in memory. Create a new trip or select one from My Trips to begin planning.",
            icon="🧭",
            action_label="➕ Create New Trip",
            target_page="New Trip",
        )
        return

    travel_state = st.session_state.get("travel_state", {})
    itinerary_ver = travel_state.get("itinerary_version", 1)
    wf_status = st.session_state.get("workflow_status", "ACTIVE")

    # Header Card
    st.markdown(
        f"""
        <div class="travel-card">
            <div class="travel-card-header">
                <div>
                    <span style="font-size: 1.35rem; font-weight: 700; color: #F8FAFC;">
                        {trip.origin} &rarr; {trip.destination}
                    </span>
                    <span class="badge badge-demo" style="margin-left: 10px;">VERSION {itinerary_ver}</span>
                </div>
                <div>
                    <span class="badge badge-running">{wf_status}</span>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-top: 8px;">
                <div>
                    <div style="font-size: 0.75rem; color: #94A3B8; text-transform: uppercase;">Dates</div>
                    <div style="font-size: 0.95rem; font-weight: 600; color: #E2E8F0;">{trip.start_date} to {trip.end_date}</div>
                    <div style="font-size: 0.8rem; color: #64748B;">({trip.duration_days} Days)</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #94A3B8; text-transform: uppercase;">Travelers</div>
                    <div style="font-size: 0.95rem; font-weight: 600; color: #E2E8F0;">{trip.travelers} Guest(s)</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #94A3B8; text-transform: uppercase;">Budget Cap</div>
                    <div style="font-size: 0.95rem; font-weight: 600; color: #34D399;">{trip.currency} {trip.budget:,.2f}</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #94A3B8; text-transform: uppercase;">Trip ID</div>
                    <div style="font-size: 0.85rem; font-family: monospace; color: #94A3B8;">{trip.metadata.trip_id[:8]}...</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Detailed Preferences & Constraints
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### 🎯 Traveler Preferences")
        with st.container():
            st.markdown(
                f"""
                <div class="travel-card">
                    <p><strong>Pace & Style:</strong> {trip.preferences.pace.capitalize()}</p>
                    <p><strong>Accommodation:</strong> {trip.preferences.accommodation_type.capitalize()}</p>
                    <p><strong>Cabin Class:</strong> {trip.preferences.cabin_class.replace('_', ' ').capitalize()}</p>
                    <p><strong>Selected Interests:</strong></p>
                    <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px;">
                        {' '.join([f'<span class="badge" style="background: #1E293B; color: #94A3B8; border: 1px solid #334155;">{i}</span>' for i in trip.preferences.interests]) if trip.preferences.interests else '<span style="color: #64748B;">None specified</span>'}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with c2:
        st.markdown("### 🛡️ Constraints & Governance")
        with st.container():
            st.markdown(
                f"""
                <div class="travel-card">
                    <p><strong>Direct Flights Only:</strong> {'✅ Yes' if trip.constraints.direct_flights_only else '❌ No'}</p>
                    <p><strong>Kid-Friendly Pacing:</strong> {'✅ Yes' if trip.constraints.kid_friendly else '❌ No'}</p>
                    <p><strong>Strict Budget Limit:</strong> {trip.currency} {trip.budget:,.2f}</p>
                    <p><strong>Must-Include Items:</strong></p>
                    <div style="font-size: 0.85rem; color: #94A3B8; margin-top: 4px;">
                        {', '.join(trip.constraints.must_include) if trip.constraints.must_include else 'No mandatory landmarks'}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Quick Navigation Launchpad
    st.markdown("### ⚡ Quick Navigation")
    q1, q2, q3, q4 = st.columns(4)
    with q1:
        if st.button("🗓️ View Itinerary", use_container_width=True):
            navigate_to("Itinerary")
            st.rerun()
    with q2:
        if st.button("✈️ Review Flights", use_container_width=True):
            navigate_to("Flights")
            st.rerun()
    with q3:
        if st.button("🏨 Review Hotels", use_container_width=True):
            navigate_to("Hotels")
            st.rerun()
    with q4:
        if st.button("💰 Budget Analysis", use_container_width=True):
            navigate_to("Budget")
            st.rerun()
