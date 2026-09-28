"""Streamlit application entry point for the Multi-Agent Travel Intelligence Platform."""

import streamlit as st
from config.settings import get_settings
from services.health_service import get_health_status
from models.travel_request import TravelRequest, TravelerPreferences, TripConstraints
from datetime import date, timedelta


def main():
    """Render minimal Phase 1 foundation dashboard."""
    st.set_page_config(
        page_title="Multi-Agent AI Travel Intelligence Platform",
        page_icon="✈️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Load configuration & health status
    settings = get_settings()
    health = get_health_status(settings)

    # Header
    st.title("✈️ Multi-Agent AI Travel Intelligence Platform")
    st.caption("Phase 1: Project Foundation & Development Environment")

    st.markdown("---")

    # Environment Banner
    col_env, col_health = st.columns([1, 1])
    with col_env:
        env_badge = (
            "🟢 DEMO MODE (Offline Capable)"
            if health.demo_mode
            else f"🔵 {health.environment}"
        )
        st.subheader("Environment")
        st.info(env_badge)

    with col_health:
        st.subheader("Overall System Status")
        if health.overall_status == "HEALTHY":
            st.success(f"Status: **{health.overall_status}**")
        elif health.overall_status == "DEGRADED":
            st.warning(f"Status: **{health.overall_status}**")
        else:
            st.error(f"Status: **{health.overall_status}**")

    st.markdown("### System Status")

    # Required status metrics
    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.metric(label="Configuration", value=health.configuration_status)

    with m2:
        st.metric(label="Supabase", value=health.supabase_status)

    with m3:
        st.metric(label="LLM", value=health.llm_status)

    with m4:
        st.metric(label="LangSmith", value=health.langsmith_status)

    # Component details expander
    with st.expander("🔍 Component Configuration Details", expanded=False):
        for key, comp in health.components.items():
            st.write(f"**{comp.name}**: `{comp.status}` — {comp.details}")

    st.markdown("---")

    # Foundation Demo: Pydantic Schema Verification Sandbox
    st.markdown("### 🧪 Foundation Verification: Travel Request Model")
    st.write(
        "Verify that core Pydantic validation rules and data contracts function properly in this environment."
    )

    with st.form("test_request_form"):
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            origin = st.text_input("Origin Airport / City", value="SFO")
            dest = st.text_input("Destination City", value="Tokyo")
            travelers = st.number_input("Travelers", min_value=1, value=2, step=1)
        with f_col2:
            today = date.today()
            start = st.date_input("Start Date", value=today + timedelta(days=30))
            end = st.date_input("End Date", value=today + timedelta(days=37))
            budget = st.number_input("Budget ($)", min_value=100.0, value=4500.0, step=100.0)

        submitted = st.form_submit_button("Validate TravelRequest Schema")

        if submitted:
            try:
                req = TravelRequest(
                    origin=origin,
                    destination=dest,
                    start_date=start,
                    end_date=end,
                    travelers=travelers,
                    budget=budget,
                    currency="USD",
                    preferences=TravelerPreferences(interests=["Culinary", "Culture"], pace="moderate"),
                    constraints=TripConstraints(kid_friendly=False),
                )
                st.success(
                    f"✅ Schema validation passed! Duration: {req.duration_days} days, Trip ID: `{req.metadata.trip_id}`"
                )
                st.json(req.model_dump(mode="json"))
            except Exception as e:
                st.error(f"❌ Validation failed: {e}")


if __name__ == "__main__":
    main()
