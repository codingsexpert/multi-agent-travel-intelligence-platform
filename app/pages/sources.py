"""Sources, citations, and ground-truth knowledge retrieval page."""

import streamlit as st


def render_sources_page() -> None:
    """Render verified knowledge sources and citation references."""
    st.title("Information Sources & Citations")
    st.markdown(
        "Grounding citations retrieved from Supabase pgvector RAG, verified live travel APIs, and real-time web search."
    )

    st.markdown("---")

    # Categories tabs
    tab_rag, tab_web, tab_api = st.tabs([
        "📚 pgvector RAG Knowledge Base",
        "🌐 Live Web Search Results",
        "🔌 External Travel APIs (MCP)",
    ])

    with tab_rag:
        st.subheader("Curated Destination Knowledge")
        st.caption("Target: Static visa guides, cultural customs, seasonal patterns, neighborhood profiles")
        st.info("No sources available yet.")

    with tab_web:
        st.subheader("Live Web Disruption & Event Radar")
        st.caption("Target: Tavily / Brave Search live queries, terminal updates, local festival dates")
        st.info("No sources available yet.")

    with tab_api:
        st.subheader("Direct Provider Feeds")
        st.caption("Target: Amadeus Flight/Hotel inventory and OpenWeather 14-day forecasts")
        st.info("No sources available yet.")
