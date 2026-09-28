"""LangGraph core state definition for multi-agent travel intelligence platform."""

from enum import Enum
from typing import TypedDict, Optional, List, Dict, Any


class WorkflowStatus(str, Enum):
    """Execution status of the travel planning workflow."""

    INITIALIZING = "INITIALIZING"
    PLANNING = "PLANNING"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    READY_FOR_SPECIALIZED_AGENTS = "READY_FOR_SPECIALIZED_AGENTS"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class TravelState(TypedDict, total=False):
    """Central LangGraph state passed between all reasoning and specialized agents.

    Maintains session context, extracted travel requirements, validation constraints,
    clarification dialogues, future sub-agent deliverables, and observability traces.
    """

    # --- Session & Identity Context ---
    user_id: str
    trip_id: Optional[str]
    conversation_id: Optional[str]
    original_request: str

    # --- Travel Requirements ---
    origin: Optional[str]
    destination: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    duration: Optional[int]
    travelers: Optional[int]
    budget: Optional[float]
    currency: Optional[str]

    # --- Preferences & Constraints ---
    interests: List[str]
    travel_style: Optional[str]
    accommodation_preference: Optional[str]
    food_preferences: List[str]
    constraints: List[str]
    additional_requirements: Optional[str]

    # --- Planning & Clarification State ---
    planning_status: str
    clarification_required: bool
    clarification_questions: List[str]
    planner_result: Optional[Dict[str, Any]]
    warnings: List[str]
    errors: List[str]

    # --- Future-Ready Agent Deliverables (Phases 5-11) ---
    flight_options: List[Dict[str, Any]]
    hotel_options: List[Dict[str, Any]]
    activities: List[Dict[str, Any]]
    weather: Optional[Dict[str, Any]]
    research_results: Optional[Dict[str, Any]]
    budget_breakdown: Optional[Dict[str, Any]]
    itinerary: Optional[Dict[str, Any]]
    validation_results: Optional[Dict[str, Any]]
    sources: List[Dict[str, Any]]

    # --- Observability, Guardrails & Execution Tracing ---
    agent_runs: List[Dict[str, Any]]
    tool_calls: List[Dict[str, Any]]
    retry_count: int
    graph_step_count: int
    is_demo: bool


def create_initial_state(
    original_request: str,
    user_id: str,
    trip_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    is_demo: bool = False,
    existing_trip_data: Optional[Dict[str, Any]] = None,
) -> TravelState:
    """Create a pristine, typed initial TravelState instance."""
    existing_trip = existing_trip_data or {}
    prefs = existing_trip.get("preferences") or {}

    return TravelState(
        user_id=user_id,
        trip_id=trip_id or existing_trip.get("id"),
        conversation_id=conversation_id,
        original_request=original_request,
        origin=existing_trip.get("origin"),
        destination=existing_trip.get("destination"),
        start_date=str(existing_trip["start_date"]) if existing_trip.get("start_date") else None,
        end_date=str(existing_trip["end_date"]) if existing_trip.get("end_date") else None,
        duration=None,
        travelers=int(existing_trip.get("travelers")) if existing_trip.get("travelers") else None,
        budget=float(existing_trip.get("budget")) if existing_trip.get("budget") is not None else None,
        currency=existing_trip.get("currency", "USD"),
        interests=prefs.get("preferences") or [],
        travel_style=prefs.get("travel_style"),
        accommodation_preference=prefs.get("accommodation_preference"),
        food_preferences=[],
        constraints=[],
        additional_requirements=prefs.get("additional_requirements"),
        planning_status=WorkflowStatus.INITIALIZING.value,
        clarification_required=False,
        clarification_questions=[],
        planner_result=None,
        warnings=[],
        errors=[],
        flight_options=[],
        hotel_options=[],
        activities=[],
        weather=None,
        research_results=None,
        budget_breakdown=None,
        itinerary=None,
        validation_results=None,
        sources=[],
        agent_runs=[],
        tool_calls=[],
        retry_count=0,
        graph_step_count=0,
        is_demo=is_demo,
    )
