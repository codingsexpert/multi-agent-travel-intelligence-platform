"""Integration-style tests for planning service and persistence layers."""

from config.settings import Settings
from repositories.mock_store import MockDataStore
from repositories.trip_repository import TripRepository
from repositories.conversation_repository import ConversationRepository
from repositories.message_repository import MessageRepository
from repositories.agent_run_repository import AgentRunRepository
from services.planning_service import run_travel_planning
from graph.state import WorkflowStatus

DEMO_SETTINGS = Settings(_env_file=None, demo_mode=True)


def test_planning_service_complete_lifecycle_with_persistence():
    """Verify run_travel_planning loads trip, creates messages, and records agent runs."""
    store = MockDataStore()
    trip_repo = TripRepository(store=store, settings=DEMO_SETTINGS)
    conv_repo = ConversationRepository(store=store, settings=DEMO_SETTINGS)
    msg_repo = MessageRepository(store=store, settings=DEMO_SETTINGS)
    run_repo = AgentRunRepository(store=store, settings=DEMO_SETTINGS)

    user_id = "test-user-uuid"
    session_state = {}

    # 1. Create preliminary trip
    trip = trip_repo.create_trip(user_id, {
        "origin": "SFO",
        "destination": "Tokyo",
        "start_date": "2026-11-01",
        "end_date": "2026-11-10",
        "travelers": 2,
        "budget": 5000.0,
        "currency": "USD",
        "status": "DRAFT",
    })

    # 2. Create conversation
    conv = conv_repo.create_conversation(user_id, trip_id=trip["id"], title="Tokyo Planning")

    # 3. Execute planning service
    req_text = "Trip from SFO to Tokyo from 2026-11-01 to 2026-11-10 for 2 people with $5000 budget."
    state = run_travel_planning(
        user_request=req_text,
        user_id=user_id,
        trip_id=trip["id"],
        conversation_id=conv["id"],
        session_state=session_state,
        trip_repo=trip_repo,
        conv_repo=conv_repo,
        msg_repo=msg_repo,
        run_repo=run_repo,
    )

    # Assertions on state
    assert state["planning_status"] in [
        WorkflowStatus.READY_FOR_ITINERARY.value,
        WorkflowStatus.READY_WITH_WARNINGS.value,
        WorkflowStatus.READY_FOR_VALIDATION.value,
    ]
    assert state["destination"] == "Tokyo"
    assert session_state["workflow_status"] in [
        WorkflowStatus.READY_FOR_ITINERARY.value,
        WorkflowStatus.READY_WITH_WARNINGS.value,
        WorkflowStatus.READY_FOR_VALIDATION.value,
    ]

    # Assertions on message repository
    messages = msg_repo.list_messages_for_conversation(conv["id"])
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert "Travel Analysis" in messages[1]["content"]

    # Assertions on agent runs
    runs = run_repo.list_runs_for_trip(trip["id"])
    assert len(runs) == 1
    assert runs[0]["agent_name"] == "planner_orchestrator"
    assert runs[0]["status"] == "SUCCESS"


def test_planning_service_clarification_persists_questions():
    """Verify clarification questions are persisted to conversation thread when parameters are missing."""
    store = MockDataStore()
    trip_repo = TripRepository(store=store, settings=DEMO_SETTINGS)
    conv_repo = ConversationRepository(store=store, settings=DEMO_SETTINGS)
    msg_repo = MessageRepository(store=store, settings=DEMO_SETTINGS)
    run_repo = AgentRunRepository(store=store, settings=DEMO_SETTINGS)

    user_id = "test-user-uuid"
    conv = conv_repo.create_conversation(user_id, title="Japan Inquiries")

    req_text = "Japan trip plan karo."
    state = run_travel_planning(
        user_request=req_text,
        user_id=user_id,
        conversation_id=conv["id"],
        trip_repo=trip_repo,
        conv_repo=conv_repo,
        msg_repo=msg_repo,
        run_repo=run_repo,
    )

    assert state["planning_status"] == WorkflowStatus.NEEDS_CLARIFICATION.value
    assert state["clarification_required"] is True

    messages = msg_repo.list_messages_for_conversation(conv["id"])
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert "I need a few details before planning" in messages[1]["content"]
