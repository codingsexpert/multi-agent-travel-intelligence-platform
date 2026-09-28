"""New trip creation and structured travel requirement intake form with Supabase persistence."""

from datetime import date, timedelta
import streamlit as st
from pydantic import ValidationError as PydanticValidationError
from models.travel_request import (
    TravelRequest,
    TravelerPreferences,
    TripConstraints,
)
from app.state.session import (
    set_current_trip,
    get_current_trip,
    get_current_user,
    set_current_conversation_id,
)
from app.components.trip_summary_card import render_trip_summary_card
from repositories import trip_repository, conversation_repository, message_repository
from services.planning_service import run_travel_planning

PREFERENCE_OPTIONS = [
    "Food",
    "Culture",
    "Nature",
    "Adventure",
    "Shopping",
    "History",
    "Nightlife",
    "Photography",
    "Relaxation",
]

TRAVEL_STYLES = [
    "Budget",
    "Balanced",
    "Premium",
    "Luxury",
]

ACCOMMODATION_OPTIONS = [
    "Hostel",
    "Budget Hotel",
    "3 Star",
    "4 Star",
    "5 Star",
    "Other",
]

CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "INR"]


def render_new_trip_page() -> None:
    """Render structured trip intake form with Pydantic validation and repository persistence."""
    st.title("Plan a New Trip")
    st.markdown(
        "Specify your travel route, timing, budget, and personal preferences. All inputs are strictly validated against domain schemas before persistence."
    )

    st.markdown("---")

    current_user = get_current_user()
    today = date.today()

    with st.form("new_trip_form"):
        st.subheader("1. Core Route & Schedule")
        r_col1, r_col2 = st.columns(2)
        with r_col1:
            origin = st.text_input("Origin (City or Airport Code)", value="SFO", placeholder="e.g. SFO or San Francisco")
            dest = st.text_input("Destination", value="Tokyo", placeholder="e.g. Tokyo or Japan")
            travelers = st.number_input("Number of Travellers", min_value=1, max_value=20, value=2, step=1)

        with r_col2:
            start_d = st.date_input("Start Date", value=today + timedelta(days=30))
            end_d = st.date_input("End Date", value=today + timedelta(days=38))
            b_col1, b_col2 = st.columns([2, 1])
            with b_col1:
                budget = st.number_input("Total Budget Limit", min_value=100.0, value=5000.0, step=100.0)
            with b_col2:
                currency = st.selectbox("Currency", options=CURRENCIES, index=0)

        st.markdown("---")
        st.subheader("2. Travel Preferences & Style")

        p_col1, p_col2 = st.columns(2)
        with p_col1:
            selected_interests = st.multiselect(
                "Travel Interests (Select all that apply)",
                options=PREFERENCE_OPTIONS,
                default=["Food", "Culture", "History"],
            )
            travel_style = st.selectbox("Travel Pace & Style", options=TRAVEL_STYLES, index=1)

        with p_col2:
            accommodation = st.selectbox("Accommodation Preference", options=ACCOMMODATION_OPTIONS, index=3)
            direct_flights = st.checkbox("Require direct / non-stop flights only", value=False)
            kid_friendly = st.checkbox("Require kid-friendly venues & pacing", value=False)

        st.markdown("---")
        st.subheader("3. Additional Requirements & Constraints")
        additional_notes = st.text_area(
            "Free-form notes, must-see landmarks, or dietary restrictions",
            value="",
            placeholder="e.g. We love authentic ramen, hate rushing between museums, and need vegetarian dining options.",
            height=100,
        )

        submitted = st.form_submit_button("🚀 Plan My Trip", type="primary", use_container_width=True)

    if submitted:
        # Step 1: Validate input using Pydantic models
        try:
            style_pace_map = {
                "Budget": "moderate",
                "Balanced": "moderate",
                "Premium": "relaxed",
                "Luxury": "relaxed",
            }
            pace = style_pace_map.get(travel_style, "moderate")

            must_include_items = []
            if additional_notes.strip():
                must_include_items.append(additional_notes.strip()[:100])

            travel_req = TravelRequest(
                origin=origin,
                destination=dest,
                start_date=start_d,
                end_date=end_d,
                travelers=travelers,
                budget=float(budget),
                currency=currency,
                preferences=TravelerPreferences(
                    interests=selected_interests,
                    pace=pace,
                    accommodation_type=accommodation.lower(),
                    cabin_class="economy" if travel_style in ["Budget", "Balanced"] else "premium_economy",
                ),
                constraints=TripConstraints(
                    direct_flights_only=direct_flights,
                    kid_friendly=kid_friendly,
                    must_include=must_include_items,
                ),
            )

            # Step 2: Persist trip and associated preferences
            trip_payload = {
                "origin": travel_req.origin,
                "destination": travel_req.destination,
                "start_date": travel_req.start_date,
                "end_date": travel_req.end_date,
                "travelers": travel_req.travelers,
                "budget": travel_req.budget,
                "currency": travel_req.currency,
                "status": "DRAFT",
            }
            preferences_payload = {
                "preferences": travel_req.preferences.interests,
                "travel_style": travel_style,
                "accommodation_preference": accommodation,
                "additional_requirements": additional_notes.strip(),
            }

            created_trip = trip_repository.create_trip(
                user_id=current_user["id"],
                trip_data=trip_payload,
                preferences_data=preferences_payload,
            )

            # Step 3: Create associated conversation thread
            conv_title = f"Trip to {travel_req.destination} ({travel_req.start_date})"
            conv = conversation_repository.create_conversation(
                user_id=current_user["id"],
                trip_id=created_trip["id"],
                title=conv_title,
            )

            # Step 4: Run LangGraph Planning Workflow
            msg_content = (
                f"Trip Request: {travel_req.origin} to {travel_req.destination}, "
                f"{travel_req.start_date} to {travel_req.end_date} for {travel_req.travelers} traveler(s). "
                f"Budget: {travel_req.currency} {travel_req.budget:,.2f}. "
                f"Interests: {', '.join(selected_interests) if selected_interests else 'General'}. "
                f"Notes: {additional_notes or 'None'}"
            )
            planning_state = run_travel_planning(
                user_request=msg_content,
                user_id=current_user["id"],
                trip_id=created_trip["id"],
                conversation_id=conv["id"],
                session_state=st.session_state,
            )

            # Step 5: Update session state
            set_current_trip(travel_req, trip_id=created_trip["id"])
            set_current_conversation_id(conv["id"])

            # Step 6: User feedback
            if created_trip.get("is_demo") or planning_state.get("is_demo"):
                st.info("ℹ️ **DEMO_MODE Active**: Running offline using mock storage and deterministic Planner Agent.")
            else:
                st.success(f"✅ Trip successfully saved to Supabase! (Trip ID: `{created_trip['id']}`)")

            if planning_state.get("clarification_required"):
                st.warning("⚠️ **Clarification Required**: Additional travel details needed before planning.")
                for q in planning_state.get("clarification_questions", []):
                    st.markdown(f"• {q}")
                st.caption("💬 Head to the **Conversation** page to provide these details to the assistant.")
            else:
                status_text = planning_state.get("planning_status", "READY_FOR_VALIDATION")
                st.success(f"✅ **Multi-Agent Travel Analysis Complete.** (Status: `{status_text}`)")

                st.markdown("#### Specialized Agents Execution Progress (DEMO DATA)")
                runs = planning_state.get("agent_runs", [])
                run_status_map = {r.get("agent_name"): r.get("status") for r in runs}

                prog_col1, prog_col2, prog_col3 = st.columns(3)
                with prog_col1:
                    p_st = run_status_map.get("planner", "SUCCESS")
                    f_st = run_status_map.get("flight", "SUCCESS")
                    st.markdown(f"• **Planner Agent**: `✓ {p_st}`")
                    st.markdown(f"• **Flight Agent**: `✓ {f_st}`")
                with prog_col2:
                    h_st = run_status_map.get("hotel", "SUCCESS")
                    a_st = run_status_map.get("activity", "SUCCESS")
                    st.markdown(f"• **Hotel Agent**: `✓ {h_st}`")
                    st.markdown(f"• **Activity Agent**: `✓ {a_st}`")
                with prog_col3:
                    w_st = run_status_map.get("weather", "SUCCESS")
                    r_st = run_status_map.get("research", "SUCCESS")
                    st.markdown(f"• **Weather Agent**: `✓ {w_st}`")
                    st.markdown(f"• **Research Agent**: `✓ {r_st}`")

                st.caption("🔍 Navigate to **Flights**, **Hotels**, **Activities**, **Weather**, or **Agent Trace** in the sidebar to inspect domain deliverables.")

            st.markdown("### Submitted Trip Overview")
            render_trip_summary_card(travel_req)

        except PydanticValidationError as e:
            st.error("❌ Validation Error: Please check your input parameters.")
            for err in e.errors():
                field = " -> ".join(str(loc) for loc in err["loc"])
                st.write(f"• **{field}**: {err['msg']}")
        except Exception as e:
            st.error(f"❌ Error persisting trip: {str(e)}")

    # Current active trip display
    elif get_current_trip() is not None:
        st.markdown("---")
        st.markdown("### Current Active Trip in Session")
        active_trip_obj = get_current_trip()
        render_trip_summary_card(active_trip_obj)

        active_trip_id = st.session_state.get("current_trip_id")
        if st.button("⚡ Run / Re-run Travel Analysis", type="primary", use_container_width=True):
            with st.spinner("Executing Multi-Agent Workflow (Planner, Flight, Hotel, Activity, Weather, Research)..."):
                analysis_prompt = (
                    f"Trip from {active_trip_obj.origin} to {active_trip_obj.destination} "
                    f"from {active_trip_obj.start_date} to {active_trip_obj.end_date} for {active_trip_obj.travelers} traveler(s), "
                    f"budget {active_trip_obj.currency} {active_trip_obj.budget:,.2f}."
                )
                run_travel_planning(
                    user_request=analysis_prompt,
                    user_id=current_user["id"],
                    trip_id=active_trip_id,
                    session_state=st.session_state,
                )
            st.success("✅ Multi-Agent Workflow Executed! Check Flights, Hotels, Activities, and Weather in the sidebar.")
            st.rerun()
