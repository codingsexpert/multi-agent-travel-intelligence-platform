"""Deterministic Dynamic Replanning Engine with Dependency Mapping, Selective Re-execution, and Versioning."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from config.settings import get_settings
from models.replanning import (
    ChangeEvent,
    ChangeEventSeverity,
    ChangeEventType,
    ImpactAnalysis,
    ItineraryVersion,
    NodeExecutionAction,
    ReplanningAuditRecord,
)

logger = logging.getLogger("travel_platform.replanning_engine")


class ReplanningEngine:
    """Core deterministic engine for change event impact analysis, dependency resolution, and selective re-execution."""

    # Explicit deterministic dependency graph
    # Node -> Set of downstream nodes that depend on it
    DEPENDENCY_GRAPH: Dict[str, Set[str]] = {
        "flight": {"day_1_schedule", "day_1_activities", "hotel_checkin", "budget_engine"},
        "hotel": {"lodging_location", "transit_routes", "evening_activities", "budget_engine"},
        "weather": {"outdoor_activities", "daily_schedule"},
        "activity": {"daily_schedule", "transit_routes", "budget_engine"},
        "research": {"advisories", "customs_warnings"},
        "budget": {"validator"},
        "budget_engine": {"validator"},
    }

    # Direct mapping from ChangeEventType to primary affected agent / node
    EVENT_NODE_MAPPING: Dict[ChangeEventType, Dict[str, Any]] = {
        ChangeEventType.FLIGHT_CANCELLED: {
            "primary_node": "flight",
            "downstream_reruns": {"flight", "activity", "budget_engine", "validator"},
            "affected_days": [1],
            "budget_item": "FLIGHTS",
            "severity": ChangeEventSeverity.CRITICAL,
        },
        ChangeEventType.FLIGHT_DELAYED: {
            "primary_node": "flight",
            "downstream_reruns": {"flight", "activity", "budget_engine", "validator"},
            "affected_days": [1],
            "budget_item": "FLIGHTS",
            "severity": ChangeEventSeverity.HIGH,
        },
        ChangeEventType.FLIGHT_CHANGED: {
            "primary_node": "flight",
            "downstream_reruns": {"flight", "budget_engine", "validator"},
            "affected_days": [1],
            "budget_item": "FLIGHTS",
            "severity": ChangeEventSeverity.MEDIUM,
        },
        ChangeEventType.HOTEL_UNAVAILABLE: {
            "primary_node": "hotel",
            "downstream_reruns": {"hotel", "activity", "budget_engine", "validator"},
            "affected_days": [],
            "budget_item": "HOTELS",
            "severity": ChangeEventSeverity.HIGH,
        },
        ChangeEventType.HOTEL_PRICE_CHANGED: {
            "primary_node": "hotel",
            "downstream_reruns": {"hotel", "budget_engine", "validator"},
            "affected_days": [],
            "budget_item": "HOTELS",
            "severity": ChangeEventSeverity.MEDIUM,
        },
        ChangeEventType.WEATHER_CHANGED: {
            "primary_node": "activity",
            "downstream_reruns": {"activity", "budget_engine", "validator"},
            "affected_days": [3],
            "budget_item": "ACTIVITIES",
            "severity": ChangeEventSeverity.MEDIUM,
        },
        ChangeEventType.WEATHER_ALERT: {
            "primary_node": "activity",
            "downstream_reruns": {"activity", "budget_engine", "validator"},
            "affected_days": [2, 3],
            "budget_item": "ACTIVITIES",
            "severity": ChangeEventSeverity.HIGH,
        },
        ChangeEventType.ACTIVITY_UNAVAILABLE: {
            "primary_node": "activity",
            "downstream_reruns": {"activity", "budget_engine", "validator"},
            "affected_days": [2],
            "budget_item": "ACTIVITIES",
            "severity": ChangeEventSeverity.MEDIUM,
        },
        ChangeEventType.BUDGET_CHANGED: {
            "primary_node": "budget_engine",
            "downstream_reruns": {"budget_engine", "validator"},
            "affected_days": [],
            "budget_item": "ALL",
            "severity": ChangeEventSeverity.HIGH,
        },
        ChangeEventType.TRIP_DATES_CHANGED: {
            "primary_node": "all_travel",
            "downstream_reruns": {"flight", "hotel", "activity", "weather", "budget_engine", "validator"},
            "affected_days": [],
            "budget_item": "ALL",
            "severity": ChangeEventSeverity.CRITICAL,
        },
        ChangeEventType.TRAVELLER_COUNT_CHANGED: {
            "primary_node": "all_travel",
            "downstream_reruns": {"flight", "hotel", "activity", "budget_engine", "validator"},
            "affected_days": [],
            "budget_item": "ALL",
            "severity": ChangeEventSeverity.HIGH,
        },
        ChangeEventType.PREFERENCE_CHANGED: {
            "primary_node": "activity",
            "downstream_reruns": {"activity", "budget_engine", "validator"},
            "affected_days": [],
            "budget_item": "ACTIVITIES",
            "severity": ChangeEventSeverity.LOW,
        },
        ChangeEventType.DESTINATION_CHANGED: {
            "primary_node": "all_travel",
            "downstream_reruns": {"flight", "hotel", "activity", "weather", "research", "budget_engine", "validator"},
            "affected_days": [],
            "budget_item": "ALL",
            "severity": ChangeEventSeverity.CRITICAL,
        },
        ChangeEventType.EXTERNAL_ADVISORY: {
            "primary_node": "research",
            "downstream_reruns": {"research", "activity", "validator"},
            "affected_days": [],
            "budget_item": "NONE",
            "severity": ChangeEventSeverity.HIGH,
        },
        ChangeEventType.USER_REQUESTED_REPLAN: {
            "primary_node": "planner",
            "downstream_reruns": {"activity", "budget_engine", "validator"},
            "affected_days": [],
            "budget_item": "ALL",
            "severity": ChangeEventSeverity.MEDIUM,
        },
    }

    ALL_WORKFLOW_NODES: List[str] = [
        "flight", "hotel", "activity", "weather", "research", "budget_engine", "validator"
    ]

    @classmethod
    def analyze_impact(
        cls,
        events: List[ChangeEvent],
        current_state: Dict[str, Any],
        processed_event_ids: Optional[Set[str]] = None,
    ) -> ImpactAnalysis:
        """
        Perform deterministic impact analysis across incoming change events.
        Identifies:
        - Deduplication & loop detection
        - Affected components and trip days
        - Minimal set of nodes to rerun
        - Nodes safely reusable
        - Structured human-readable explanation
        """
        settings = get_settings()
        seen_ids = set(processed_event_ids or set())

        # 1. Deduplicate events
        valid_events: List[ChangeEvent] = []
        for ev in events:
            if ev.event_id in seen_ids:
                logger.info(f"[ReplanningEngine] Skipping already processed event: {ev.event_id}")
                continue
            valid_events.append(ev)
            seen_ids.add(ev.event_id)

        if not valid_events:
            return ImpactAnalysis(
                analysis_id=f"imp-{uuid.uuid4().hex[:8]}",
                event_ids=[],
                affected_components=[],
                affected_agents=[],
                affected_days=[],
                affected_activities=[],
                affected_budget_items=[],
                dependencies={},
                rerun_nodes=[],
                reusable_nodes=list(cls.ALL_WORKFLOW_NODES),
                invalidated_nodes=[],
                severity=ChangeEventSeverity.INFO,
                replan_required=False,
                replan_reason="No new or unprocessed change events detected.",
                human_explanation="All trip components are up-to-date. No adjustments required.",
            )

        # 2. Check Loop Protection / Max Events
        if len(valid_events) > settings.max_replan_events:
            logger.warning(f"[ReplanningEngine] Event count ({len(valid_events)}) exceeds max_replan_events ({settings.max_replan_events}). Truncating.")
            valid_events = valid_events[:settings.max_replan_events]

        rerun_set: Set[str] = set()
        affected_components: Set[str] = set()
        affected_days: Set[int] = set()
        affected_budget_items: Set[str] = set()
        dependencies_map: Dict[str, List[str]] = {}
        highest_severity = ChangeEventSeverity.INFO
        reasons: List[str] = []

        severity_rank = {
            ChangeEventSeverity.INFO: 0,
            ChangeEventSeverity.LOW: 1,
            ChangeEventSeverity.MEDIUM: 2,
            ChangeEventSeverity.HIGH: 3,
            ChangeEventSeverity.CRITICAL: 4,
        }

        # 3. Resolve Dependencies per Event
        for ev in valid_events:
            mapping = cls.EVENT_NODE_MAPPING.get(ev.event_type)
            if not mapping:
                # Default fallback for unmapped custom events
                mapping = {
                    "primary_node": "activity",
                    "downstream_reruns": {"activity", "budget_engine", "validator"},
                    "affected_days": [],
                    "budget_item": "ACTIVITIES",
                    "severity": ChangeEventSeverity.MEDIUM,
                }

            # Update highest severity
            if severity_rank[mapping["severity"]] > severity_rank[highest_severity]:
                highest_severity = mapping["severity"]

            # Add reruns
            ev_reruns = set(mapping["downstream_reruns"])
            rerun_set.update(ev_reruns)

            # Record affected days
            ev_days = mapping.get("affected_days") or []
            if ev.metadata and "affected_days" in ev.metadata:
                ev_days = ev.metadata["affected_days"]
            affected_days.update(ev_days)

            # Record budget category
            b_item = mapping.get("budget_item", "ALL")
            if b_item != "NONE":
                affected_budget_items.add(b_item)

            primary_node = mapping.get("primary_node", "system")
            affected_components.add(primary_node)

            # Record dependency link
            dep_key = f"{ev.event_type.value}:{primary_node}"
            dependencies_map[dep_key] = sorted(list(ev_reruns))

            # Build concise reason
            desc = ev.description or ev.event_type.value.replace("_", " ").title()
            reasons.append(desc)

        # Budget and validator always rerun if any cost-bearing component changed
        if any(c in rerun_set for c in ("flight", "hotel", "activity")):
            rerun_set.add("budget_engine")
            rerun_set.add("validator")

        # Determine reusable and invalidated nodes
        rerun_list = [n for n in cls.ALL_WORKFLOW_NODES if n in rerun_set]
        reusable_list = [n for n in cls.ALL_WORKFLOW_NODES if n not in rerun_set]
        invalidated_list = list(rerun_list)

        # 4. Generate Structured Human Explanation
        explanation = cls._generate_human_explanation(valid_events, rerun_list, reusable_list, affected_days)

        return ImpactAnalysis(
            analysis_id=f"imp-{uuid.uuid4().hex[:8]}",
            event_ids=[e.event_id for e in valid_events],
            affected_components=sorted(list(affected_components)),
            affected_agents=[f"{c}_agent" if not c.endswith("_engine") and c != "validator" else c for c in affected_components],
            affected_days=sorted(list(affected_days)),
            affected_activities=[f"Day {d} activity" for d in sorted(list(affected_days))],
            affected_budget_items=sorted(list(affected_budget_items)),
            dependencies=dependencies_map,
            rerun_nodes=rerun_list,
            reusable_nodes=reusable_list,
            invalidated_nodes=invalidated_list,
            severity=highest_severity,
            replan_required=len(rerun_list) > 0,
            replan_reason="; ".join(reasons),
            human_explanation=explanation,
        )

    @classmethod
    def _generate_human_explanation(
        cls,
        events: List[ChangeEvent],
        rerun_nodes: List[str],
        reusable_nodes: List[str],
        affected_days: Set[int],
    ) -> str:
        """Synthesize a clear, truthful explanation derived strictly from structured event facts."""
        event_descriptions = []
        for ev in events:
            if ev.description:
                event_descriptions.append(ev.description)
            elif ev.event_type == ChangeEventType.FLIGHT_CANCELLED:
                event_descriptions.append("Your flight was cancelled by the carrier")
            elif ev.event_type == ChangeEventType.FLIGHT_DELAYED:
                hours = ev.metadata.get("delay_hours", 3)
                event_descriptions.append(f"Your flight was delayed by {hours} hours")
            elif ev.event_type == ChangeEventType.WEATHER_ALERT or ev.event_type == ChangeEventType.WEATHER_CHANGED:
                cond = ev.metadata.get("condition", "inclement weather")
                days_str = f"Day {', '.join(str(d) for d in sorted(list(affected_days)))}" if affected_days else "your trip"
                event_descriptions.append(f"A weather advisory for {cond} was issued for {days_str}")
            elif ev.event_type == ChangeEventType.HOTEL_UNAVAILABLE:
                event_descriptions.append("Your selected accommodation is no longer available")
            elif ev.event_type == ChangeEventType.BUDGET_CHANGED:
                event_descriptions.append("Your travel budget was updated")
            else:
                event_descriptions.append(ev.event_type.value.replace("_", " ").title())

        main_cause = "; ".join(event_descriptions)

        # What reran
        adjustments = []
        if "flight" in rerun_nodes:
            adjustments.append("rescheduled flight options")
        if "hotel" in rerun_nodes:
            adjustments.append("sourced alternative lodging")
        if "activity" in rerun_nodes:
            if affected_days:
                days_label = ", ".join(f"Day {d}" for d in sorted(list(affected_days)))
                adjustments.append(f"replaced outdoor activities on {days_label} with verified alternatives")
            else:
                adjustments.append("adjusted scheduled activities")
        if "budget_engine" in rerun_nodes:
            adjustments.append("recalculated total expenses")

        adj_str = ", ".join(adjustments) if adjustments else "re-verified itinerary details"

        # What remained unchanged
        unchanged = []
        if "hotel" in reusable_nodes:
            unchanged.append("hotel reservations")
        if "flight" in reusable_nodes:
            unchanged.append("flight itinerary")
        if "weather" in reusable_nodes:
            unchanged.append("weather forecast")
        if "research" in reusable_nodes:
            unchanged.append("destination intelligence")

        unchanged_str = f" Your {', '.join(unchanged)} remain unchanged." if unchanged else ""

        return f"{main_cause}. The system automatically {adj_str}.{unchanged_str}"

    @classmethod
    def parse_user_replan_request(cls, prompt: str) -> ChangeEvent:
        """Parse natural language user revision requests into structured ChangeEvent."""
        text = prompt.lower().strip()
        import re

        # Check for flight cancellation
        if ("flight" in text and ("cancel" in text or "cancelled" in text)) or "cancel flight" in text:
            return ChangeEvent(
                event_type=ChangeEventType.FLIGHT_CANCELLED,
                source="USER",
                affected_entity="flight",
                severity=ChangeEventSeverity.CRITICAL,
                description="User reported flight cancellation.",
            )

        # Check for flight delay
        if "flight delay" in text or "delayed" in text:
            m = re.search(r"(\d+)\s*(?:hour|hr)", text)
            hours = int(m.group(1)) if m else 3
            return ChangeEvent(
                event_type=ChangeEventType.FLIGHT_DELAYED,
                source="USER",
                affected_entity="flight",
                severity=ChangeEventSeverity.HIGH,
                metadata={"delay_hours": hours},
                description=f"User reported flight delayed by {hours} hours.",
            )

        # Check for budget change
        if "budget" in text:
            m = re.search(r"(?:to|of|is)?\s*[\$₹€£]?\s*([0-9,]+)", text)
            new_val = None
            if m:
                val_str = m.group(1).replace(",", "")
                try:
                    new_val = float(val_str)
                except ValueError:
                    new_val = None
            return ChangeEvent(
                event_type=ChangeEventType.BUDGET_CHANGED,
                source="USER",
                affected_entity="budget",
                new_value=new_val,
                severity=ChangeEventSeverity.HIGH,
                description=f"User requested budget revision to {new_val}" if new_val else "User requested budget revision.",
            )

        # Check for weather alert / change
        if any(w in text for w in ["rain", "storm", "weather", "typhoon", "snow", "heavy rain"]):
            m = re.search(r"day\s*(\d+)", text)
            affected_days = [int(m.group(1))] if m else [3]
            return ChangeEvent(
                event_type=ChangeEventType.WEATHER_ALERT,
                source="USER",
                affected_entity="weather",
                metadata={"affected_days": affected_days, "condition": "inclement weather"},
                severity=ChangeEventSeverity.HIGH,
                description=f"Weather alert reported for Day {affected_days[0]}.",
            )

        # Check for hotel unavailable
        if any(w in text for w in ["hotel unavailable", "hotel booked", "hotel sold out", "change hotel"]):
            return ChangeEvent(
                event_type=ChangeEventType.HOTEL_UNAVAILABLE,
                source="USER",
                affected_entity="hotel",
                severity=ChangeEventSeverity.HIGH,
                description="User reported hotel unavailability.",
            )

        # Check for hotel price change
        if "hotel price" in text or "hotel rate" in text or "hotel cost" in text:
            return ChangeEvent(
                event_type=ChangeEventType.HOTEL_PRICE_CHANGED,
                source="USER",
                affected_entity="hotel",
                severity=ChangeEventSeverity.MEDIUM,
                description="User reported hotel price change.",
            )

        # Check for trip dates change
        if "date" in text or "extend trip" in text or "days trip" in text:
            return ChangeEvent(
                event_type=ChangeEventType.TRIP_DATES_CHANGED,
                source="USER",
                affected_entity="trip_dates",
                severity=ChangeEventSeverity.CRITICAL,
                description="User requested trip dates change.",
            )

        # Check for traveller count change
        if any(w in text for w in ["traveler", "traveller", "people", "guest", "person"]):
            m = re.search(r"(\d+)\s*(?:traveler|traveller|people|guest|person)", text)
            num = int(m.group(1)) if m else None
            return ChangeEvent(
                event_type=ChangeEventType.TRAVELLER_COUNT_CHANGED,
                source="USER",
                affected_entity="travelers",
                new_value=num,
                severity=ChangeEventSeverity.HIGH,
                description=f"User updated traveller count to {num}." if num else "User updated traveller count.",
            )

        # Check for destination change
        if any(w in text for w in ["move to", "change destination", "destination to"]):
            m = re.search(r"(?:move to|destination to|change destination to)\s+([A-Za-z\s]+)", text)
            dest = m.group(1).strip().title() if m else None
            return ChangeEvent(
                event_type=ChangeEventType.DESTINATION_CHANGED,
                source="USER",
                affected_entity="destination",
                new_value=dest,
                severity=ChangeEventSeverity.CRITICAL,
                description=f"User changed destination to {dest}." if dest else "User changed destination.",
            )

        # Check for preference / activity change
        if any(w in text for w in ["outdoor", "indoor", "activity", "activities", "prefer", "interest"]):
            return ChangeEvent(
                event_type=ChangeEventType.PREFERENCE_CHANGED,
                source="USER",
                affected_entity="activity",
                severity=ChangeEventSeverity.LOW,
                description="User updated activity preferences.",
            )

        # Default fallback
        return ChangeEvent(
            event_type=ChangeEventType.USER_REQUESTED_REPLAN,
            source="USER",
            affected_entity="trip",
            description=prompt,
            severity=ChangeEventSeverity.MEDIUM,
        )

    @classmethod
    def execute_selective_replan(
        cls,
        state: Dict[str, Any],
        impact: ImpactAnalysis,
        flight_generator: Optional[Any] = None,
        hotel_generator: Optional[Any] = None,
        activity_generator: Optional[Any] = None,
        events: Optional[List[ChangeEvent]] = None,
    ) -> Tuple[Dict[str, Any], ItineraryVersion]:
        """
        Execute selective re-execution:
        1. Keep reusable nodes intact
        2. Rerun ONLY affected nodes
        3. Recalculate deterministic budget
        4. Run deterministic validator
        5. Generate new ItineraryVersion
        6. Preserve last_valid_itinerary on failure
        """
        current_version_num = state.get("itinerary_version", 1)
        next_version_num = current_version_num + 1

        # Preserve snapshot of last valid itinerary before modifying
        previous_valid = state.get("last_valid_itinerary")
        if not previous_valid:
            previous_valid = {
                "version": current_version_num,
                "flight_options": list(state.get("flight_options") or []),
                "hotel_options": list(state.get("hotel_options") or []),
                "activities": list(state.get("activities") or []),
                "weather": state.get("weather"),
                "budget_breakdown": state.get("budget_breakdown"),
                "validation_results": state.get("validation_results"),
            }

        actions_map: Dict[str, str] = {}
        for node in cls.ALL_WORKFLOW_NODES:
            if node in impact.rerun_nodes:
                actions_map[node] = NodeExecutionAction.RERUN.value
            else:
                actions_map[node] = NodeExecutionAction.REUSE.value

        updated_state = dict(state)
        updated_state["last_valid_itinerary"] = previous_valid
        updated_state["agent_execution_modes"] = actions_map

        # Apply any direct state mutations from change events
        effective_events = events or []
        for ev in effective_events:
            if ev.event_type == ChangeEventType.BUDGET_CHANGED and ev.new_value is not None:
                updated_state["budget"] = float(ev.new_value)
            elif ev.event_type == ChangeEventType.TRAVELLER_COUNT_CHANGED and ev.new_value is not None:
                updated_state["travelers"] = int(ev.new_value)
            elif ev.event_type == ChangeEventType.DESTINATION_CHANGED and ev.new_value is not None:
                updated_state["destination"] = str(ev.new_value)

        try:
            # 1. Flight selective rerun
            if "flight" in impact.rerun_nodes:
                logger.info("[ReplanningEngine] Selectively re-executing Flight Agent.")
                if flight_generator:
                    updated_state["flight_options"] = flight_generator(updated_state)
                else:
                    from agents.flight_agent import generate_mock_flights
                    orig = updated_state.get("origin") or "SFO"
                    dest = updated_state.get("destination") or "Tokyo"
                    dep = updated_state.get("start_date") or "2026-10-15"
                    opts = generate_mock_flights(
                        origin=orig,
                        destination=dest,
                        start_date=dep,
                        travelers=updated_state.get("travelers", 1) or 1,
                        currency=updated_state.get("currency", "USD"),
                    )
                    # Mark alternative flight
                    if opts:
                        opts[0].flight_number = f"{opts[0].flight_number}-ALT"
                        opts[0].availability_status = "Replan Confirmed"
                    updated_state["flight_options"] = [o.model_dump() for o in opts]

            # 2. Hotel selective rerun
            if "hotel" in impact.rerun_nodes:
                logger.info("[ReplanningEngine] Selectively re-executing Hotel Agent.")
                if hotel_generator:
                    updated_state["hotel_options"] = hotel_generator(updated_state)
                else:
                    from agents.hotel_agent import generate_mock_hotels
                    dest = updated_state.get("destination") or "Tokyo"
                    dur = updated_state.get("duration", 5) or 5
                    h_opts = generate_mock_hotels(
                        destination=dest,
                        duration=dur,
                        travelers=updated_state.get("travelers", 1) or 1,
                        currency=updated_state.get("currency", "USD"),
                    )
                    if h_opts:
                        h_opts[0].name = f"{h_opts[0].name} (Alternative Wing)"
                    updated_state["hotel_options"] = [h.model_dump() for h in h_opts]

            # 3. Activity selective rerun (e.g. replace outdoor with indoor or shift schedule)
            if "activity" in impact.rerun_nodes:
                logger.info("[ReplanningEngine] Selectively re-executing Activity Agent.")
                if activity_generator:
                    updated_state["activities"] = activity_generator(updated_state)
                else:
                    current_acts = list(updated_state.get("activities") or [])
                    if current_acts:
                        # Convert outdoor to indoor or shift day
                        updated_acts = []
                        for act in current_acts:
                            act_copy = dict(act)
                            # If outdoor or in affected days, replace with indoor museum/landmark
                            day_num = act_copy.get("day", 1)
                            if not impact.affected_days or day_num in impact.affected_days:
                                act_copy["name"] = f"Indoor Cultural Experience: {act_copy.get('name', 'Attraction')}"
                                act_copy["description"] = "Weather-protected indoor venue selected during replanning."
                                act_copy["is_indoor"] = True
                            updated_acts.append(act_copy)
                        updated_state["activities"] = updated_acts
                    else:
                        from agents.activity_agent import generate_mock_activities
                        dest = updated_state.get("destination") or "Tokyo"
                        acts = generate_mock_activities(
                            destination=dest,
                            interests=updated_state.get("interests", []),
                            currency=updated_state.get("currency", "USD"),
                        )
                        updated_state["activities"] = [a.model_dump() for a in acts]

            # 4. Budget Engine deterministic re-execution
            if "budget_engine" in impact.rerun_nodes:
                logger.info("[ReplanningEngine] Recomputing deterministic budget.")
                from engines.budget_engine import BudgetEngine
                budget_sum = BudgetEngine.calculate_from_state(updated_state)
                updated_state["budget_breakdown"] = budget_sum.model_dump()

            # 5. Validator deterministic re-execution
            if "validator" in impact.rerun_nodes:
                logger.info("[ReplanningEngine] Re-executing deterministic Validator.")
                from engines.validator_engine import ValidatorEngine
                from models.budget import BudgetSummary
                bs = None
                if updated_state.get("budget_breakdown"):
                    try:
                        bs = BudgetSummary(**updated_state["budget_breakdown"])
                    except Exception:
                        bs = None
                val_res = ValidatorEngine.validate_plan(updated_state, budget_summary=bs)
                updated_state["validation_results"] = val_res.model_dump()
                updated_state["planning_status"] = val_res.status

            # Create new ItineraryVersion
            new_version = ItineraryVersion(
                version=next_version_num,
                change_reason=impact.replan_reason,
                trigger_event_type=impact.event_ids[0] if impact.event_ids else None,
                human_explanation=impact.human_explanation,
                flight_options=updated_state.get("flight_options", []),
                hotel_options=updated_state.get("hotel_options", []),
                activities=updated_state.get("activities", []),
                weather=updated_state.get("weather"),
                research_results=updated_state.get("research_results"),
                budget_breakdown=updated_state.get("budget_breakdown"),
                validation_results=updated_state.get("validation_results"),
                is_valid=updated_state.get("validation_results", {}).get("valid", True),
                warnings=updated_state.get("validation_results", {}).get("warnings", []),
                sources=updated_state.get("sources", []),
                node_execution_actions=actions_map,
            )

            # Append to history and update state version
            history = list(updated_state.get("itinerary_history") or [])
            history.append(new_version.model_dump())
            updated_state["itinerary_history"] = history
            updated_state["itinerary_version"] = next_version_num
            updated_state["latest_impact_analysis"] = impact.model_dump()
            updated_state["replan_count"] = updated_state.get("replan_count", 0) + 1
            reasons = list(updated_state.get("replan_reasons") or [])
            reasons.append(impact.replan_reason)
            updated_state["replan_reasons"] = reasons

            # If validation failed, keep last valid itinerary reference
            if not new_version.is_valid and previous_valid:
                logger.warning("[ReplanningEngine] Replan produced invalid plan. Preserving previous valid itinerary.")

            return updated_state, new_version

        except Exception as e:
            logger.error(f"[ReplanningEngine] Replanning execution failed: {str(e)}. Restoring previous valid state.")
            # Graceful failure fallback: restore last valid itinerary
            fallback_state = dict(state)
            fallback_state["planning_status"] = "REPLAN_FAILED"
            fallback_state["errors"] = [f"Replanning could not be completed ({str(e)}). Your previous valid itinerary is preserved."]
            fallback_state["agent_execution_modes"] = actions_map
            if previous_valid:
                fallback_state["flight_options"] = previous_valid.get("flight_options", [])
                fallback_state["hotel_options"] = previous_valid.get("hotel_options", [])
                fallback_state["activities"] = previous_valid.get("activities", [])
                fallback_state["budget_breakdown"] = previous_valid.get("budget_breakdown")
                fallback_state["validation_results"] = previous_valid.get("validation_results")

            empty_ver = ItineraryVersion(
                version=current_version_num,
                change_reason=f"Failed replan attempt: {str(e)}",
                human_explanation="Replanning could not be completed. Your previous valid itinerary is preserved.",
                is_valid=False,
                warnings=[f"Replanning failed: {str(e)}"],
            )
            return fallback_state, empty_ver
