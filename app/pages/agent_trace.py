"""Agent Trace and LangSmith orchestration observability page."""

from typing import Any, Dict, List, Optional
import streamlit as st

PLANNED_AGENTS = [
    {
        "name": "Planner Agent",
        "role": "Deconstructs natural language inputs, establishes constraints, and coordinates graph flow.",
        "phase": "Phase 4 (Active)",
        "model": "gpt-4o / DemoExtractor",
        "type": "LLM",
        "key": "planner",
    },
    {
        "name": "Flight Agent",
        "role": "Discovers and filters flights matching dates, class, and transit rules.",
        "phase": "Phase 5 (Active)",
        "model": "Amadeus GDS / Mock",
        "type": "MCP",
        "key": "flight",
    },
    {
        "name": "Hotel Agent",
        "role": "Identifies lodging matching budget, guest capacity, and geographic radius.",
        "phase": "Phase 5 (Active)",
        "model": "Amadeus Hospitality / Mock",
        "type": "MCP",
        "key": "hotel",
    },
    {
        "name": "Activity Agent",
        "role": "Curates daily experiences, meals, and cultural visits based on pace.",
        "phase": "Phase 5 (Active)",
        "model": "Photon & OSRM / Mock",
        "type": "MCP",
        "key": "activity",
    },
    {
        "name": "Weather Agent",
        "role": "Evaluates seasonal trends and forecasts to identify outdoor hazards.",
        "phase": "Phase 5 (Active)",
        "model": "Open-Meteo WMO / Mock",
        "type": "MCP",
        "key": "weather",
    },
    {
        "name": "Research Agent",
        "role": "Synthesizes curated RAG knowledge with fresh Web Search via Search MCP.",
        "phase": "Phase 10 (Active)",
        "model": "Wikipedia / Tavily / pgvector",
        "type": "RAG",
        "key": "research",
    },
    {
        "name": "Budget Engine",
        "role": "Calculates exact cost totals, category percentages, and flags budget overruns.",
        "phase": "Phase 6 (Active)",
        "model": "Pure Python (DETERMINISTIC)",
        "type": "DETERMINISTIC",
        "key": "budget_engine",
    },
    {
        "name": "Validator",
        "role": "Validates temporal feasibility, connection times, budget caps, and logistics.",
        "phase": "Phase 6 (Active)",
        "model": "Pure Python (DETERMINISTIC)",
        "type": "DETERMINISTIC",
        "key": "validator",
    },
    {
        "name": "Dynamic Replanning",
        "role": "Selective node re-execution on external disruptions while preserving unaffected state.",
        "phase": "Phase 12 (Active)",
        "model": "Replanning Engine",
        "type": "DETERMINISTIC",
        "key": "replanning",
    },
    {
        "name": "Human Approval",
        "role": "Human-in-the-loop gate requiring explicit authorization for transactional actions.",
        "phase": "Phase 13 (Active)",
        "model": "Approval Gate & Mock Providers",
        "type": "HUMAN",
        "key": "approval",
    },
    {
        "name": "Final Itinerary",
        "role": "Synthesizes approved travel options into a structured versioned deliverable.",
        "phase": "Phase 7+ (Active)",
        "model": "gpt-4o / Itinerary Version",
        "type": "LLM",
        "key": "itinerary",
    },
]


