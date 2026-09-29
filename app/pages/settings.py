"""Settings, authentication, and environment diagnostics page."""

import sys
import streamlit as st
from config.settings import get_settings
from services.health_service import get_health_status
from services.auth_service import auth_service
from app.state.session import get_current_user, set_current_user


def render_settings_page() -> None:
    """Render system settings, Supabase Auth controls, and runtime diagnostics."""
    st.title("System Settings & Authentication")
    st.markdown("Manage your user account, authentication session, and inspect runtime configurations.")

    st.markdown("---")

    settings = get_settings()
    health = get_health_status(settings)
    current_user = get_current_user()

    # --------------------------------------------------------------------------
    # 1. Authentication & Account Management Section
    # --------------------------------------------------------------------------
    st.subheader("Account & Authentication")

    if settings.has_supabase_config and not settings.demo_mode:
        # Live Supabase Auth Mode
        if current_user and not current_user.get("is_demo"):
            st.success(f"👤 Currently signed in as: **{current_user.get('email')}**")
            st.caption(f"User ID: `{current_user.get('id')}`")
            if st.button("🚪 Sign Out", type="secondary"):
                auth_service.sign_out(st.session_state)
                st.info("Signed out successfully.")
                st.rerun()
        else:
            auth_tab_signin, auth_tab_signup = st.tabs(["🔑 Sign In", "📝 Sign Up"])

            with auth_tab_signin:
                with st.form("signin_form"):
                    email = st.text_input("Email Address", placeholder="traveler@example.com")
                    password = st.text_input("Password", type="password")
                    signin_btn = st.form_submit_button("Sign In", type="primary")

                    if signin_btn:
                        if not email or not password:
                            st.error("Please provide both email and password.")
                        else:
                            try:
                                user = auth_service.sign_in(email, password, st.session_state)
                                st.success(f"Welcome back, {user.get('email')}!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Sign in failed: {str(e)}")

            with auth_tab_signup:
                with st.form("signup_form"):
                    new_email = st.text_input("Email Address", placeholder="new.traveler@example.com")
                    new_password = st.text_input("Password (min 6 characters)", type="password")
                    full_name = st.text_input("Full Name", placeholder="Jane Doe")
                    signup_btn = st.form_submit_button("Create Account", type="primary")

                    if signup_btn:
                        if not new_email or not new_password:
                            st.error("Please provide both email and password.")
                        elif len(new_password) < 6:
                            st.error("Password must be at least 6 characters.")
                        else:
                            try:
                                new_user = auth_service.sign_up(new_email, new_password, full_name=full_name)
                                st.success("Account created successfully! You can now sign in.")
                            except Exception as e:
                                st.error(f"Registration failed: {str(e)}")

    else:
        # DEMO_MODE / Supabase Not Configured
        st.markdown(
            """
            <div style="
                border: 1px solid rgba(76, 175, 80, 0.4);
                background: rgba(76, 175, 80, 0.08);
                padding: 16px 20px;
                border-radius: 8px;
                margin-bottom: 16px;
            ">
                <h4 style="margin: 0 0 8px 0; color: #81C784;">🟢 DEMO MODE (Local Guest Identity)</h4>
                <p style="margin: 0; font-size: 0.9rem; color: #E0E0E0;">
                    Supabase credentials are not configured or DEMO_MODE is active.
                    The platform is operating with an isolated in-memory guest profile.
                    All trip and conversation data will be held in temporary memory for testing.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            st.markdown(f"**Guest Email:** `{current_user.get('email')}`")
            st.caption("Default offline traveler persona")
        with col_u2:
            st.markdown(f"**Mock User ID:** `{current_user.get('id')}`")
            st.caption("Isolation UUID for local session")

    st.markdown("---")

    # --------------------------------------------------------------------------
    # 2. Runtime Environment Diagnostics
    # --------------------------------------------------------------------------
    st.subheader("Runtime Environment")
    r1, r2, r3, r4 = st.columns(4)
    with r1:
        st.markdown("**Environment**")
        st.code(health.environment)
    with r2:
        st.markdown("**DEMO_MODE**")
        st.code(str(health.demo_mode))
    with r3:
        st.markdown("**Python Version**")
        st.code(sys.version.split()[0])
    with r4:
        st.markdown("**Streamlit Version**")
        st.code(st.__version__)

    st.markdown("---")

    # --------------------------------------------------------------------------
    # 3. System Health & Subsystem Readiness (8 Subsystems)
    # --------------------------------------------------------------------------
    st.subheader("System Health & Subsystem Readiness")
    st.caption("Real-time operational liveness and readiness probes across platform architecture. Secret values are never exposed.")

    # Top Health Status Banner
    status_color = "#10B981" if health.overall_status == "HEALTHY" else ("#F59E0B" if health.overall_status == "DEGRADED" else "#EF4444")
    st.markdown(
        f"""
        <div class="travel-card" style="border-left: 4px solid {status_color};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-size: 1.1rem; font-weight: 700; color: #F8FAFC;">OVERALL STATUS: {health.overall_status}</span>
                    <span class="badge {'badge-live' if health.overall_status == 'HEALTHY' else ('badge-warning' if health.overall_status == 'DEGRADED' else 'badge-failed')}" style="margin-left: 10px;">
                        {'READY' if health.readiness else 'UNAVAILABLE'}
                    </span>
                </div>
                <div style="font-size: 0.85rem; color: #94A3B8;">
                    <span>Liveness: <strong>{'ALIVE' if health.liveness else 'DOWN'}</strong></span> |
                    <span>Readiness: <strong>{'PASS' if health.readiness else 'FAIL'}</strong></span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 8 Subsystems Grid
    sub_col1, sub_col2 = st.columns(2)

    subsystems_list = list(health.components.items())
    for idx, (comp_key, comp_val) in enumerate(subsystems_list):
        target_col = sub_col1 if idx % 2 == 0 else sub_col2
        badge_cls = "badge-completed" if comp_val.status == "HEALTHY" else ("badge-warning" if comp_val.status in ("DEGRADED", "NOT_CONFIGURED") else "badge-failed")
        with target_col:
            st.markdown(
                f"""
                <div class="travel-card" style="margin-bottom: 12px; padding: 12px 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 600; color: #F1F5F9; font-size: 0.95rem;">{comp_val.name}</span>
                        <span class="badge {badge_cls}">{comp_val.status}</span>
                    </div>
                    <div style="font-size: 0.8rem; color: #94A3B8; margin-top: 4px;">{comp_val.details or 'Active'}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # --------------------------------------------------------------------------
    # 4. Security & Guardrails Policies (Phase 11)
    # --------------------------------------------------------------------------
    st.subheader("🛡️ Production Guardrails & Security Policies")
    st.caption("Active runtime execution limits, circuit breakers, and security parameters.")

    g1, g2, g3, g4 = st.columns(4)
    with g1:
        st.markdown("**Max Agent Steps**")
        st.code(str(settings.max_agent_steps))
        st.markdown("**Max Input Chars**")
        st.code(str(settings.max_input_chars))
    with g2:
        st.markdown("**Max Tool Calls**")
        st.code(str(settings.max_tool_calls))
        st.markdown("**Max Context Chars**")
        st.code(str(settings.max_context_chars))
    with g3:
        st.markdown("**Max Search Calls**")
        st.code(str(settings.max_search_calls))
        st.markdown("**Workflow Timeout**")
        st.code(f"{settings.workflow_timeout_seconds}s")
    with g4:
        st.markdown("**Max Retries**")
        st.code(str(settings.max_retries))
        st.markdown("**Rate Limit**")
        st.code(f"{settings.rate_limit_requests} req / {settings.rate_limit_window_seconds}s")

    st.markdown("---")

    # --------------------------------------------------------------------------
    # 5. Session Controls
    # --------------------------------------------------------------------------
    st.subheader("Session State Controls")

    if st.button("🔄 Reset Active Trip & Session State", type="secondary"):
        st.session_state.clear()
        st.success("Session state cleared.")
        st.rerun()
