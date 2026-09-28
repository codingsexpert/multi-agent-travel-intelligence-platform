"""Component for rendering structured travel request summary cards."""

import streamlit as st
from models.travel_request import TravelRequest


def render_trip_summary_card(request: TravelRequest, show_id: bool = True) -> None:
    """Render a clean, structured summary card for a TravelRequest entity."""
    with st.container():
        st.markdown(
            f"""
            <div style="
                border: 1px solid rgba(128, 128, 128, 0.2);
                border-radius: 8px;
                padding: 18px 24px;
                margin-bottom: 20px;
                background-color: rgba(255, 255, 255, 0.03);
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h3 style="margin: 0; font-size: 1.35rem; color: #1E88E5;">
                        ✈️ {request.origin} &rarr; {request.destination}
                    </h3>
                    <span style="
                        font-size: 0.85rem;
                        padding: 4px 10px;
                        border-radius: 12px;
                        background: rgba(30, 136, 229, 0.15);
                        color: #64B5F6;
                        font-weight: 600;
                    ">
                        {request.metadata.status}
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown("**Dates**")
            st.write(f"{request.start_date} to {request.end_date}")
            st.caption(f"Duration: {request.duration_days} days")

        with c2:
            st.markdown("**Travellers**")
            st.write(f"{request.travelers} Person{'s' if request.travelers > 1 else ''}")
            st.caption(f"Style: {request.preferences.pace.capitalize()} pace")

        with c3:
            st.markdown("**Budget**")
            st.write(f"{request.currency} {request.budget:,.2f}")
            st.caption(f"Class: {request.preferences.cabin_class.replace('_', ' ').capitalize()}")

        with c4:
            st.markdown("**Lodging Type**")
            st.write(request.preferences.accommodation_type.capitalize())
            if show_id:
                st.caption(f"ID: {request.metadata.trip_id[:8]}...")

        # Preferences and Constraints
        p_col, c_col = st.columns(2)
        with p_col:
            st.markdown("**Interests & Preferences**")
            if request.preferences.interests:
                st.write(", ".join(request.preferences.interests))
            else:
                st.caption("No specific interests selected")

            if request.preferences.dietary_restrictions:
                st.caption(f"Dietary: {', '.join(request.preferences.dietary_restrictions)}")

        with c_col:
            st.markdown("**Operational Constraints**")
            constraints_list = []
            if request.constraints.direct_flights_only:
                constraints_list.append("Direct flights required")
            if request.constraints.kid_friendly:
                constraints_list.append("Kid-friendly activities required")
            if request.constraints.must_include:
                constraints_list.append(f"Must include: {', '.join(request.constraints.must_include)}")
            if request.constraints.avoid:
                constraints_list.append(f"Avoid: {', '.join(request.constraints.avoid)}")

            if constraints_list:
                for c in constraints_list:
                    st.write(f"• {c}")
            else:
                st.caption("Standard operational constraints (no custom exclusions)")
