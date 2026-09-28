"""Sources, citations, and ground-truth knowledge retrieval page."""

import streamlit as st


def render_sources_page() -> None:
    """Render verified knowledge sources, destination research, and citation references."""
    st.title("Information Sources & Destination Research")
    st.markdown(
        "Destination cultural etiquette, travel logistics, and grounding knowledge compiled by the Research Agent."
    )

    st.markdown("---")

    travel_state = st.session_state.get("travel_state", {})
    research = travel_state.get("research_results")

    if not research:
        st.info(
            "ℹ️ **No Destination Research Compiled Yet**: Plan a trip from **New Trip** or **Conversation** to execute the multi-agent workflow and compile destination intelligence."
        )
        return

    st.success(f"📚 **Destination Research: {research.get('destination', 'Target Destination')}**")
    st.caption("⚠️ **DEMO_DATA**: Synthesized by the mock Research Agent from controlled knowledge fixtures. Real-time RAG and Web Search will be connected in Phases 9 & 10.")

    st.markdown("### Destination Overview")
    st.write(research.get("destination_overview", "Overview unavailable."))

    r_col1, r_col2 = st.columns(2)
    with r_col1:
        st.markdown("### 🏛️ Cultural Etiquette & Norms")
        for item in research.get("cultural_notes", []):
            st.markdown(f"• {item}")

        st.markdown("### 🤝 Local Customs & Manners")
        for item in research.get("local_customs", []):
            st.markdown(f"• {item}")

    with r_col2:
        st.markdown("### 💡 Practical Travel Tips")
        for item in research.get("travel_tips", []):
            st.markdown(f"• {item}")

        st.markdown("### ⚠️ Important Advisories")
        for item in research.get("important_notes", []):
            st.markdown(f"• {item}")

    st.markdown("---")
    st.caption(f"Sources Attributed: {', '.join(research.get('sources', []))}")
