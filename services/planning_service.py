"""Planning service orchestrating LangGraph execution, persistence, and state tracking."""

import time
from typing import Optional, Dict, Any
from graph.state import TravelState, WorkflowStatus, create_initial_state
from graph.workflow import travel_graph
from repositories import (
    trip_repository as default_trip_repo,
    conversation_repository as default_conv_repo,
    message_repository as default_msg_repo,
    agent_run_repository as default_run_repo,
)
from repositories.trip_repository import TripRepository
from repositories.conversation_repository import ConversationRepository
from repositories.message_repository import MessageRepository
from repositories.agent_run_repository import AgentRunRepository
from utils.logger import logger


def run_travel_planning(
    user_request: str,
    user_id: str,
    trip_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    session_state: Optional[Dict[str, Any]] = None,
    trip_repo: Optional[TripRepository] = None,
    conv_repo: Optional[ConversationRepository] = None,
    msg_repo: Optional[MessageRepository] = None,
    run_repo: Optional[AgentRunRepository] = None,
) -> TravelState:
    """Execute LangGraph travel planning workflow with repository integration and observability.

    Args:
        user_request: Natural-language travel request or refinement prompt.
        user_id: Authenticated or demo user identifier.
        trip_id: Optional active trip UUID.
        conversation_id: Optional active conversation UUID.
        session_state: Optional Streamlit session dictionary for real-time UI synchronization.
        trip_repo: Optional injected TripRepository for testing.
        conv_repo: Optional injected ConversationRepository for testing.
        msg_repo: Optional injected MessageRepository for testing.
        run_repo: Optional injected AgentRunRepository for testing.

    Returns:
        Final TravelState after executing LangGraph workflow.
    """
    start_time = time.time()
    t_repo = trip_repo or default_trip_repo
    c_repo = conv_repo or default_conv_repo
    m_repo = msg_repo or default_msg_repo
    r_repo = run_repo or default_run_repo

    logger.info(f"[PlanningService] Starting planning for user {user_id}, trip {trip_id}, conv {conversation_id}")

    # 1. Load existing trip context if available
    existing_trip_data: Optional[Dict[str, Any]] = None
    if trip_id:
        try:
            existing_trip_data = t_repo.get_trip(trip_id=trip_id, user_id=user_id)
        except Exception as e:
            logger.warning(f"[PlanningService] Unable to load trip {trip_id}: {str(e)}")

    # 2. Record incoming user message if conversation exists
    if conversation_id:
        try:
            m_repo.create_message(
                conversation_id=conversation_id,
                role="user",
                content=user_request,
            )
        except Exception as e:
            logger.warning(f"[PlanningService] Failed to persist user message: {str(e)}")

    # 3. Create initial LangGraph state and workflow telemetry tracker
    from services.observability_service import observability_service
    tracker = observability_service.create_workflow_tracker(
        trip_id=trip_id,
        user_id=user_id,
        is_demo=t_repo.is_demo_mode,
    )

    initial_state = create_initial_state(
        original_request=user_request,
        user_id=user_id,
        trip_id=trip_id,
        conversation_id=conversation_id,
        is_demo=t_repo.is_demo_mode,
        existing_trip_data=existing_trip_data,
    )
    initial_state["workflow_telemetry"] = tracker.to_summary_dict()

    # 4. Invoke LangGraph workflow
    try:
        final_state: TravelState = travel_graph.invoke(initial_state)
    except Exception as e:
        logger.error(f"[PlanningService] LangGraph execution error: {str(e)}")
        tracker.record_error(
            error_type=type(e).__name__,
            safe_message=str(e),
            component="travel_graph",
        )
        final_state = dict(initial_state)  # type: ignore
        final_state["planning_status"] = WorkflowStatus.FAILED.value
        final_state["errors"] = [f"LangGraph execution failure: {str(e)}"]

    duration_ms = round((time.time() - start_time) * 1000, 2)

    # Ingest agent runs and model token usage into tracker
    for ar in final_state.get("agent_runs", []):
        agent_name = ar.get("agent_name", "unknown")
        dur = ar.get("duration_ms", 0.0)
        stat = ar.get("status", "SUCCESS")
        meta = ar.get("metadata", {})
        tracker.add_span(
            span_id=ar.get("id") or str(time.time()),
            name=f"Agent: {agent_name}",
            span_type="agent",
            duration_ms=dur,
            status=stat,
            metadata=meta,
            error=ar.get("error_message"),
        )
        tokens = meta.get("total_tokens")
        if tokens:
            tracker.record_model_usage(
                model_name=meta.get("model", "gpt-4o"),
                input_tokens=meta.get("input_tokens", int(tokens * 0.7)),
                output_tokens=meta.get("output_tokens", int(tokens * 0.3)),
            )

    tracker.finish(
        status="SUCCESS" if final_state.get("planning_status") != WorkflowStatus.FAILED.value else "FAILED"
    )
    telemetry_summary = tracker.to_summary_dict()
    telemetry_summary["spans"] = tracker.spans
    telemetry_summary["errors"] = tracker.errors
    telemetry_summary["retry_events"] = tracker.retry_events
    final_state["workflow_telemetry"] = telemetry_summary

    # 5. Persist agent execution run for observability
    if trip_id:
        try:
            run_rec = r_repo.create_agent_run(
                trip_id=trip_id,
                agent_name="planner_orchestrator",
                metadata={
                    "step_name": "phase_4_planner_graph",
                    "original_request": user_request,
                    "graph_steps": final_state.get("graph_step_count"),
                    "execution_time_ms": duration_ms,
                    "workflow_run_id": tracker.workflow_run_id,
                    "total_tokens": tracker.total_tokens,
                },
            )
            r_repo.update_agent_run(
                run_id=run_rec["id"],
                status="SUCCESS" if final_state.get("planning_status") != WorkflowStatus.FAILED.value else "FAILED",
                error_message=final_state.get("errors")[0] if final_state.get("errors") else None,
                metadata={
                    "planning_status": final_state.get("planning_status"),
                    "clarification_required": final_state.get("clarification_required"),
                },
            )
        except Exception as e:
            logger.warning(f"[PlanningService] Failed to record agent run: {str(e)}")

    # 6. Persist assistant reply to conversation
    if conversation_id:
        try:
            if final_state.get("clarification_required"):
                questions = final_state.get("clarification_questions", [])
                assistant_text = "I need a few details before planning:\n\n" + "\n".join(questions)
            elif final_state.get("planning_status") in [
                WorkflowStatus.READY_FOR_ITINERARY.value,
                WorkflowStatus.READY_WITH_WARNINGS.value,
                WorkflowStatus.VALIDATION_FAILED.value,
                WorkflowStatus.READY_FOR_VALIDATION.value,
                WorkflowStatus.SPECIALIZED_AGENTS_COMPLETED.value,
                WorkflowStatus.PARTIAL_RESULTS.value,
                WorkflowStatus.READY_FOR_SPECIALIZED_AGENTS.value,
            ]:
                dest = final_state.get("destination", "your destination")
                orig = final_state.get("origin", "your departure")
                dur = final_state.get("duration")
                curr = final_state.get("currency", "USD")
                bgt = final_state.get("budget")
                budget_str = f"{curr} {bgt:,.2f}" if bgt is not None else "Unspecified"

                flights_count = len(final_state.get("flight_options", []))
                hotels_count = len(final_state.get("hotel_options", []))
                activities_count = len(final_state.get("activities", []))
                has_weather = bool(final_state.get("weather"))
                has_research = bool(final_state.get("research_results"))

                budget_data = final_state.get("budget_breakdown") or {}
                validation_data = final_state.get("validation_results") or {}

                p_status = final_state.get("planning_status")
                if p_status == WorkflowStatus.READY_FOR_ITINERARY.value:
                    status_label = "✅ **Travel Analysis & Validation Verified**"
                elif p_status == WorkflowStatus.READY_WITH_WARNINGS.value:
                    status_label = "⚠️ **Travel Analysis Verified With Warnings**"
                elif p_status == WorkflowStatus.VALIDATION_FAILED.value:
                    status_label = "❌ **Itinerary Validation Failed**"
                else:
                    status_label = "ℹ️ **Specialized Travel Analysis Complete**"

                estimated_cost_str = (
                    f"{curr} {budget_data.get('total_estimated_cost', 0):,.2f} ({budget_data.get('utilization_percentage', 0)}% utilized)"
                    if budget_data
                    else "Calculated on demand"
                )

                val_issues_count = len(validation_data.get("issues", []))
                val_summary_str = (
                    f"{'Passed' if validation_data.get('valid') else 'Failed'} ({len(validation_data.get('errors', []))} error(s), {len(validation_data.get('warnings', []))} warning(s))"
                    if validation_data
                    else "Pending"
                )

                assistant_text = (
                    f"{status_label} (Status: `{p_status}`)\n\n"
                    f"• **Route**: {orig} → {dest} ({dur or 'N/A'} days, {final_state.get('travelers') or 1} traveler(s))\n"
                    f"• **Budget Limit**: {budget_str}\n"
                    f"• **Estimated Total**: {estimated_cost_str}\n"
                    f"• **Validation Status**: {val_summary_str}\n"
                    f"• **Flights Discovered**: {flights_count} option(s) [DEMO_DATA]\n"
                    f"• **Accommodations Found**: {hotels_count} property option(s) [DEMO_DATA]\n"
                    f"• **Experiences Curated**: {activities_count} activities [DEMO_DATA]\n"
                    f"• **Climatological Context**: {'Available' if has_weather else 'Unavailable'}\n"
                    f"• **Destination Intelligence**: {'Compiled' if has_research else 'Unavailable'}\n\n"
                    f"Visit the **Budget**, **Flights**, **Hotels**, **Activities**, **Weather**, and **Agent Trace** pages to inspect detailed deterministic calculations and validation reports."
                )
            elif final_state.get("planning_status") == WorkflowStatus.FAILED.value:
                err_list = final_state.get("errors") or ["Request rejected by safety and validation constraints."]
                from guardrails.security import SecretRedactor
                safe_err = SecretRedactor.redact_text(err_list[0])
                assistant_text = f"❌ **Request Blocked**: {safe_err}"
            else:
                assistant_text = f"Planning status: {final_state.get('planning_status')}."

            from guardrails.security import SecretRedactor
            safe_assistant_text = SecretRedactor.redact_text(assistant_text)

            m_repo.create_message(
                conversation_id=conversation_id,
                role="assistant",
                content=safe_assistant_text,
            )
        except Exception as e:
            logger.warning(f"[PlanningService] Failed to record assistant reply message: {str(e)}")


    # 7. Update session state if provided
    if session_state is not None:
        session_state["travel_state"] = final_state
        session_state["workflow_status"] = final_state.get("planning_status")

    logger.info(
        f"[PlanningService] Planning completed in {duration_ms}ms with status: {final_state.get('planning_status')}"
    )
    return final_state
