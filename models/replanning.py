"""Pydantic schemas and enums for Dynamic Replanning, Change Events, Impact Analysis, and Itinerary Versioning."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChangeEventType(str, Enum):
    """Categorical classification of dynamic disruptions, updates, or user change events."""

    FLIGHT_CANCELLED = "FLIGHT_CANCELLED"
    FLIGHT_DELAYED = "FLIGHT_DELAYED"
    FLIGHT_CHANGED = "FLIGHT_CHANGED"
    HOTEL_UNAVAILABLE = "HOTEL_UNAVAILABLE"
    HOTEL_PRICE_CHANGED = "HOTEL_PRICE_CHANGED"
    WEATHER_CHANGED = "WEATHER_CHANGED"
    WEATHER_ALERT = "WEATHER_ALERT"
    ACTIVITY_UNAVAILABLE = "ACTIVITY_UNAVAILABLE"
    BUDGET_CHANGED = "BUDGET_CHANGED"
    TRIP_DATES_CHANGED = "TRIP_DATES_CHANGED"
    TRAVELLER_COUNT_CHANGED = "TRAVELLER_COUNT_CHANGED"
    PREFERENCE_CHANGED = "PREFERENCE_CHANGED"
    DESTINATION_CHANGED = "DESTINATION_CHANGED"
    EXTERNAL_ADVISORY = "EXTERNAL_ADVISORY"
    USER_REQUESTED_REPLAN = "USER_REQUESTED_REPLAN"


class ChangeEventSeverity(str, Enum):
    """Severity classification indicating the urgency and scope of impact."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NodeExecutionAction(str, Enum):
    """Execution status for each workflow node in a selective replanning run."""

    RERUN = "RERUN"
    REUSE = "REUSE"
    INVALIDATE = "INVALIDATE"
    SKIP = "SKIP"


class ChangeEvent(BaseModel):
    """Structured event capturing a real-world change, disruption, or user revision."""

    event_id: str = Field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:8]}", description="Unique change event identifier")
    event_type: ChangeEventType = Field(..., description="Classification of the change event")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp of event creation",
    )
    source: str = Field(default="SYSTEM", description="Origin of event: USER, AIRLINE_PROVIDER, WEATHER_ALERT, HOTEL_SYSTEM, ADVISORY")
    affected_entity: Optional[str] = Field(default=None, description="Target entity ID or component (e.g. flight, hotel, activity:1, budget, dates)")
    old_value: Optional[Any] = Field(default=None, description="Previous recorded state or value before the change")
    new_value: Optional[Any] = Field(default=None, description="Updated state or value triggering the change")
    severity: ChangeEventSeverity = Field(default=ChangeEventSeverity.MEDIUM, description="Urgency of the disruption")
    description: Optional[str] = Field(default=None, description="Human-readable description of what changed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary domain metadata (delays in hours, alternative flight IDs, etc.)")


class ImpactAnalysis(BaseModel):
    """Deterministic assessment of which components and agents are affected by change events."""

    analysis_id: str = Field(default_factory=lambda: f"imp-{uuid.uuid4().hex[:8]}", description="Unique impact analysis identifier")
    event_ids: List[str] = Field(default_factory=list, description="IDs of change events analyzed")
    affected_components: List[str] = Field(default_factory=list, description="Components marked as affected (flight, hotel, activity, budget, validator)")
    affected_agents: List[str] = Field(default_factory=list, description="Names of agents whose reasoning must update")
    affected_days: List[int] = Field(default_factory=list, description="Trip days whose scheduled activities are affected")
    affected_activities: List[str] = Field(default_factory=list, description="Specific activity IDs or names requiring replacement or reschedule")
    affected_budget_items: List[str] = Field(default_factory=list, description="Budget item categories affected (e.g. FLIGHTS, HOTELS, ACTIVITIES)")
    dependencies: Dict[str, List[str]] = Field(default_factory=dict, description="Explicit dependency mapping explaining why downstream items are affected")
    rerun_nodes: List[str] = Field(default_factory=list, description="Nodes that MUST selectively re-execute in LangGraph")
    reusable_nodes: List[str] = Field(default_factory=list, description="Nodes whose previous results are preserved intact")
    invalidated_nodes: List[str] = Field(default_factory=list, description="Nodes whose previous deliverables are discarded")
    severity: ChangeEventSeverity = Field(default=ChangeEventSeverity.MEDIUM, description="Highest severity among analyzed events")
    replan_required: bool = Field(default=True, description="Whether workflow re-execution is needed")
    replan_reason: str = Field(default="", description="Structured summary reason for the replan")
    human_explanation: str = Field(default="", description="Clear, non-technical explanation of what changed and what was adjusted")


class ItineraryVersion(BaseModel):
    """Immutable snapshot of a trip plan version resulting from initial creation or dynamic replanning."""

    version: int = Field(default=1, description="Logical version sequence number (1, 2, 3...)")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 creation timestamp",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 update timestamp",
    )
    change_reason: Optional[str] = Field(default=None, description="Concise explanation for why this version was generated")
    trigger_event_type: Optional[str] = Field(default=None, description="Event type that triggered this revision, if any")
    human_explanation: Optional[str] = Field(default=None, description="Friendly summary of changes made in this version")
    flight_options: List[Dict[str, Any]] = Field(default_factory=list, description="Flight options for this version")
    hotel_options: List[Dict[str, Any]] = Field(default_factory=list, description="Hotel options for this version")
    activities: List[Dict[str, Any]] = Field(default_factory=list, description="Activities for this version")
    weather: Optional[Dict[str, Any]] = Field(default=None, description="Weather intelligence for this version")
    research_results: Optional[Dict[str, Any]] = Field(default=None, description="Destination research findings")
    budget_breakdown: Optional[Dict[str, Any]] = Field(default=None, description="Itemized budget breakdown")
    validation_results: Optional[Dict[str, Any]] = Field(default=None, description="Feasibility and constraint validation results")
    is_valid: bool = Field(default=True, description="Whether this version passed deterministic validation")
    warnings: List[Any] = Field(default_factory=list, description="Non-fatal warnings or advisories")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Attributed citations and providers")
    node_execution_actions: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of node names to execution action taken (RERUN, REUSE, INVALIDATE, SKIP)",
    )


class ReplanningAuditRecord(BaseModel):
    """Persistent audit log entity recording a dynamic replanning transaction."""

    id: str = Field(default_factory=lambda: f"rpl-{uuid.uuid4().hex[:8]}", description="Unique audit record UUID")
    trip_id: str = Field(..., description="ID of the trip being replanned")
    event_type: str = Field(..., description="The triggering change event type")
    event_payload: Dict[str, Any] = Field(default_factory=dict, description="Serialized ChangeEvent data")
    impact_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of affected components and rerun nodes")
    previous_itinerary_version: int = Field(default=1, description="Version number before replanning")
    new_itinerary_version: int = Field(default=2, description="Version number after replanning")
    human_explanation: Optional[str] = Field(default=None, description="Human-readable explanation of adjustments")
    status: str = Field(default="COMPLETED", description="Status of replan (COMPLETED, FAILED, PRESERVED_PREVIOUS)")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp of replan completion",
    )
