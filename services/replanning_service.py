"""Replanning service orchestrating dynamic impact analysis, guardrails, selective execution, and audit logging."""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from config.settings import get_settings
from engines.replanning_engine import ReplanningEngine
from guardrails.input import InputGuardrail
from models.replanning import (
    ChangeEvent,
    ChangeEventSeverity,
    ChangeEventType,
    ImpactAnalysis,
    ItineraryVersion,
    ReplanningAuditRecord,
)
from repositories.replanning_repository import ReplanningRepository, replanning_repository
from repositories.trip_repository import TripRepository, trip_repository
from utils.exceptions import ServiceError

logger = logging.getLogger("travel_platform.replanning_service")


class ReplanningService:
    """Service managing dynamic replanning workflows, security boundary checks, and audit trails."""

    def __init__(
        self,
        replan_repo: Optional[ReplanningRepository] = None,
        t_repo: Optional[TripRepository] = None,
    ):
        self.replan_repo = replan_repo or replanning_repository
        self.trip_repo = t_repo or trip_repository
        self.settings = get_settings()

    def trigger_dynamic_replan(
        self,
        change_event: Union[ChangeEvent, Dict[str, Any]],
        current_state: Dict[str, Any],
        user_id: str,
        trip_id: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], ItineraryVersion, ImpactAnalysis]:
        """Process a single ChangeEvent, run impact analysis, selectively re-execute affected nodes, and persist audit logs."""
        return self.handle_batch_change_events(
            events=[change_event],
            current_state=current_state,
            user_id=user_id,
            trip_id=trip_id,
        )

    def handle_batch_change_events(
        self,
        events: List[Union[ChangeEvent, Dict[str, Any]]],
        current_state: Dict[str, Any],
        user_id: str,
        trip_id: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], ItineraryVersion, ImpactAnalysis]:
        """
        Process multiple concurrent change events simultaneously:
        1. Validate inputs and security boundaries
        2. Deduplicate events
        3. Prevent infinite replanning loops
        4. Calculate minimal affected node set
        5. Execute selective re-execution
        6. Persist audit records
        """
        effective_trip_id = trip_id or current_state.get("trip_id") or "mock-trip-123"

        # 1. Parse and sanitize incoming events
        parsed_events: List[ChangeEvent] = []
        for raw_ev in events:
            if isinstance(raw_ev, dict):
                ev = ChangeEvent(**raw_ev)
            else:
                ev = raw_ev

            # Security Guardrail on event text / description
            if ev.description:
                guard_res = InputGuardrail.validate_text(ev.description)
                if not guard_res.allowed:
                    logger.warning(f"[ReplanningService] Change event blocked by input guardrail: {guard_res.reason}")
                    # Return preserved previous state with error
                    current_ver = current_state.get("itinerary_version", 1)
                    fallback_ver = ItineraryVersion(
                        version=current_ver,
                        change_reason=f"Security guardrail rejected change event: {guard_res.reason}",
                        human_explanation="Change request was rejected by security guardrails. Your existing itinerary is preserved.",
                        is_valid=False,
                        warnings=[guard_res.reason or "Untrusted change event input."],
                    )
                    impact = ImpactAnalysis(
                        affected_components=[],
                        rerun_nodes=[],
                        reusable_nodes=list(ReplanningEngine.ALL_WORKFLOW_NODES),
                        replan_required=False,
                        human_explanation="No changes made due to security violation.",
                    )
                    return current_state, fallback_ver, impact

            parsed_events.append(ev)

        # 2. Check Trip Authorization / Tenant Isolation (RLS check in live mode)
        is_demo = current_state.get("is_demo", False) or self.settings.demo_mode
        if trip_id and not is_demo:
            try:
                trip = self.trip_repo.get_trip(trip_id=trip_id, user_id=user_id)
                if not trip:
                    raise ServiceError("ReplanningService", f"Trip {trip_id} not found or unauthorized for user {user_id}")
            except Exception as e:
                logger.error(f"[ReplanningService] Trip verification failed: {str(e)}")
                raise ServiceError("ReplanningService", f"Authorization failed for trip {trip_id}") from e

        # 3. Check Replanning Loop Protection / Max Depth
        current_replan_count = current_state.get("replan_count", 0)
        if current_replan_count >= self.settings.max_replan_depth:
            logger.warning(
                f"[ReplanningService] Replan loop detected! Depth ({current_replan_count}) >= MAX_REPLAN_DEPTH ({self.settings.max_replan_depth}). Aborting."
            )
            current_ver = current_state.get("itinerary_version", 1)
            prev_valid = current_state.get("last_valid_itinerary")
            loop_ver = ItineraryVersion(
                version=current_ver,
                change_reason=f"Max replanning depth ({self.settings.max_replan_depth}) reached. Loop protection engaged.",
                human_explanation="Maximum replan limit reached. Your last valid itinerary has been safely preserved.",
                is_valid=True,
                warnings=[f"Replanning cycle halted by loop protection (depth {current_replan_count})."],
            )
            impact = ImpactAnalysis(
                affected_components=[],
                rerun_nodes=[],
                reusable_nodes=list(ReplanningEngine.ALL_WORKFLOW_NODES),
                replan_required=False,
                replan_reason="Max replan depth reached.",
                human_explanation="Loop protection engaged; previous itinerary preserved.",
            )
            return current_state, loop_ver, impact

        # 4. Perform Deterministic Impact Analysis
        processed_ids = set(current_state.get("processed_event_ids") or [])
        impact = ReplanningEngine.analyze_impact(
            events=parsed_events,
            current_state=current_state,
            processed_event_ids=processed_ids,
        )

        if not impact.replan_required:
            logger.info("[ReplanningService] Impact analysis determined no replan is required.")
            curr_ver_num = current_state.get("itinerary_version", 1)
            noop_ver = ItineraryVersion(
                version=curr_ver_num,
                change_reason="No adjustments required",
                human_explanation=impact.human_explanation,
                is_valid=True,
            )
            return current_state, noop_ver, impact

        # 5. Execute Selective Re-execution
        logger.info(
            f"[ReplanningService] Executing selective replan. Rerunning nodes: {impact.rerun_nodes}, Reusing nodes: {impact.reusable_nodes}"
        )
        updated_state, new_version = ReplanningEngine.execute_selective_replan(
            state=current_state,
            impact=impact,
            events=parsed_events,
        )

        # Update processed event tracking in state
        updated_state["processed_event_ids"] = list(processed_ids.union(impact.event_ids))

        # 5b. State-version Protection: Invalidate stale action proposals for this trip
        previous_version = current_state.get("itinerary_version", 1)
        if new_version.version > previous_version:
            try:
                from services.approval_service import approval_service
                approval_service.invalidate_proposals_for_trip(
                    trip_id=effective_trip_id,
                    new_state_version=new_version.version,
                    reason=f"Dynamic replan to v{new_version.version}: {new_version.change_reason}",
                )
            except Exception as e:
                logger.error(f"[ReplanningService] Failed to invalidate stale proposals: {str(e)}")

        # 6. Record Immutable Audit Trail
        audit_record = ReplanningAuditRecord(
            trip_id=effective_trip_id,
            event_type=parsed_events[0].event_type.value if parsed_events else "BATCH_EVENTS",
            event_payload={
                "events": [e.model_dump() for e in parsed_events],
            },
            impact_summary=impact.model_dump(),
            previous_itinerary_version=current_state.get("itinerary_version", 1),
            new_itinerary_version=new_version.version,
            human_explanation=new_version.human_explanation,
            status="COMPLETED" if new_version.is_valid else "FAILED_PRESERVED_PREVIOUS",
        )
        try:
            self.replan_repo.record_replanning_event(audit_record)
        except Exception as e:
            logger.error(f"[ReplanningService] Failed to record audit log: {str(e)}")

        return updated_state, new_version, impact

    def handle_user_replan_request(
        self,
        prompt: str,
        current_state: Dict[str, Any],
        user_id: str,
        trip_id: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], ItineraryVersion, ImpactAnalysis]:
        """Convert natural language prompt into structured ChangeEvent and trigger dynamic replan."""
        # Validate prompt through InputGuardrail
        guard_res = InputGuardrail.validate_text(prompt)
        if not guard_res.allowed:
            logger.warning(f"[ReplanningService] User prompt blocked by guardrail: {guard_res.reason}")
            current_ver = current_state.get("itinerary_version", 1)
            fallback_ver = ItineraryVersion(
                version=current_ver,
                change_reason=f"Security rejection: {guard_res.reason}",
                human_explanation="Your request was blocked by security guardrails. Existing itinerary preserved.",
                is_valid=False,
                warnings=[guard_res.reason or "Security validation failed."],
            )
            impact = ImpactAnalysis(
                affected_components=[],
                rerun_nodes=[],
                reusable_nodes=list(ReplanningEngine.ALL_WORKFLOW_NODES),
                replan_required=False,
                human_explanation="No adjustments made.",
            )
            return current_state, fallback_ver, impact

        # Deterministic parsing to ChangeEvent
        change_event = ReplanningEngine.parse_user_replan_request(prompt)
        logger.info(f"[ReplanningService] Parsed prompt into ChangeEvent type: {change_event.event_type.value}")

        return self.trigger_dynamic_replan(
            change_event=change_event,
            current_state=current_state,
            user_id=user_id,
            trip_id=trip_id,
        )

    def run_graph_replan(
        self,
        events: List[Union[ChangeEvent, Dict[str, Any]]],
        current_state: Dict[str, Any],
        trip_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run replanning directly through LangGraph replanning_graph."""
        from graph.workflow import replanning_graph
        state_copy = dict(current_state)
        state_copy["pending_change_events"] = [
            e.model_dump() if isinstance(e, ChangeEvent) else e for e in events
        ]
        res = replanning_graph.invoke(state_copy)

        effective_trip_id = trip_id or current_state.get("trip_id") or "mock-trip-123"
        impact_dict = res.get("latest_impact_analysis") or {}
        audit_record = ReplanningAuditRecord(
            trip_id=effective_trip_id,
            event_type="GRAPH_DYNAMIC_REPLAN",
            event_payload={"events": state_copy["pending_change_events"]},
            impact_summary=impact_dict,
            previous_itinerary_version=current_state.get("itinerary_version", 1),
            new_itinerary_version=res.get("itinerary_version", 2),
            human_explanation=impact_dict.get("human_explanation"),
            status="COMPLETED",
        )
        try:
            self.replan_repo.record_replanning_event(audit_record)
        except Exception as e:
            logger.error(f"[ReplanningService] Failed to record audit log: {str(e)}")

        return res


# Default singleton instance
replanning_service = ReplanningService()
