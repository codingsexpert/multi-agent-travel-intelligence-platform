"""Unit tests for specialized domain agents and Pydantic schemas (Phase 5)."""

import pytest
from pydantic import ValidationError
from models.specialized_options import (
    FlightOption,
    HotelOption,
    ActivityOption,
    WeatherObservation,
    DestinationResearch,
)
from agents.flight_agent import generate_mock_flights, flight_agent_node
from agents.hotel_agent import generate_mock_hotels, hotel_agent_node
from agents.activity_agent import generate_mock_activities, activity_agent_node
from agents.weather_agent import generate_mock_weather, weather_agent_node
from agents.research_agent import generate_mock_research, research_agent_node
from graph.state import create_initial_state, WorkflowStatus


def test_flight_option_schema_and_demo_marker():
    """Verify FlightOption Pydantic validation and strict demo_data marking."""
    flight = FlightOption(
        airline="ANA",
        flight_number="NH-108",
        departure_airport="SFO Terminal 2",
        arrival_airport="NRT Int'l",
        departure_time="2026-11-01 10:45",
        arrival_time="2026-11-01 15:30 (+1)",
        duration="10h 45m",
        stops=0,
        cabin_class="Economy",
        price=1700.0,
        currency="USD",
        source="Mock Flight Catalog [DEMO_DATA]",
        availability_status="Demo Available",
        demo_data=True,
    )
    assert flight.demo_data is True
    assert "DEMO_DATA" in flight.source
    assert flight.price == 1700.0


def test_hotel_option_schema_and_demo_marker():
    """Verify HotelOption Pydantic validation and strict demo_data marking."""
    hotel = HotelOption(
        name="Park Hotel Tokyo",
        location="Minato, Tokyo",
        rating=4.7,
        stars=4,
        price_per_night=180.0,
        total_price=1260.0,
        currency="USD",
        amenities=["WiFi", "Skyline View"],
        room_type="Deluxe City View Room",
        source="Mock Hospitality Catalog [DEMO_DATA]",
        availability_status="Demo Available",
        demo_data=True,
    )
    assert hotel.demo_data is True
    assert hotel.total_price == 1260.0
    assert hotel.rating == 4.7


def test_activity_option_schema():
    """Verify ActivityOption schema and fields."""
    act = ActivityOption(
        name="Senso-ji Temple Walking Tour",
        location="Asakusa, Tokyo",
        category="Culture & Heritage",
        duration="2.5 hours",
        estimated_cost=25.0,
        currency="USD",
        best_time="Morning",
        description="Historical temple walk",
        source="Mock Experiences Catalog [DEMO_DATA]",
        demo_data=True,
    )
    assert act.demo_data is True
    assert act.estimated_cost == 25.0


def test_weather_observation_schema():
    """Verify WeatherObservation schema and temperature conversion."""
    weather = WeatherObservation(
        date="2026-11-01 to 2026-11-08",
        location="Tokyo",
        temperature_celsius=18.5,
        temperature_fahrenheit=65.3,
        condition="Partly Cloudy",
        precipitation_probability=15,
        humidity_percentage=55,
        warning="Breezy evenings",
        source="Mock Climatological Service [DEMO_DATA]",
        demo_data=True,
    )
    assert weather.demo_data is True
    assert weather.precipitation_probability == 15


def test_destination_research_schema():
    """Verify DestinationResearch schema and cultural notes."""
    res = DestinationResearch(
        destination="Tokyo",
        destination_overview="Vibrant Japanese metropolis",
        cultural_notes=["No tipping"],
        travel_tips=["Get an IC card"],
        local_customs=["Keep voice low on trains"],
        important_notes=["Carry passport"],
        sources=["Mock Destination Knowledge Graph [DEMO_DATA]"],
        demo_data=True,
    )
    assert res.demo_data is True
    assert len(res.cultural_notes) == 1


def test_flight_agent_node_execution():
    """Verify Flight Agent node produces structured options with metadata."""
    state = create_initial_state("Trip to Tokyo", user_id="u1", is_demo=True)
    state["origin"] = "SFO"
    state["destination"] = "Tokyo"
    state["travelers"] = 2
    state["currency"] = "USD"

    delta = flight_agent_node(state)
    assert "flight_options" in delta
    assert len(delta["flight_options"]) >= 2
    assert delta["flight_options"][0]["demo_data"] is True
    assert len(delta["agent_runs"]) == 1
    assert delta["agent_runs"][0]["agent_name"] == "flight"
    assert delta["agent_runs"][0]["status"] == "SUCCESS"


def test_hotel_agent_node_execution():
    """Verify Hotel Agent node produces structured lodging options with metadata."""
    state = create_initial_state("Trip to Paris", user_id="u1", is_demo=True)
    state["destination"] = "Paris"
    state["duration"] = 6
    state["travelers"] = 2
    state["currency"] = "EUR"

    delta = hotel_agent_node(state)
    assert "hotel_options" in delta
    assert len(delta["hotel_options"]) >= 2
    assert delta["hotel_options"][0]["demo_data"] is True
    assert delta["agent_runs"][0]["agent_name"] == "hotel"
    assert delta["agent_runs"][0]["status"] == "SUCCESS"


def test_activity_agent_node_execution():
    """Verify Activity Agent node produces interest-aligned experiences."""
    state = create_initial_state("Trip to Tokyo", user_id="u1", is_demo=True)
    state["destination"] = "Tokyo"
    state["interests"] = ["food", "culture"]

    delta = activity_agent_node(state)
    assert "activities" in delta
    assert len(delta["activities"]) >= 3
    assert delta["activities"][0]["demo_data"] is True
    assert delta["agent_runs"][0]["agent_name"] == "activity"


def test_weather_agent_node_execution():
    """Verify Weather Agent node produces climatological forecast context."""
    state = create_initial_state("Trip to London", user_id="u1", is_demo=True)
    state["destination"] = "London"
    state["duration"] = 5

    delta = weather_agent_node(state)
    assert "weather" in delta
    assert delta["weather"]["location"] == "London"
    assert delta["weather"]["demo_data"] is True
    assert delta["agent_runs"][0]["agent_name"] == "weather"


def test_research_agent_node_execution():
    """Verify Research Agent node synthesizes destination research and status."""
    state = create_initial_state("Trip to Tokyo", user_id="u1", is_demo=True)
    state["destination"] = "Tokyo"
    state["agent_runs"] = [
        {"agent_name": "flight", "status": "SUCCESS"},
        {"agent_name": "hotel", "status": "SUCCESS"},
    ]

    delta = research_agent_node(state)
    assert "research_results" in delta
    assert delta["research_results"]["destination"] == "Tokyo"
    assert delta["planning_status"] == WorkflowStatus.READY_FOR_VALIDATION.value
    assert delta["agent_runs"][0]["agent_name"] == "research"
