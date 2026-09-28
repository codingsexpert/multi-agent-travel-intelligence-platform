"""Sources, citations, and ground-truth RAG & Fresh Web Research page."""

from datetime import datetime, timezone
import streamlit as st
from models.rag import RAGRetrievalQuery, SourceTrustLevel
from rag.retriever import travel_knowledge_retriever
from services.research_service import research_service, InformationRouter
from models.research import SourceTrustCategory


def render_sources_page() -> None:
    """Render curated travel knowledge base, vector retrieval sandbox, fresh web research, and citations."""
    st.title("Travel Intelligence: RAG & Fresh Web Research")
    st.markdown(
        "Dual-engine grounding: **Curated RAG** (Supabase pgvector) for cultural etiquette and stable heritage, "
        "paired with **Search MCP** for fresh events, temporary closures, and official advisories."
    )

    tab_fresh, tab_kb, tab_trip, tab_arch = st.tabs([
        "🌐 Fresh Web Research (Search MCP)",
        "📚 Curated Knowledge Base (RAG)",
        "🏛️ Active Trip Intelligence",
        "🛡️ Routing & Trust Architecture",
    ])

    with tab_fresh:
        render_fresh_research_sandbox()

    with tab_kb:
        render_knowledge_sandbox()

    with tab_trip:
        render_active_trip_research()

    with tab_arch:
        render_rag_architecture_guide()


