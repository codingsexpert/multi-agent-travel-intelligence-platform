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
        "role": "Synthesizes destination etiquette, tips, and customs into shared state.",
        "phase": "Phase 5 (Active)",
        "model": "Mock Knowledge Graph [DEMO]",
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
    st.markdown("### System Architecture Roster (Phase 6)")

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
