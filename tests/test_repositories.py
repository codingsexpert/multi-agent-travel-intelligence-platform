"""Unit tests for repository layer and user data isolation in DEMO_MODE."""

from datetime import date
import pytest
from repositories.mock_store import MockDataStore
from repositories.trip_repository import TripRepository
from repositories.conversation_repository import ConversationRepository
from repositories.message_repository import MessageRepository
from repositories.agent_run_repository import AgentRunRepository
from utils.exceptions import ValidationError


@pytest.fixture
def clean_store():
    """Provide an isolated, clean in-memory mock store for each test."""
    store = MockDataStore()
    return store


@pytest.fixture
def repositories(clean_store):
    """Instantiate repository classes bound to the isolated store."""
    trip_repo = TripRepository(store=clean_store)
    conv_repo = ConversationRepository(store=clean_store)
    msg_repo = MessageRepository(store=clean_store)
    run_repo = AgentRunRepository(store=clean_store)
    return trip_repo, conv_repo, msg_repo, run_repo


def test_trip_repository_crud_and_isolation(repositories):
    """Verify trip creation, retrieval, preferences association, and user data isolation."""
    trip_repo, _, _, _ = repositories
    user_a = "user-aaa-1111"
    user_b = "user-bbb-2222"

    trip_data = {
        "origin": "SFO",
        "destination": "Tokyo",
        "start_date": date(2026, 11, 1),
        "end_date": date(2026, 11, 10),
        "travelers": 2,
        "budget": 4500.0,
        "currency": "USD",
        "status": "DRAFT",
    }
    preferences_data = {
        "preferences": ["Food", "Culture"],
        "travel_style": "Balanced",
        "accommodation_preference": "4 Star",
        "additional_requirements": "Ramen exploration",
    }

    # User A creates trip
    created = trip_repo.create_trip(user_a, trip_data, preferences_data)
    assert created["id"] is not None
    assert created["user_id"] == user_a
    assert created["origin"] == "SFO"
    assert created["is_demo"] is True
    assert "preferences" in created
    assert created["preferences"]["travel_style"] == "Balanced"

    # User A can retrieve their trip
    fetched = trip_repo.get_trip(created["id"], user_id=user_a)
    assert fetched is not None
    assert fetched["id"] == created["id"]
    assert fetched["destination"] == "Tokyo"

    # User B CANNOT retrieve User A's trip (Data Isolation)
    b_fetched = trip_repo.get_trip(created["id"], user_id=user_b)
    assert b_fetched is None

    # User B's trip list should be empty
    assert trip_repo.list_user_trips(user_b) == []

    # User A's trip list contains 1 trip
    user_a_trips = trip_repo.list_user_trips(user_a)
    assert len(user_a_trips) == 1
    assert user_a_trips[0]["id"] == created["id"]

    # Status update
    updated = trip_repo.update_trip_status(created["id"], user_id=user_a, status="PLANNING")
    assert updated is not None
    assert updated["status"] == "PLANNING"

    # User B cannot update User A's trip
    b_updated = trip_repo.update_trip_status(created["id"], user_id=user_b, status="CANCELLED")
    assert b_updated is None


def test_conversation_and_message_repository(repositories):
    """Verify thread creation, messaging, and chronological ordering."""
    trip_repo, conv_repo, msg_repo, _ = repositories
    user_id = "user-123"
    other_user = "user-456"

    # Create conversation
    conv = conv_repo.create_conversation(user_id=user_id, title="Tokyo Trip Chat")
    assert conv["id"] is not None
    assert conv["title"] == "Tokyo Trip Chat"
    assert conv["is_demo"] is True

    # User isolation check on conversation
    assert conv_repo.get_conversation(conv["id"], user_id=user_id) is not None
    assert conv_repo.get_conversation(conv["id"], user_id=other_user) is None

    # Append messages
    m1 = msg_repo.create_message(conv["id"], role="user", content="I want to visit Tokyo.")
    m2 = msg_repo.create_message(conv["id"], role="assistant", content="Great choice! What dates?")
    m3 = msg_repo.create_message(conv["id"], role="system", content="Routing to Planner Agent.")

    assert m1["role"] == "user"
    assert m2["role"] == "assistant"
    assert m3["role"] == "system"

    # Invalid role check
    with pytest.raises(ValidationError):
        msg_repo.create_message(conv["id"], role="invalid_role", content="hello")

    # Chronological retrieval
    messages = msg_repo.list_messages_for_conversation(conv["id"])
    assert len(messages) == 3
    assert messages[0]["content"] == "I want to visit Tokyo."
    assert messages[1]["content"] == "Great choice! What dates?"
    assert messages[2]["content"] == "Routing to Planner Agent."


def test_agent_run_repository(repositories):
    """Verify tracking of agent execution runs and status transitions."""
    trip_repo, _, _, run_repo = repositories
    trip = trip_repo.create_trip("user-1", {
        "origin": "JFK", "destination": "London",
        "start_date": date(2026, 12, 1), "end_date": date(2026, 12, 8),
        "travelers": 1, "budget": 2000.0,
    })

    # Start run
    run = run_repo.create_agent_run(trip_id=trip["id"], agent_name="FlightAgent")
    assert run["status"] == "RUNNING"
    assert run["agent_name"] == "FlightAgent"
    assert run["is_demo"] is True

    # Complete run
    completed = run_repo.update_agent_run(
        run_id=run["id"],
        status="COMPLETED",
        metadata={"candidates_found": 5, "duration_ms": 120},
    )
    assert completed is not None
    assert completed["status"] == "COMPLETED"
    assert completed["metadata"]["candidates_found"] == 5

    # List runs
    runs = run_repo.list_runs_for_trip(trip["id"])
    assert len(runs) == 1
    assert runs[0]["id"] == run["id"]
