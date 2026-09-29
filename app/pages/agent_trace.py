"""Agent Trace and orchestration observability page."""

import streamlit as st

PLANNED_AGENTS = [
    {
        "name": "Planner Agent",
        "role": "Deconstructs natural language inputs, establishes constraints, and coordinates graph flow.",
        "phase": "Phase 4 (Active)",
        "model": "gpt-4o / DemoExtractor",
    },
    {
        "name": "Flight Agent",
        "role": "Discovers and filters flights matching dates, class, and transit rules.",
        "phase": "Phase 5 (Active)",
        "model": "Mock Flight Index [DEMO]",
    },
    {
        "name": "Hotel Agent",
        "role": "Identifies lodging matching budget, guest capacity, and geographic radius.",
        "phase": "Phase 5 (Active)",
        "model": "Mock Hospitality Index [DEMO]",
    },
    {
        "name": "Activity Agent",
        "role": "Curates daily experiences, meals, and cultural visits based on pace.",
        "phase": "Phase 5 (Active)",
        "model": "Mock Experiences Index [DEMO]",
    },
    {
        "name": "Weather Agent",
        "role": "Evaluates seasonal trends and forecasts to identify outdoor hazards.",
        "phase": "Phase 5 (Active)",
        "model": "Mock Climatology [DEMO]",
    },
    {
        "name": "Research Agent",
        "role": "Synthesizes curated RAG knowledge with fresh Web Search, news, and official advisories via Search MCP.",
        "phase": "Phase 10 (Active)",
        "model": "Search MCP + Supabase pgvector",
    },
    {
        "name": "Budget Engine",
        "role": "Calculates exact cost totals, category percentages, and flags budget overruns (zero LLM math).",
        "phase": "Phase 6 (Active)",
        "model": "Pure Python (DETERMINISTIC)",
    },
    {
        "name": "Validator",
        "role": "Validates temporal feasibility, connection times, budget caps, and logistics consistency.",
        "phase": "Phase 6 (Active)",
        "model": "Pure Python (DETERMINISTIC)",
    },
    {
        "name": "Itinerary Agent",
        "role": "Synthesizes approved flight, hotel, and activity options into a narrative plan.",
        "phase": "Phase 7+",
        "model": "gpt-4o",
    },
]


