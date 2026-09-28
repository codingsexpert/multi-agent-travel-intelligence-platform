"""Day-by-day itinerary page layout and placeholders."""

import streamlit as st
from app.state.session import get_current_trip
from app.components.trip_summary_card import render_trip_summary_card


def render_activity_slot(
    time_of_day: str,
    time_range: str,
    title: str,
    location: str,
    cost: str,
    transit: str,
    weather: str,
    source: str,
) -> None:
    """Render a structural placeholder slot for future itinerary items."""
    with st.container():
        st.markdown(
            f"""
            <div style="
                border-left: 3px solid #42A5F5;
                padding: 10px 14px;
                margin-bottom: 12px;
                background-color: rgba(255, 255, 255, 0.02);
                border-radius: 0 6px 6px 0;
            ">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <span style="font-weight: 600; color: #90CAF9; font-size: 0.9rem;">{time_of_day.upper()} ({time_range})</span>
                    <span style="font-size: 0.8rem; color: #81C784;">Estimated Cost: {cost}</span>
                </div>
                <div style="font-weight: 500; font-size: 1.05rem; margin: 4px 0;">{title}</div>
                <div style="display: flex; gap: 16px; font-size: 0.8rem; color: #B0BEC5; flex-wrap: wrap;">
                    <span>📍 <strong>Location:</strong> {location}</span>
                    <span>🚆 <strong>Transit:</strong> {transit}</span>
                    <span>⛅ <strong>Weather:</strong> {weather}</span>
                    <span>📚 <strong>Source:</strong> {source}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_itinerary_page() -> None:
    """Render empty itinerary structure and day-by-day activity placeholders."""
    st.title("Trip Itinerary")
    st.markdown("Chronological, day-by-day schedule with timing, transit buffers, and budget tracking.")

    st.markdown("---")

    active_trip = get_current_trip()

    if not active_trip:
        st.info("ℹ️ No active trip found. Visit the **New Trip** page to submit trip requirements.")
        return

    # Trip Summary
    st.subheader("Trip Summary")
    render_trip_summary_card(active_trip, show_id=False)

    st.markdown("---")

    # Validation Status Section (Phase 6)
    travel_state = st.session_state.get("travel_state", {})
    val_data = travel_state.get("validation_results")

    st.subheader("Itinerary Feasibility & Constraint Validation")
    if not val_data:
        st.info("ℹ️ **Validation Pending**: Run Travel Planning to execute deterministic constraint verification.")
    else:
        v_status = val_data.get("status", "READY_FOR_ITINERARY")
        is_valid = val_data.get("valid", True)
        v_issues = val_data.get("issues", [])
        v_warnings = val_data.get("warnings", [])
        v_errors = val_data.get("errors", [])

        if not is_valid:
            st.error(f"❌ **Validation Failed** (Status: `{v_status}`). Fix critical blocking issues before generating itinerary.")
        elif len(v_warnings) > 0:
            st.warning(f"⚠️ **Validation Passed With Warnings** (Status: `{v_status}`). Review advisories below.")
        else:
            st.success(f"✅ **Itinerary Fully Verified** (Status: `{v_status}`). Zero constraint violations or time conflicts.")

        # Checklists
        has_budget_err = any(i.get("component") == "budget" and i.get("severity") == "ERROR" for i in v_issues)
        has_budget_warn = any(i.get("component") == "budget" and i.get("severity") == "WARNING" for i in v_issues)
        has_date_err = any(i.get("component") == "dates" for i in v_issues)
        has_traveler_err = any(i.get("component") == "travelers" for i in v_issues)
        has_weather_warn = any(i.get("component") == "weather" for i in v_issues)
        has_act_conflict = any(i.get("component") == "activities" for i in v_issues)

        b_label = "❌ Budget Error" if has_budget_err else ("⚠️ Budget Overrun" if has_budget_warn else "✓ Budget Within Cap")
        d_label = "❌ Invalid Dates" if has_date_err else "✓ Valid Dates Sequence"
        t_label = "❌ Invalid Travellers" if has_traveler_err else "✓ Positive Traveller Count"
        w_label = "⚠️ Weather Unavailable" if has_weather_warn else "✓ Weather Observed"
        a_label = "⚠️ Activity Schedule Conflict" if has_act_conflict else "✓ Activity Pacing Consistent"

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"• **Budget Feasibility**: `{b_label}`")
            st.markdown(f"• **Date Feasibility**: `{d_label}`")
        with c2:
            st.markdown(f"• **Traveller Headcount**: `{t_label}`")
            st.markdown(f"• **Meteorological Feed**: `{w_label}`")
        with c3:
            st.markdown(f"• **Activity Schedule**: `{a_label}`")
            mode_lbl = "DEMO DATA" if travel_state.get("is_demo", True) else "LIVE API"
            st.markdown(f"• **Validation Engine**: `DETERMINISTIC ({mode_lbl})`")

        if v_issues:
            with st.expander(f"Detailed Validation Issues Log ({len(v_issues)} items)", expanded=not is_valid):
                for iss in v_issues:
                    sev = iss.get("severity", "INFO")
                    comp = iss.get("component", "General").title()
                    code = iss.get("code", "")
                    msg = iss.get("message", "")
                    if sev == "ERROR":
                        st.markdown(f"❌ **[{sev}] [{comp} - {code}]**: {msg}")
                    elif sev == "WARNING":
                        st.markdown(f"⚠️ **[{sev}] [{comp} - {code}]**: {msg}")
                    else:
                        st.markdown(f"ℹ️ **[{sev}] [{comp} - {code}]**: {msg}")

    st.markdown("---")

    # Placeholder banner
    st.info(
        "ℹ️ **Itinerary Synthesis Preview**: Final day-by-day itinerary synthesis will be assembled by the Itinerary Agent in Phase 7+. The verified slots below illustrate the target data structure."
    )

    # Day 1 Structure
    with st.expander("📅 Day 1: Arrival, Neighborhood Exploration & Welcome Dinner", expanded=True):
        st.caption("Theme: Cultural immersion & low-stress orientation")

        render_activity_slot(
            time_of_day="Morning",
            time_range="09:00 - 12:00",
            title="[Slot] Airport Arrival, Transit & Hotel Check-in",
            location="Arrival Terminal & Hotel District",
            cost="Included in Transit / Lodging",
            transit="45 min Express Train",
            weather="Forecast: 18°C, Partly Cloudy",
            source="Flight Agent & OpenWeather API",
        )

        render_activity_slot(
            time_of_day="Afternoon",
            time_range="13:30 - 16:30",
            title="[Slot] Historic District Walking Tour & Local Landmark",
            location="Old Town Center",
            cost="$25.00 / person",
            transit="15 min Walking",
            weather="Forecast: 20°C, Mild",
            source="Activity Agent via Places Tools",
        )

        render_activity_slot(
            time_of_day="Evening",
            time_range="18:30 - 21:00",
            title="[Slot] Traditional Regional Cuisine Experience",
            location="Culinary Arcade",
            cost="$45.00 / person",
            transit="10 min Metro",
            weather="Forecast: 16°C, Clear",
            source="pgvector RAG Dining Guide",
        )

    # Day 2 Structure
    with st.expander("📅 Day 2: Iconic Sights & Immersive Experiences", expanded=True):
        st.caption("Theme: High-priority attractions & cultural highlights")

        render_activity_slot(
            time_of_day="Morning",
            time_range="09:30 - 12:30",
            title="[Slot] Major Architectural Landmark & Gardens",
            location="Central Cultural Quarter",
            cost="$15.00 / person",
            transit="20 min Transit",
            weather="Forecast: 19°C, Sunny",
            source="Activity Agent / Curated Knowledge Base",
        )

        render_activity_slot(
            time_of_day="Afternoon",
            time_range="14:00 - 17:00",
            title="[Slot] Renowned Art Museum & Exhibitions",
            location="Museum District",
            cost="$22.00 / person",
            transit="15 min Walking",
            weather="Forecast: 21°C, Indoor Friendly",
            source="Places API",
        )

        render_activity_slot(
            time_of_day="Evening",
            time_range="19:00 - 21:30",
            title="[Slot] Evening Observation Deck & Sunset Viewpoint",
            location="Skyline Tower",
            cost="$30.00 / person",
            transit="15 min Metro",
            weather="Forecast: 15°C, Good Visibility",
            source="Tavily Live Web Search",
        )