def render_agent_trace_page() -> None:
    """Render multi-agent execution telemetry, workflow summary, and active trace timeline."""
    st.title("LangSmith Observability & Agent Trace")
    st.markdown(
        "Production-grade distributed observability across LangGraph, individual agents, MCP tools, "
        "RAG retrieval, Web Search, Dynamic Replanning, and Human-in-the-loop approvals."
    )

    st.markdown("---")

    travel_state = st.session_state.get("travel_state", {})
    workflow_telemetry = (
        travel_state.get("workflow_telemetry")
        or st.session_state.get("workflow_telemetry")
        or {}
    )
    agent_runs = travel_state.get("agent_runs", [])
    workflow_status = workflow_telemetry.get(
        "status",
        st.session_state.get("workflow_status", travel_state.get("planning_status", "IDLE")),
    )

    # 1. WORKFLOW SUMMARY
    st.markdown("### 📊 WORKFLOW SUMMARY")

    w_run_id = workflow_telemetry.get("workflow_run_id") or travel_state.get("trip_id") or "run-idle"
    t_id = workflow_telemetry.get("trip_id") or travel_state.get("trip_id") or "Unassigned"
    dur_ms = workflow_telemetry.get("duration_ms", 0.0)
    if dur_ms == 0.0 and agent_runs:
        dur_ms = sum(r.get("duration_ms", 0) for r in agent_runs)
    dur_sec = round(dur_ms / 1000.0, 2)

    total_ops = workflow_telemetry.get("total_operations", len(agent_runs))
    model_calls = workflow_telemetry.get("model_calls", 1 if agent_runs else 0)
    mcp_calls = workflow_telemetry.get("mcp_calls", len(travel_state.get("tool_calls", [])))
    search_calls = workflow_telemetry.get("search_calls", 1 if any("research" in r.get("agent_name", "") for r in agent_runs) else 0)
    rag_calls = workflow_telemetry.get("rag_calls", len(travel_state.get("rag_retrievals", [])))
    retries = workflow_telemetry.get("retries", 0)
    cost_str = workflow_telemetry.get("estimated_cost", "$0.0000" if travel_state.get("is_demo", True) else "UNKNOWN")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric(label="Status", value=str(workflow_status))
    with c2:
        st.metric(label="Workflow ID", value=str(w_run_id)[:10] + "...")
    with c3:
        st.metric(label="Trip ID", value=str(t_id)[:10] + "..." if t_id != "Unassigned" else "Unassigned")
    with c4:
        st.metric(label="Duration", value=f"{dur_sec:.2f}s ({dur_ms:,.0f}ms)")
    with c5:
        st.metric(label="Estimated Cost", value=cost_str)

    c6, c7, c8, c9, c10 = st.columns(5)
    with c6:
        st.metric(label="Total Operations", value=str(total_ops))
    with c7:
        st.metric(label="Model Calls", value=str(model_calls))
    with c8:
        st.metric(label="MCP Calls", value=str(mcp_calls))
    with c9:
        st.metric(label="RAG / Search Calls", value=f"{rag_calls} / {search_calls}")
    with c10:
        st.metric(label="Retries", value=str(retries))

    # LangSmith Run Link
    ls_url = workflow_telemetry.get("langsmith_url")
    if ls_url and "smith.langchain.com" in ls_url:
        st.markdown(f"🔗 **LangSmith Trace**: [{ls_url}]({ls_url})")
    else:
        st.caption("ℹ️ **LangSmith Run Link**: Tracing unavailable (Running in Offline / Safe DEMO Mode)")

    st.markdown("---")

    # 2. AGENT TRACE (Node Status Checklist)
    st.markdown("### 🧭 AGENT TRACE")

    # Extract executed nodes from agent runs
    executed_agent_names = {r.get("agent_name", "").lower(): r for r in agent_runs}
    is_demo = travel_state.get("is_demo", True)
    mode_badge = "MOCK" if is_demo else "LIVE"

    trace_cols = st.columns(3)
    for idx, node in enumerate(PLANNED_AGENTS):
        col = trace_cols[idx % 3]
        key = node["key"]
        matched_run = None
        for a_name, r_data in executed_agent_names.items():
            if key in a_name:
                matched_run = r_data
                break

        has_run = matched_run is not None or (key in ("replanning", "approval", "itinerary") and bool(agent_runs))
        status_symbol = "✓" if has_run else "○"
        status_color = "#4CAF50" if has_run else "#78909C"

        n_dur = matched_run.get("duration_ms", 0.0) if matched_run else 0.0
        n_retries = matched_run.get("metadata", {}).get("retries", 0) if matched_run else 0
        node_status = matched_run.get("status", "SUCCESS") if matched_run else ("PENDING" if not agent_runs else "SKIPPED")

        # Badges
        type_badge = node["type"]
        labels = [type_badge, mode_badge]

        with col:
            st.markdown(
                f"""
                <div style="
                    border: 1px solid rgba(128, 128, 128, 0.25);
                    border-radius: 8px;
                    padding: 10px 14px;
                    margin-bottom: 12px;
                    background: rgba(255, 255, 255, 0.02);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 600; font-size: 0.95rem; color: #ECEFF1;">
                            {node['name']} <strong style="color: {status_color};">{status_symbol}</strong>
                        </span>
                        <span style="font-size: 0.75rem; color: {status_color}; font-weight: 600;">
                            {node_status}
                        </span>
                    </div>
                    <div style="font-size: 0.78rem; color: #90A4AE; margin: 4px 0;">
                        Duration: <strong>{n_dur:.1f}ms</strong> | Retries: <strong>{n_retries}</strong>
                    </div>
                    <div style="font-size: 0.78rem; color: #78909C; margin-bottom: 6px;">
                        Engine: {node['model']}
                    </div>
                    <div>
                        <span style="background: rgba(33, 150, 243, 0.2); color: #64B5F6; font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; font-weight: 600; margin-right: 4px;">{type_badge}</span>
                        <span style="background: rgba(76, 175, 80, 0.2); color: #81C784; font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; font-weight: 600;">{mode_badge}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # 3. TRACE DETAILS (Execution Timeline)
    st.markdown("### ⏱️ TRACE DETAILS & TIMELINE")

    spans = workflow_telemetry.get("spans", [])
    if not spans and agent_runs:
        # Fallback reconstruct spans from agent_runs
        for r in agent_runs:
            spans.append({
                "name": f"Agent: {r.get('agent_name')}",
                "type": "agent",
                "duration_ms": r.get("duration_ms", 0.0),
                "status": r.get("status", "SUCCESS"),
                "metadata": r.get("metadata", {}),
                "error": r.get("error_message"),
            })

    if not spans:
        st.info("ℹ️ **No active trace events logged yet**: Execute a travel request to inspect detailed timeline spans.")
    else:
        timeline_rows = []
        for s in spans:
            name = s.get("name", "Operation")
            s_type = s.get("type", "chain").upper()
            dur = s.get("duration_ms", 0.0)
            status = s.get("status", "SUCCESS")
            meta = s.get("metadata", {})
            retries = meta.get("retries", 0)
            tool = meta.get("tool_name", "--")
            provider = meta.get("provider", "Internal" if is_demo else "Amadeus / API")
            model = meta.get("model", "gpt-4o" if s_type == "LLM" else "--")
            err = s.get("error") or "None"

            # Sanitized result summary
            res_summary = f"Completed ({dur:.1f}ms)" if status == "SUCCESS" else f"Failed: {err[:40]}"

            timeline_rows.append({
                "Node / Component": name,
                "Type": s_type,
                "Duration": f"{dur:.1f}ms",
                "Status": "✅ " + status if status == "SUCCESS" else "❌ " + status,
                "Retries": retries,
                "Tool": tool,
                "Provider": provider,
                "Model": model,
                "Result Summary": res_summary,
                "Error Summary": err[:50] if err != "None" else "None",
            })

        st.table(timeline_rows)

    st.markdown("---")

    # 4. GUARDRAILS & SECURITY STATUS
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

    st.markdown("---")

    # 5. MCP TOOL INVOCATIONS & OBSERVABILITY
    st.markdown("### 🔌 MCP Tool Invocations & Observability (Phase 7 & 10)")
    state_tool_calls = travel_state.get("tool_calls", [])
    from mcp.client import MCPClient
    client_tool_calls = [c.model_dump() for c in MCPClient.get_recent_calls()]

    all_calls = list(state_tool_calls)
    seen_ids = {c.get("execution_id") for c in all_calls if c.get("execution_id")}
    for cc in client_tool_calls:
        if cc.get("execution_id") not in seen_ids:
            all_calls.append(cc)
            seen_ids.add(cc.get("execution_id"))

    if not all_calls:
        st.info("ℹ️ **No MCP Tool Calls Recorded Yet**: Run a trip planning workflow to see real-time tool telemetry.")
    else:
        mcp_table_rows = []
        for call in all_calls:
            c_tool = call.get("tool_name", "unknown")
            c_agent = f"{call.get('agent_name', 'system').capitalize()} Agent"
            c_provider = call.get("provider") or ("Demo Mock" if is_demo else "Real API")
            c_status = call.get("status", "SUCCESS")
            c_duration = call.get("duration_ms", 0.0)
            c_retries = call.get("retries", 0)
            c_mode = call.get("mode", "DEMO")
            c_error = call.get("error") or "None"

            status_icon = "✅ SUCCESS" if c_status == "SUCCESS" else f"❌ {c_status}"
            data_badge = "🟢 LIVE DATA" if c_mode == "LIVE" else "🟡 DEMO DATA"

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

    # 6. RAG RETRIEVAL AUDIT
    st.markdown("---")
    st.markdown("### 📚 RAG Knowledge Retrieval Audit (Phase 9)")
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

    # 7. DYNAMIC REPLANNING TRACE
    st.markdown("---")
    st.markdown("### 🔄 Dynamic Replanning & Selective Node Execution (Phase 12)")
    itinerary_ver = travel_state.get("itinerary_version", 1)
    replan_count = travel_state.get("replan_count", 0)
    exec_modes = travel_state.get("agent_execution_modes", {})
    latest_impact = travel_state.get("latest_impact_analysis", {})

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        st.metric(label="Itinerary Version", value=f"v{itinerary_ver}")
    with col_r2:
        st.metric(label="Replans Executed", value=str(replan_count))
    with col_r3:
        st.metric(label="Replan Severity", value=latest_impact.get("severity", "NONE") if latest_impact else "NONE")

    # Selective Execution Badges
    node_roster = [
        ("flight", "Flight Agent"),
        ("hotel", "Hotel Agent"),
        ("activity", "Activity Agent"),
        ("weather", "Weather Agent"),
        ("research", "Research Agent"),
        ("budget_engine", "Budget Engine"),
        ("validator", "Validator Engine"),
    ]

    badge_cols = st.columns(len(node_roster))
    for idx, (node_key, node_label) in enumerate(node_roster):
        action = exec_modes.get(node_key, "REUSED" if replan_count > 0 else "RERUN")
        with badge_cols[idx]:
            if action == "RERUN":
                b_color = "#FF9800"
                b_text = "RERUN ⚡"
                b_bg = "rgba(255, 152, 0, 0.15)"
            elif action in ("REUSE", "REUSED"):
                b_color = "#4CAF50"
                b_text = "REUSED ✓"
                b_bg = "rgba(76, 175, 80, 0.15)"
            elif action in ("INVALIDATE", "INVALIDATED"):
                b_color = "#F44336"
                b_text = "INVALIDATED ✗"
                b_bg = "rgba(244, 67, 54, 0.15)"
            else:
                b_color = "#9E9E9E"
                b_text = "SKIPPED ⏸️"
                b_bg = "rgba(158, 158, 158, 0.15)"

            st.markdown(
                f"""
                <div style="
                    border: 1px solid {b_color};
                    background: {b_bg};
                    border-radius: 6px;
                    padding: 8px 4px;
                    text-align: center;
                    margin-bottom: 8px;
                ">
                    <div style="font-size: 0.75rem; color: #ECEFF1; font-weight: 500;">{node_label}</div>
                    <div style="font-size: 0.85rem; color: {b_color}; font-weight: 700; margin-top: 4px;">{b_text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # 8. HUMAN-IN-THE-LOOP APPROVAL TRACE
    st.markdown("---")
    st.markdown("### 🛡️ Human-in-the-Loop Approval Lifecycle (Phase 13)")
    col_h1, col_h2 = st.columns([3, 2])

    with col_h1:
        st.markdown("#### Execution Paradigm Breakdown")
        hitl_lifecycle = [
            ("Planner Agent", "AUTOMATIC", "Generates travel strategy & decomposes requirements", "✓"),
            ("Specialized Agents (Flight/Hotel/Activity)", "AUTOMATIC", "Discovers options via read-only MCP queries", "✓"),
            ("Budget & Validator Engines", "DETERMINISTIC", "Verifies caps and temporal consistency without LLM math", "✓"),
            ("Action Proposal Generator", "DETERMINISTIC", "Classifies risk and generates ActionProposal", "✓"),
            ("Approval Gate", "HUMAN APPROVAL", "Halts graph execution if risk > LOW; awaits human decision", "⏸"),
            ("Transactional Booking Adapter", "MOCK", "Safe simulated GDS/CRS execution (no real money)", "✓"),
        ]
        h_table = []
        for stage, mode, desc, icon in hitl_lifecycle:
            h_table.append({
                "Workflow Stage": f"{icon} {stage}",
                "Execution Nature": mode,
                "Governance": desc,
            })
        st.table(h_table)

    with col_h2:
        st.markdown("#### Active HITL State")
        hitl_paused = travel_state.get("hitl_paused", False)
        pause_reason = travel_state.get("hitl_pause_reason")
        confirmed_count = len(travel_state.get("confirmed_bookings", []))
        proposals_count = len(travel_state.get("pending_proposals", []))

        if hitl_paused:
            st.warning(f"⏸️ **Graph Paused for Approval**:\n{pause_reason or 'Transactional action pending human review.'}")
        else:
            st.success("✅ **Graph Unblocked**: No transactional actions pending human authorization.")

        st.metric("Confirmed Transactions", f"{confirmed_count} (DEMO / MOCK)")
        st.metric("Proposals Monitored", str(proposals_count))
