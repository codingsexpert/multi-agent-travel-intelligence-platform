"""Agent Trace and orchestration observability page."""

import streamlit as st

PLANNED_AGENTS = [
    {
        "name": "Planner Agent",
        "role": "Deconstructs natural language inputs, establishes constraints, and coordinates graph flow.",
        "phase": "Phase 4",
        "model": "gpt-4o",
    },
    {
        "name": "Flight Agent",
        "role": "Searches, filters, and selects flights matching dates, class, and transit rules.",
        "phase": "Phase 5",
        "model": "gpt-4o-mini",
    },
    {
        "name": "Hotel Agent",
        "role": "Identifies lodging matching budget, guest capacity, and geographic radius.",
        "phase": "Phase 5",
        "model": "gpt-4o-mini",
    },
    {
        "name": "Activity Agent",
        "role": "Curates daily experiences, meals, and cultural visits based on pace.",
        "phase": "Phase 5",
        "model": "gpt-4o-mini",
    },
    {
        "name": "Weather Agent",
        "role": "Evaluates seasonal trends and forecasts to identify outdoor hazards.",
        "phase": "Phase 5",
        "model": "gpt-4o-mini",
    },
    {
        "name": "Research Agent",
        "role": "Retrieves visa rules, local customs, and public transit guidelines via RAG & search.",
        "phase": "Phase 9 & 10",
        "model": "gpt-4o-mini",
    },
    {
        "name": "Budget Agent",
        "role": "Calculates exact cost totals, category percentages, and flags budget overruns.",
        "phase": "Phase 6",
        "model": "Pure Python",
    },
    {
        "name": "Validator Agent",
        "role": "Validates temporal feasibility, connection times, and fatigue indices.",
        "phase": "Phase 6",
        "model": "Pure Python",
    },
    {
        "name": "Itinerary Agent",
        "role": "Synthesizes approved flight, hotel, and activity options into a narrative plan.",
        "phase": "Phase 6",
        "model": "gpt-4o",
    },
]


def render_agent_trace_page() -> None:
    """Render future-ready multi-agent execution and observability trace page."""
    st.title("Agent Execution Trace & Telemetry")
    st.markdown(
        "Real-time visibility into the LangGraph state machine, individual agent reasoning, tool invocations, token costs, and execution latencies."
    )

    st.markdown("---")

    # Metrics Summary Row (Placeholders)
    st.markdown("### Aggregated Telemetry")
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric(label="Active Workflow", value=st.session_state.get("workflow_status", "IDLE"))
    with m2:
        st.metric(label="Execution Time", value="-- ms")
    with m3:
        st.metric(label="Tool Invocations", value="0")
    with m4:
        st.metric(label="Tokens Consumed", value="0")
    with m5:
        st.metric(label="Estimated Cost", value="$0.000")

    st.info(
        "ℹ️ **Trace Status**: All agents currently have status **Not started**. Live step-by-step tracing, tool calls, retry counters, and LangSmith spans will be connected in Phase 4 & Phase 14."
    )

    st.markdown("---")
    st.markdown("### Planned Agents Roster (9 Agents)")

    for idx, agent in enumerate(PLANNED_AGENTS, 1):
        with st.container():
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
                            background: rgba(158, 158, 158, 0.2);
                            color: #BDBDBD;
                        ">
                            Status: Not started
                        </span>
                    </div>
                    <div style="color: #9E9E9E; font-size: 0.85rem; margin: 6px 0;">{agent['role']}</div>
                    <div style="display: flex; gap: 20px; font-size: 0.8rem; color: #78909C;">
                        <span>Target Phase: <strong>{agent['phase']}</strong></span>
                        <span>Engine: <strong>{agent['model']}</strong></span>
                        <span>Tool Calls: <strong>0</strong></span>
                        <span>Retries: <strong>0</strong></span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