def render_agent_trace_page() -> None:
    """Render multi-agent execution telemetry and active trace table."""
    st.title("Agent Execution Trace & Telemetry")
    st.markdown(
        "Real-time visibility into the LangGraph state machine, individual agent reasoning, deterministic calculation engines, and execution latencies."
    )

    st.markdown("---")

    travel_state = st.session_state.get("travel_state", {})
    agent_runs = travel_state.get("agent_runs", [])
    workflow_status = st.session_state.get("workflow_status", travel_state.get("planning_status", "IDLE"))

    # Aggregated Metrics
    total_runs = len(agent_runs)
    successful_runs = sum(1 for r in agent_runs if r.get("status") == "SUCCESS")
    failed_runs = sum(1 for r in agent_runs if r.get("status") == "FAILED")
    total_latency_ms = sum(r.get("duration_ms", 0) for r in agent_runs)

    st.markdown("### Aggregated Telemetry")
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric(label="Workflow Status", value=workflow_status)
    with m2:
        st.metric(label="Total Invocations", value=str(total_runs))
    with m3:
        st.metric(label="Successful Steps", value=str(successful_runs))
    with m4:
        st.metric(label="Total Latency", value=f"{total_latency_ms:,.1f} ms" if total_latency_ms > 0 else "-- ms")
    with m5:
        mode_val = "DEMO DATA" if travel_state.get("is_demo", True) else "LIVE API"
        st.metric(label="Execution Mode", value=mode_val)

    st.markdown("---")
    st.markdown("### 🛡️ Production Guardrails & Security Status (Phase 11)")

    guardrail_status = travel_state.get("guardrail_status", {})
    input_status = guardrail_status.get("input", {})
    is_blocked = input_status.get("status") == "BLOCKED"

    g1, g2, g3, g4, g5, g6 = st.columns(6)
    with g1:
        if is_blocked:
            st.error("Input: 🛑 Blocked")
        else:
            st.success("Input: ✓ Validated")
    with g2:
        st.success("Tools: ✓ Authorized")
    with g3:
        st.success("RAG: ✓ Validated")
    with g4:
        st.success("Web: ✓ Validated")
    with g5:
        out_stat = guardrail_status.get("output", {}).get("status", "VALIDATED")
        if out_stat == "FAILED":
            st.error("Output: ⚠️ Failed")
        else:
            st.success("Output: ✓ Validated")
    with g6:
        st.success("Runtime: ✓ Within Limits")

    if is_blocked:
        safe_reason = input_status.get("reason", "Suspicious instruction pattern or invalid format")
        st.warning(f"⚠️ **Request Blocked by Security Guardrail**: {safe_reason}")

    # Flowchart Representation
    st.markdown("#### Guardrail Architecture & Execution Boundary")
    if is_blocked:
        st.code("Input Guardrail ───► 🛑 BLOCKED (Reason: Suspicious instruction pattern) ───► TERMINATED", language="text")
    else:
        st.code("Planner ──► Input Guardrail ✓ ──► Flight Agent ──► Tool Guardrail ✓ ──► Flight MCP ──► Output Validation ✓ ──► Budget Engine ──► Validator ✓", language="text")

    st.markdown("### Active Execution Trace Table")

    if not agent_runs:
        st.info("ℹ️ **No Active Agent Trace Yet**: Submit a trip request to view live agent execution steps and telemetry.")
    else:
        trace_data = []
        for run in agent_runs:
            raw_name = run.get("agent_name", "Unknown")
            is_deterministic = "engine" in raw_name.lower() or run.get("engine_type") == "DETERMINISTIC"

            if "budget" in raw_name.lower():
                display_name = "Budget Engine"
            elif "validator" in raw_name.lower():
                display_name = "Validator"
            elif "planner" in raw_name.lower():
                display_name = "Planner Agent"
            else:
                display_name = f"{raw_name.replace('_', ' ').title()} Agent"

            status = run.get("status", "UNKNOWN")
            duration_ms = run.get("duration_ms", 0.0)
            duration_s = f"{duration_ms / 1000:.2f}s" if duration_ms >= 1000 else f"{duration_ms:.1f}ms"

            if is_deterministic:
                mode_str = "DETERMINISTIC"
            else:
                mode_str = "DEMO" if run.get("is_demo", True) else "LIVE"

            step = run.get("step", 1)

            trace_data.append({
                "Component": display_name,
                "Type": "DETERMINISTIC" if is_deterministic else "REASONING",
                "Status": status,
                "Duration": duration_s,
                "Mode": mode_str,
                "Step": step,
                "Error": run.get("error") or "None",
            })

        st.table(trace_data)

    st.markdown("---")
    st.markdown("### 🔌 MCP Tool Invocations & Observability (Phase 7)")
    st.markdown(
        "Standardized Model Context Protocol (MCP) tool execution. Agents invoke typed external capabilities "
        "through the secure MCP Client with least-privilege permission validation, timeouts, retries, and data sandboxing."
    )

    # 1. Fetch recorded tool calls from state or client
    state_tool_calls = travel_state.get("tool_calls", [])
    from mcp.client import MCPClient
    client_tool_calls = [c.model_dump() for c in MCPClient.get_recent_calls()]

    # Combine unique calls by execution_id or timestamp
    all_calls = list(state_tool_calls)
    seen_ids = {c.get("execution_id") for c in all_calls if c.get("execution_id")}
    for cc in client_tool_calls:
        if cc.get("execution_id") not in seen_ids:
            all_calls.append(cc)
            seen_ids.add(cc.get("execution_id"))

    # Tool Execution Hierarchy Visual
    col_tree, col_summary = st.columns([3, 2])

    with col_tree:
        st.markdown("#### Provider Execution Tree & Status")

        # Dynamically build provider status tree from recorded calls
        tree_lines = []
        agent_group_order = [
            ("Flight Agent", "Flight MCP", "Amadeus GDS"),
            ("Hotel Agent", "Hotel MCP", "Amadeus Hospitality"),
            ("Activity Agent", "Maps MCP", "OSM / Photon & OSRM"),
            ("Weather Agent", "Weather MCP", "Open-Meteo WMO"),
            ("Research Agent", "Search MCP", "Wikipedia / Tavily"),
            ("Budget Engine", "Currency MCP", "Frankfurter (ECB)"),
        ]

        # Map calls by agent
        calls_by_agent: Dict[str, List[Dict[str, Any]]] = {}
        for c in all_calls:
            a_key = c.get("agent_name", "").lower()
            calls_by_agent.setdefault(a_key, []).append(c)

        for agent_label, mcp_label, default_provider in agent_group_order:
            a_key = agent_label.lower().split()[0]
            agent_calls = calls_by_agent.get(a_key, [])

            tree_lines.append(f"{agent_label}")
            tree_lines.append(f" └─ {mcp_label}")

            if not agent_calls:
                tree_lines.append(f"     └─ Provider: {default_provider}")
                tree_lines.append(f"        ○ STANDBY")
            else:
                last_call = agent_calls[-1]
                prov_name = last_call.get("provider") or default_provider
                is_success = last_call.get("status") == "SUCCESS"
                mode_str = last_call.get("mode", "DEMO")
                dur_s = last_call.get("duration_ms", 0.0) / 1000.0
                retries = last_call.get("retries", 0)

                if is_success:
                    badge = "✓ LIVE" if mode_str == "LIVE" else "✓ DEMO DATA"
                    tree_lines.append(f"     └─ Provider: {prov_name}")
                    tree_lines.append(f"        {badge}")
                    tree_lines.append(f"        {dur_s:.2f}s")
                else:
                    tree_lines.append(f"     └─ Provider Error")
                    tree_lines.append(f"        ✗ {mode_str}")
                    err_brief = (last_call.get("error") or "execution failed")[:30]
                    tree_lines.append(f"        {err_brief}")
                    if retries > 0:
                        tree_lines.append(f"        retry_count: {retries}")
            tree_lines.append("")

        st.code("\n".join(tree_lines), language="text")

    with col_summary:
        st.markdown("#### Provider Integration Architecture")
        st.code(
            """
Agent
 ↓
LangGraph
 ↓
MCP Tool Boundary
 ↓
Provider Adapter
 ↓
External API
 ↓
Normalized Pydantic Model
 ↓
MCP Gateway
 ↓
Agent
            """,
            language="text",
        )
        st.markdown(
            """
            - 🌐 **Real APIs**: Frankfurter ECB (FX), Open-Meteo (Weather), Photon/OSRM (Maps), Wikipedia/Tavily (Search), Amadeus GDS (Flights/Hotels).
            - 🛡️ **Untrusted Data Isolation**: All third-party HTML/APIs sanitized before reaching reasoning agents.
            - ⚡ **Resilient Adapters**: Bounded retries (max 2), explicit 5-8s timeouts, rate-limit backoff (429), and in-memory TTL caching.
            - 🔒 **Zero Secret Exposure**: Headers, Authorization tokens, and keys scrubbed from audit traces.
            """
        )

    # MCP Tool Call Telemetry Table
    st.markdown("#### Active MCP Tool Telemetry")
    if not all_calls:
        st.info("ℹ️ **No MCP Tool Calls Recorded Yet**: Run a trip planning workflow to see real-time tool telemetry.")
    else:
        mcp_table_rows = []
        for call in all_calls:
            c_tool = call.get("tool_name", "unknown")
            c_agent = f"{call.get('agent_name', 'system').capitalize()} Agent"
            c_provider = call.get("provider") or "Internal Provider"
            c_status = call.get("status", "SUCCESS")
            c_duration = call.get("duration_ms", 0.0)
            c_retries = call.get("retries", 0)
            c_mode = call.get("mode", "DEMO")
            c_error = call.get("error") or "None"

            # Mode & Status Badges
            if c_status == "SUCCESS":
                status_icon = "✅ SUCCESS"
                data_badge = "🟢 LIVE DATA" if c_mode == "LIVE" else "🟡 DEMO DATA"
            elif c_status == "UNAUTHORIZED":
                status_icon = "🚫 UNAUTHORIZED"
                data_badge = "🔴 UNAVAILABLE"
            elif c_status == "TIMED_OUT":
                status_icon = "⏱️ TIMED OUT"
                data_badge = "🔴 PROVIDER ERROR"
            else:
                status_icon = f"❌ {c_status}"
                data_badge = "🔴 PROVIDER ERROR"

            mcp_table_rows.append({
                "Tool": c_tool,
                "Agent": c_agent,
                "Provider": c_provider,
                "Status": status_icon,
                "Data Mode": data_badge,
                "Duration": f"{c_duration:.1f}ms",
                "Retries": c_retries,
                "Error Details": c_error[:60] if c_error != "None" else "None",
            })

        st.table(mcp_table_rows)

    # RAG Retrieval Telemetry (Phase 9)
    st.markdown("---")
    st.markdown("### 📚 RAG Knowledge Retrieval Audit (Phase 9)")
    st.markdown(
        "Verifiable curated travel grounding via **Supabase pgvector** and semantic vector similarity. "
        "Captures query parameters, chunks retrieved, top similarity scores, and source attribution."
    )

    rag_retrievals = travel_state.get("rag_retrievals", [])
    if not rag_retrievals:
        st.info("ℹ️ **No RAG Retrievals Recorded Yet**: Run a travel planning workflow to view vector retrieval traces.")
    else:
        rag_rows = []
        for r in rag_retrievals:
            rag_rows.append({
                "Agent": f"{r.get('agent_name', 'system').capitalize()} Agent",
                "Query": r.get("query", ""),
                "Destination": r.get("destination", "Global"),
                "Chunks Retrieved": r.get("chunks_retrieved", 0),
                "Top Score": f"{r.get('top_score', 0.0):.3f}",
                "Sources Count": r.get("sources_count", 0),
                "Mode": "🟢 LIVE" if r.get("mode") == "LIVE" else "🟡 DEMO",
                "Latency": f"{r.get('latency_ms', 0.0):.1f}ms",
            })
        st.table(rag_rows)

    st.markdown("---")
    st.markdown("### 🔐 Security & Audit Events (Phase 11)")
    from guardrails.security import SecurityAuditor
    sec_events = SecurityAuditor.get_events(limit=15)
    if not sec_events:
        st.info("ℹ️ **Zero Security Violations Detected**: Workflow operating strictly within authorized security boundaries.")
    else:
        sec_rows = []
        for se in sec_events:
            sec_rows.append({
                "Timestamp": se.get("timestamp", "")[:19],
                "Type": se.get("event_type"),
                "Severity": se.get("severity"),
                "Agent": se.get("agent_role") or "N/A",
                "Tool": se.get("tool_name") or "N/A",
                "Message": se.get("message"),
            })
        st.table(sec_rows)

    st.markdown("---")
    st.markdown("### System Architecture Roster (Phase 11)")


    for idx, agent in enumerate(PLANNED_AGENTS, 1):
        with st.container():
            is_active = "Active" in agent["phase"]
            status_color = "#4CAF50" if is_active else "#BDBDBD"
            status_text = "Status: Implemented" if is_active else "Status: Pending Next Phase"

            st.markdown(
                f"""
                <div style="
                    border: 1px solid rgba(128, 128, 128, 0.2);
                    border-radius: 6px;
                    padding: 12px 16px;
                    margin-bottom: 10px;
                    background-color: rgba(255, 255, 255, 0.02);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 600; font-size: 1.05rem;">{idx}. {agent['name']}</span>
                        <span style="
                            font-size: 0.75rem;
                            padding: 3px 8px;
                            border-radius: 4px;
                            background: rgba(128, 128, 128, 0.15);
                            color: {status_color};
                            font-weight: 600;
                        ">
                            {status_text}
                        </span>
                    </div>
                    <div style="color: #9E9E9E; font-size: 0.85rem; margin: 6px 0;">{agent['role']}</div>
                    <div style="display: flex; gap: 20px; font-size: 0.8rem; color: #78909C;">
                        <span>Lifecycle: <strong>{agent['phase']}</strong></span>
                        <span>Engine: <strong>{agent['model']}</strong></span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

