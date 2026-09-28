"""Sources, citations, and ground-truth RAG knowledge retrieval page."""

import streamlit as st
from models.rag import RAGRetrievalQuery, SourceTrustLevel
from rag.retriever import travel_knowledge_retriever


def render_sources_page() -> None:
    """Render curated travel knowledge base, vector retrieval sandbox, and citations."""
    st.title("Travel Knowledge & RAG Retrieval")
    st.markdown(
        "Grounding travel intelligence powered by **Supabase pgvector**, curated destination knowledge bases, and multi-agent retrieval."
    )

    tab_kb, tab_research, tab_arch = st.tabs([
        "📚 Knowledge Base & Sandbox",
        "🏛️ Destination Research (Active Trip)",
        "🛡️ RAG Architecture & Guardrails",
    ])

    with tab_kb:
        render_knowledge_sandbox()

    with tab_research:
        render_active_trip_research()

    with tab_arch:
        render_rag_architecture_guide()


def render_knowledge_sandbox() -> None:
    """Render indexed knowledge base overview and interactive vector retrieval sandbox."""
    summary = travel_knowledge_retriever.get_knowledge_summary()

    # Metric Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Curated Documents", summary.get("total_documents", 0))
    with k2:
        st.metric("Vector Chunks", summary.get("total_chunks", 0))
    with k3:
        st.metric("Embedding Model", summary.get("embedding_model", "text-embedding-3-small"))
    with k4:
        mode_badge = "🟢 LIVE PGVECTOR" if summary.get("mode") == "LIVE" else "🟡 DEMO STORE"
        st.metric("Retrieval Mode", mode_badge)

    st.markdown("---")

    # Interactive Query Sandbox
    st.markdown("### 🔍 Interactive RAG Retrieval Sandbox")
    st.caption("Perform semantic vector similarity search with metadata filtering directly against the knowledge base.")

    c_q1, c_q2 = st.columns([3, 1])
    with c_q1:
        query_input = st.text_input(
            "Natural Language Travel Query",
            value="Best cultural experiences and etiquette in Tokyo",
            placeholder="e.g. Best cultural experiences in Tokyo or tube escalator rules London",
            key="rag_sandbox_query",
        )
    with c_q2:
        dest_options = ["All Destinations"] + summary.get("destinations", [])
        selected_dest = st.selectbox("Destination Filter", dest_options, key="rag_sandbox_dest")

    f1, f2, f3 = st.columns(3)
    with f1:
        cat_options = ["All Categories"] + summary.get("categories", [])
        selected_cat = st.selectbox("Category Filter", cat_options, key="rag_sandbox_cat")
    with f2:
        top_k = st.slider("Top K Chunks", min_value=1, max_value=8, value=3, key="rag_sandbox_topk")
    with f3:
        min_sim = st.slider("Min Similarity Cutoff", min_value=0.0, max_value=0.9, value=0.0, step=0.05, key="rag_sandbox_sim")

    if st.button("🔎 Execute Vector Retrieval", type="primary", key="rag_run_search"):
        filter_dest = None if selected_dest == "All Destinations" else selected_dest
        filter_cat = None if selected_cat == "All Categories" else selected_cat

        query_obj = RAGRetrievalQuery(
            query=query_input,
            destination=filter_dest,
            category=filter_cat,
            top_k=top_k,
            min_similarity=min_sim,
        )

        with st.spinner("Embedding query and querying vector database..."):
            result = travel_knowledge_retriever.retrieve(query_obj)

        st.markdown(f"#### Retrieval Results: {result.total_chunks} chunks ({result.latency_ms:.1f}ms latency)")

        if not result.results:
            st.warning("No chunks matched your query and filter criteria.")
        else:
            for idx, chunk in enumerate(result.results, 1):
                trust_color = "#2E7D32" if chunk.source_trust == SourceTrustLevel.OFFICIAL else "#1565C0"
                sim_pct = int(chunk.similarity_score * 100)

                with st.expander(f"{idx}. {chunk.title} — Similarity: {chunk.similarity_score:.3f} ({sim_pct}%)", expanded=(idx == 1)):
                    st.markdown(
                        f"""
                        <div style="display: flex; gap: 12px; margin-bottom: 8px;">
                            <span style="background: {trust_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold;">
                                {chunk.source_trust.value}
                            </span>
                            <span style="background: rgba(128,128,128,0.2); padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">
                                Category: <strong>{chunk.category}</strong>
                            </span>
                            <span style="background: rgba(128,128,128,0.2); padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">
                                Destination: <strong>{chunk.destination or 'Global'}</strong>
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.markdown(f"**Cleaned Context Content:**")
                    st.info(chunk.content)

                    st.markdown(f"**Verified Citation:** `{chunk.citation_str}`")
                    st.caption(f"Chunk Identifier: `{chunk.chunk_id}` | Untrusted Data Boundary: `untrusted={chunk.untrusted}`")


def render_active_trip_research() -> None:
    """Render compiled research results for active trip session."""
    travel_state = st.session_state.get("travel_state", {})
    research = travel_state.get("research_results")

    if not research:
        st.info(
            "ℹ️ **No Destination Research Compiled Yet**: Plan a trip from **New Trip** or **Conversation** to execute the multi-agent workflow and compile destination intelligence."
        )
        return

    dest_name = research.get("destination", "Target Destination")
    st.success(f"📚 **Grounding Destination Intelligence: {dest_name}**")

    # Observability notice
    rag_retrievals = travel_state.get("rag_retrievals", [])
    if rag_retrievals:
        total_retrieved = sum(r.get("chunks_retrieved", 0) for r in rag_retrievals)
        st.caption(f"⚡ Grounded with **{total_retrieved} verified knowledge chunks** retrieved via Supabase pgvector.")

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
    st.markdown("### 📑 Ground-Truth Citations")
    for s in research.get("sources", []):
        st.markdown(f"- {s}")


def render_rag_architecture_guide() -> None:
    """Render RAG taxonomy, prompt injection defenses, and architectural roles."""
    st.markdown("### Information Retrieval Strategy Matrix")

    st.code(
        """
                USER QUERY
                     ↓
                  AGENT
                     ↓
              RAG RETRIEVER
                     ↓
             Supabase pgvector
                     ↓
          Semantic + Metadata Filter
                     ↓
             Relevant Chunks
                     ↓
                   AGENT
        """,
        language="text",
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### 📚 RAG Knowledge")
        st.markdown(
            """
            - **Scope**: Stable, curated travel knowledge.
            - **Contents**: Local customs, cultural etiquette, attraction history, transit rules, neighborhood guides.
            - **Latency**: Very Fast (5-20ms).
            - **Engine**: Supabase pgvector + HNSW index.
            - **Update Frequency**: Editorial releases, vetted monthly.
            """
        )
    with col2:
        st.markdown("#### ⚡ MCP / Provider APIs")
        st.markdown(
            """
            - **Scope**: Structured live operational data.
            - **Contents**: Flight availability, seat inventory, hotel nightly rates, real-time weather forecasts, FX rates.
            - **Latency**: 100-800ms.
            - **Engine**: Amadeus GDS, Open-Meteo, Frankfurter ECB.
            - **Update Frequency**: Live queries on demand.
            """
        )
    with col3:
        st.markdown("#### 🌐 Web Search (Phase 10)")
        st.markdown(
            """
            - **Scope**: Fresh, dynamic, breaking information.
            - **Contents**: Travel advisories, transport strikes, local events, seasonal festivals, emergency bulletins.
            - **Latency**: 400-1200ms.
            - **Engine**: Tavily / Brave Search API.
            - **Update Frequency**: Real-time web index.
            """
        )

    st.markdown("---")
    st.markdown("### 🛡️ Prompt Injection & Untrusted Data Defense")
    st.markdown(
        """
        Retrieved documents are treated strictly as **UNTRUSTED DATA**. Under no circumstances can retrieved knowledge:
        1. Alter LangGraph agent routing or workflow states.
        2. Override system or developer prompt instructions.
        3. Grant tool invocation permissions or bypass validation constraints.
        4. Fabricate external URLs or citations.
        """
    )
