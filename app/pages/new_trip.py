"""New trip creation and structured travel requirement intake form."""

from datetime import date, timedelta
import streamlit as st
from pydantic import ValidationError as PydanticValidationError
from models.travel_request import (
    TravelRequest,
    TravelerPreferences,
    TripConstraints,
)
from app.state.session import set_current_trip, get_current_trip
from app.components.trip_summary_card import render_trip_summary_card

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
    """Render structured trip intake form with Pydantic validation."""
    st.title("Plan a New Trip")
    st.markdown(
        "Specify your travel route, timing, budget, and personal preferences. All inputs are strictly validated against domain schemas before orchestration."
    )

    st.markdown("---")

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
            # Map travel style to pace
            style_pace_map = {
                "Budget": "moderate",
                "Balanced": "moderate",
                "Premium": "relaxed",
                "Luxury": "relaxed",
            }
            pace = style_pace_map.get(travel_style, "moderate")

            # Extract must-include landmarks from free text if specified
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

            # Step 2: Store the request in Streamlit session state
            set_current_trip(travel_req)

            # Step 3: Show structured summary of request
            st.success("✅ Travel request validated and registered into session state!")

            # Step 4: Show message that LangGraph planning workflow will be connected in a later phase
            st.info(
                "ℹ️ **LangGraph Planning Workflow Connection**: The multi-agent LangGraph orchestrator (Planner, Flight, Hotel, Activity, and Budget agents) will be connected in Phase 4 & Phase 5. No fake itinerary data has been generated."
            )

            st.markdown("### Submitted Request Summary")
            render_trip_summary_card(travel_req)

        except PydanticValidationError as e:
            st.error("❌ Validation Error: Please check your input parameters.")
            for err in e.errors():
                field = " -> ".join(str(loc) for loc in err["loc"])
                st.write(f"• **{field}**: {err['msg']}")
        except Exception as e:
            st.error(f"❌ Unexpected Error: {str(e)}")

    # If there is already an active trip in session state and form was not just submitted, display it
    elif get_current_trip() is not None:
        st.markdown("---")
        st.markdown("### Current Active Trip in Session")
        render_trip_summary_card(get_current_trip())
