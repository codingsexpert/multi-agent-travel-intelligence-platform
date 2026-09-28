"""Settings and environment configuration diagnostics page."""

import sys
import streamlit as st
from config.settings import get_settings
from services.health_service import get_health_status


def render_settings_page() -> None:
    """Render system settings and configuration presence without revealing secrets."""
    st.title("System Settings & Diagnostics")
    st.markdown("Inspect local runtime environment, dependency versions, and service configuration presence.")

    st.markdown("---")

    settings = get_settings()
    health = get_health_status(settings)

    # Runtime Environment
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

    # Configuration Presence (Secrets strictly protected)
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
            st.caption("Using in-memory session state fallback (DEMO_MODE)")

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

    # Session Management
    st.subheader("Session State Controls")
    if st.button("🔄 Reset Active Trip & Session State", type="secondary"):
        st.session_state.clear()
        st.success("Session state cleared.")
        st.rerun()