def render_fresh_research_sandbox() -> None:
    """Render interactive web search and fresh information research interface."""
    st.markdown("### 🌐 Fresh Web Research & Verification Engine")
    st.caption(
        "Retrieve time-sensitive information (festivals, temporary attraction closures, flight disruptions, "
        "and official border advisories) via the Search MCP boundary."
    )

    # Search Configuration
    c_q1, c_q2 = st.columns([3, 1])
    with c_q1:
        fresh_query = st.text_input(
            "Natural Language Research Query",
            value="Tokyo festivals and cultural events autumn 2026",
            placeholder="e.g. Tokyo festivals autumn 2026 or Paris metro strike disruptions",
            key="fresh_sandbox_query",
        )
    with c_q2:
        fresh_dest = st.text_input(
            "Destination Focus",
            value="Tokyo",
            placeholder="e.g. Tokyo, Paris, London",
            key="fresh_sandbox_dest",
        )

    f1, f2, f3 = st.columns(3)
    with f1:
        recency = st.selectbox(
            "Freshness Window",
            options=["today", "24h", "7d", "30d", "all"],
            index=2,
            key="fresh_sandbox_recency",
        )
    with f2:
        is_demo_mode = st.toggle("DEMO Mode (Deterministic Sandbox)", value=True, key="fresh_sandbox_demo")
    with f3:
        st.markdown(
            f"""
            <div style="margin-top: 24px;">
                <span style="background: {'#F57F17' if is_demo_mode else '#2E7D32'}; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 0.85rem;">
                    {'🟡 DEMO MODE' if is_demo_mode else '🟢 LIVE PROVIDER'}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.button("🔎 Execute Fresh Web Research", type="primary", key="fresh_run_search"):
        with st.spinner("Executing Search MCP workflow (search_news -> web_search -> fetch_page -> verification)..."):
            research_out = research_service.execute_fresh_research(
                destination=fresh_dest,
                query_context=fresh_query,
                is_demo=is_demo_mode,
            )

        # Telemetry & Status Summary
        st.markdown("---")
        t1, t2, t3, t4 = st.columns(4)
        with t1:
            st.metric("Total Findings", len(research_out.findings))
        with t2:
            st.metric("Sources Evaluated", len(research_out.sources))
        with t3:
            auth_badge = "✅ VERIFIED" if research_out.official_verified else "⚠️ INCOMPLETE"
            st.metric("Official Verification", auth_badge)
        with t4:
            st.metric("Data Mode", research_out.data_mode)

        # Warnings / Discrepancies
        if research_out.warnings:
            for w in research_out.warnings:
                st.warning(f"⚠️ {w}")

        # Conflicting Claims Panel
        if research_out.conflicts:
            st.markdown("#### ⚡ Conflicting Claims & Source Disagreements")
            for c in research_out.conflicts:
                with st.expander(f"⚠️ Discrepancy: {c.topic}", expanded=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Claim A:** {c.claim_a}")
                        st.caption(f"Source: `{c.source_a}` | Date: `{c.date_a or 'N/A'}`")
                    with c2:
                        st.markdown(f"**Claim B:** {c.claim_b}")
                        st.caption(f"Source: `{c.source_b}` | Date: `{c.date_b or 'N/A'}`")
                    st.info(f"💡 **Uncertainty Guidance:** {c.uncertainty_note}")

        # Findings List
        st.markdown("#### 📋 Extracted Evidence & Findings")
        for idx, f in enumerate(research_out.findings, 1):
            is_auth = f.is_authoritative
            cat_color = "#2E7D32" if is_auth else "#1565C0"
            conf_pct = int(f.confidence * 100)

            with st.expander(f"{idx}. [{f.category.upper()}] {f.claim[:90]}... (Confidence: {conf_pct}%)", expanded=(idx <= 2)):
                st.markdown(
                    f"""
                    <div style="display: flex; gap: 10px; margin-bottom: 8px;">
                        <span style="background: {cat_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold;">
                            {'OFFICIAL AUTHORITY' if is_auth else 'GENERAL SOURCE'}
                        </span>
                        <span style="background: rgba(128,128,128,0.2); padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">
                            Category: <strong>{f.category}</strong>
                        </span>
                        <span style="background: rgba(128,128,128,0.2); padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">
                            Published: <strong>{f.published_at or 'Recent'}</strong>
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.write(f.claim)
                st.caption(f"Attributed Sources: {', '.join(f.sources)} | Retrieved: {f.retrieved_at}")

        # Sources Table
        st.markdown("#### 📑 Evaluated Web Sources & Trust Classifications")
        src_rows = []
        for s in research_out.sources:
            stype = s.get("source_type", "UNKNOWN")
            trust_icon = {
                "OFFICIAL": "🏛️ OFFICIAL",
                "NEWS": "📰 NEWS",
                "REFERENCE": "📚 REFERENCE",
                "COMMUNITY": "💬 COMMUNITY",
                "UNKNOWN": "❓ UNKNOWN",
            }.get(stype, stype)

            src_rows.append({
                "Source Title": s.get("title", "Web Page"),
                "Domain": s.get("domain", "web"),
                "Trust Level": trust_icon,
                "Published Date": s.get("published_at") or "Recent",
                "Retrieved Time": s.get("retrieved_at") or "Just now",
                "URL": s.get("url") or "--",
            })
        st.table(src_rows)


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

                    st.markdown("**Cleaned Context Content:**")
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

    # Fresh Findings Section (Phase 10)
    fresh_findings = research.get("fresh_findings", [])
    if fresh_findings:
        st.markdown("### 🌐 Fresh Web & News Intelligence (Phase 10)")
        auth_status = "✅ Official Government Verification Confirmed" if research.get("official_verified") else "ℹ️ Standard Web Coverage"
        st.caption(f"Live status: **{auth_status}**")

        for f in fresh_findings[:4]:
            cat = f.get("category", "general")
            st.info(f"**[{cat.upper()}]** {f.get('claim')}")

    # Conflicts Section (Phase 10)
    conflicts = research.get("conflicts", [])
    if conflicts:
        st.markdown("### ⚠️ Source Disagreements & Uncertainty Flags")
        for c in conflicts:
            st.warning(
                f"**{c.get('topic')}:**\n"
                f"- *{c.get('source_a')}:* {c.get('claim_a')}\n"
                f"- *{c.get('source_b')}:* {c.get('claim_b')}\n"
                f"💡 {c.get('uncertainty_note')}"
            )

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
    """Render RAG vs Web Search taxonomy, source-selection diagram, and security boundaries."""
    st.markdown("### Source-Selection Matrix & Information Routing")
    st.caption("How the platform deterministically dispatches user queries to the optimal knowledge and operational layers.")

    st.code(
        """
                    USER REQUEST
                         ↓
                 INFORMATION TYPE
                         ↓
        ┌────────────────┼────────────────┐
        ↓                ↓                ↓
      RAG             MCP/API         WEB SEARCH
        ↓                ↓                ↓
 Stable Knowledge    Live Structured   Fresh Info
        └────────────────┼────────────────┘
                         ↓
                      AGENTS
                         ↓
                     VALIDATOR
        """,
        language="text",
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### 📚 Curated RAG")
        st.markdown(
            """
            - **Scope**: Stable, curated travel knowledge.
            - **Contents**: Etiquette, cultural customs, heritage monuments, transit etiquette, local tipping norms.
            - **Latency**: 5–25 ms.
            - **Engine**: Supabase PostgreSQL + pgvector (HNSW index).
            - **Updates**: Controlled editorial additions.
            """
        )
    with col2:
        st.markdown("#### ⚡ MCP Operational APIs")
        st.markdown(
            """
            - **Scope**: Structured live operational facts.
            - **Contents**: Flights, hotel room rates, weather forecasts, live foreign exchange conversion.
            - **Latency**: 100–800 ms.
            - **Engine**: Amadeus GDS, Open-Meteo, Frankfurter FX.
            - **Updates**: Real-time operational queries.
            """
        )
    with col3:
        st.markdown("#### 🌐 Fresh Web Search")
        st.markdown(
            """
            - **Scope**: Volatile, time-sensitive intelligence.
            - **Contents**: Seasonal festivals, temporary closures, transport strikes, recent headlines, official visa updates.
            - **Latency**: 400–1200 ms.
            - **Engine**: Search MCP (Tavily / Brave / sandboxed fetch).
            - **Updates**: Fresh web crawl index.
            """
        )

    st.markdown("---")
    st.markdown("### 🛡️ Security Protections & Untrusted Data Boundaries")
    st.markdown(
        """
        1. **SSRF & Private Network Defense**: The Search MCP strictly blocks `localhost`, `127.0.0.1`, RFC 1918 private subnets (`10.x`, `192.168.x`, `172.16.x`), IPv6 loopbacks, and `file://` schemes.
        2. **Prompt Injection Defense**: All fetched web text and search snippets are tagged `untrusted: True`. Untrusted web content cannot alter LangGraph agent states, override system prompts, or invoke privileged tools.
        3. **Bounded Extraction**: HTML downloads are capped at 500KB with 5-second timeouts, stripping scripts, styles, tracking tags, and navigation wrappers.
        4. **Authoritative Verification**: Visa and border entry claims require `OFFICIAL` government or embassy sources. Unverified claims are flagged as incomplete.
        """
    )
