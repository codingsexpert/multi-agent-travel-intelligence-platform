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

    # ==============================================================================
    # Phase 12: Dynamic Replanning / Changes Section
    # ==============================================================================
    travel_state = st.session_state.get("travel_state", {})
    itinerary_ver = travel_state.get("itinerary_version", 1)
    replan_count = travel_state.get("replan_count", 0)
    itinerary_history = travel_state.get("itinerary_history", [])
    latest_impact = travel_state.get("latest_impact_analysis", {})
    exec_modes = travel_state.get("agent_execution_modes", {})

    st.subheader("🔄 Dynamic Replanning & Itinerary Evolution (Phase 12)")
    
    col_ver1, col_ver2, col_ver3 = st.columns([1, 2, 2])
    with col_ver1:
        st.metric(label="Current Itinerary", value=f"v{itinerary_ver}")
    with col_ver2:
        st.metric(label="Replans Applied", value=str(replan_count))
    with col_ver3:
        last_reason = travel_state.get("replan_reasons", ["Initial Creation"])[-1] if replan_count > 0 else "Initial Itinerary"
        st.metric(label="Latest Trigger", value=last_reason[:30])

    if replan_count > 0 and latest_impact:
        st.info(f"⚡ **Latest Change Event**: `{last_reason}`")
        
        # Why did the itinerary change? (Structured Explanation)
        with st.container():
            st.markdown("#### 💡 Why did the itinerary change?")
            human_expl = latest_impact.get("human_explanation") or travel_state.get("itinerary_history", [{}])[-1].get("human_explanation")
            if human_expl:
                st.markdown(
                    f"""
                    <div style="background-color: rgba(66, 165, 245, 0.08); border-left: 4px solid #42A5F5; padding: 12px 16px; border-radius: 4px; margin-bottom: 16px;">
                        <span style="font-size: 1.05rem; font-weight: 500; color: #E3F2FD;">{human_expl}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # Impacted vs Unchanged Columns
        c_impact, c_reuse = st.columns(2)
        with c_impact:
            st.markdown("##### ⚠️ Affected & Selectively Replanned")
            rerun_list = latest_impact.get("rerun_nodes", [])
            if "flight" in rerun_list:
                st.markdown("✓ **Flight Agent**: Rescheduled flight option selected")
            if "hotel" in rerun_list:
                st.markdown("✓ **Hotel Agent**: Alternative lodging assigned")
            if "activity" in rerun_list:
                aff_days = latest_impact.get("affected_days", [])
                days_txt = f"Day {', '.join(str(d) for d in aff_days)}" if aff_days else "schedule"
                st.markdown(f"✓ **Activity Agent**: Replaced outdoor/disrupted activities on {days_txt}")
            if "budget_engine" in rerun_list:
                st.markdown("✓ **Budget Engine**: Recalculated total trip expenses deterministically")
            if "validator" in rerun_list:
                st.markdown("✓ **Validator Engine**: Re-verified temporal feasibility & constraints")

        with c_reuse:
            st.markdown("##### 🛡️ Unchanged & Safely Reused")
            reuse_list = latest_impact.get("reusable_nodes", [])
            if "flight" in reuse_list:
                st.markdown("✓ **Flight Schedule**: Carrier reservations intact")
            if "hotel" in reuse_list:
                st.markdown("✓ **Hotel Booking**: Lodging selection preserved")
            if "activity" in reuse_list:
                st.markdown("✓ **Activities**: Other days' schedules unchanged")
            if "weather" in reuse_list:
                st.markdown("✓ **Weather Intelligence**: Climatology data reused")
            if "research" in reuse_list:
                st.markdown("✓ **Research Agent**: Destination guidance reused")

        # Interactive Replan Timeline
        with st.expander("⏱️ Replan Evolution Timeline", expanded=False):
            st.markdown(f"**Itinerary v1** (Initial Plan)")
            for i, hist in enumerate(itinerary_history, start=2):
                st.markdown(f"  ↓ *{hist.get('change_reason', 'Disruption')}*")
                st.markdown(f"  ↓ *Impact Analysis: Rerunning {list(hist.get('node_execution_actions', {}).keys())}*")
                st.markdown(f"**Itinerary v{i}** ({hist.get('created_at', '')[:19]}) — Status: `{ 'PASSED' if hist.get('is_valid') else 'WARNINGS' }`")

    # Interactive Simulation Form
    with st.expander("🛠️ Trigger Dynamic Replan / Disruption Event", expanded=False):
        st.markdown("Simulate a real-time event or submit a natural language change request:")
        sim_col1, sim_col2 = st.columns([1, 1])
        with sim_col1:
            scenario = st.selectbox(
                "Preset Disruption Scenario",
                [
                    "Flight Cancelled (Carrier disruption)",
                    "Flight Delayed by 4 Hours",
                    "Weather Alert: Heavy Rain on Day 3",
                    "Hotel Unavailable (Sold out)",
                    "Budget Reduced by $300",
                ],
            )
            if st.button("Trigger Preset Disruption", key="btn_preset_replan"):
                from services.replanning_service import replanning_service
                from models.replanning import ChangeEvent, ChangeEventType, ChangeEventSeverity
                
                ev_type = ChangeEventType.FLIGHT_CANCELLED
                meta = {}
                if "Delayed" in scenario:
                    ev_type = ChangeEventType.FLIGHT_DELAYED
                    meta = {"delay_hours": 4}
                elif "Weather" in scenario:
                    ev_type = ChangeEventType.WEATHER_ALERT
                    meta = {"affected_days": [3], "condition": "heavy rain"}
                elif "Hotel" in scenario:
                    ev_type = ChangeEventType.HOTEL_UNAVAILABLE
                elif "Budget" in scenario:
                    ev_type = ChangeEventType.BUDGET_CHANGED
                
                ce = ChangeEvent(
                    event_type=ev_type,
                    source="SIMULATION",
                    metadata=meta,
                    description=scenario,
                )
                updated_state, new_ver, impact = replanning_service.trigger_dynamic_replan(
                    change_event=ce,
                    current_state=travel_state,
                    user_id=travel_state.get("user_id", "demo-user"),
                    trip_id=active_trip.get("id"),
                )
                st.session_state["travel_state"] = updated_state
                st.success(f"Dynamic replan executed! Itinerary upgraded to v{new_ver.version}.")
                st.rerun()

        with sim_col2:
            custom_prompt = st.text_input("Or Natural Language Change Request", placeholder="e.g. Reduce budget to $1500, or Move Tokyo to Osaka")
            if st.button("Submit Change Request", key="btn_custom_replan") and custom_prompt:
                from services.replanning_service import replanning_service
                updated_state, new_ver, impact = replanning_service.handle_user_replan_request(
                    prompt=custom_prompt,
                    current_state=travel_state,
                    user_id=travel_state.get("user_id", "demo-user"),
                    trip_id=active_trip.get("id"),
                )
                st.session_state["travel_state"] = updated_state
                st.success(f"Change processed! Generated Itinerary v{new_ver.version}.")
                st.rerun()

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
