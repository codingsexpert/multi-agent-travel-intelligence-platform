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
    # 3. External Service Configurations (Secrets strictly protected)
    # --------------------------------------------------------------------------
    st.subheader("External Service Configurations")
    st.caption("Presence indicators only; secret values are never displayed or transmitted.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### Supabase Database & Auth")
        if settings.has_supabase_config:
            st.success("✅ Configured")
            st.caption(f"Host: `{settings.supabase_url}`")
        else:
            st.warning("⚠️ Not Configured")
            st.caption("Using in-memory repository fallback (DEMO_MODE)")

    with c2:
        st.markdown("#### LLM Reasoning Provider")
        if settings.has_llm_config:
            st.success("✅ Configured")
            st.caption(f"Primary: `{settings.primary_llm_model}`")
        else:
            st.warning("⚠️ Not Configured")
            st.caption("Using deterministic mock engines (DEMO_MODE)")

    with c3:
        st.markdown("#### LangSmith Observability")
        if settings.has_langsmith_config:
            st.success("✅ Configured")
            st.caption(f"Project: `{settings.langsmith_project}`")
        else:
            st.warning("⚠️ Not Configured")
            st.caption("Distributed tracing disabled")

    st.markdown("---")

    # --------------------------------------------------------------------------
    # 4. Session Controls
    # --------------------------------------------------------------------------
    st.subheader("Session State Controls")
    if st.button("🔄 Reset Active Trip & Session State", type="secondary"):
        st.session_state.clear()
        st.success("Session state cleared.")
        st.rerun()
