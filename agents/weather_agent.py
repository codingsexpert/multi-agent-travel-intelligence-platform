"""Weather Agent providing destination climatological context and forecast estimates using mock data."""

from typing import Dict, Any, Optional
from graph.state import TravelState
from models.specialized_options import WeatherObservation
from agents.base_agent import execute_agent_safely


def generate_mock_weather(
    destination: str,
    start_date: Optional[str] = None,
    duration: int = 5,
) -> WeatherObservation:
    """Generate deterministic mock climatological forecast context for requested travel period."""
    dest = destination or "Tokyo"
    s_date = start_date or "Seasonal Forecast"
    dest_lower = dest.lower()

    if "tokyo" in dest_lower or "japan" in dest_lower:
        temp_c = 18.5
        cond = "Partly Cloudy with Crisp Clear Skies"
        precip = 15
        humid = 55
        warn = "Mild daytime temperatures; pack a light jacket for breezy evenings."
    elif "paris" in dest_lower or "france" in dest_lower:
        temp_c = 16.0
        cond = "Overcast with Mild Showers"
        precip = 35
        humid = 65
        warn = "Intermittent rainfall expected mid-week; compact umbrella recommended."
    elif "london" in dest_lower or "uk" in dest_lower:
        temp_c = 14.0
        cond = "Breezy with Scattered Clouds"
        precip = 40
        humid = 70
        warn = "Variable maritime conditions; layered clothing advised."
    elif "delhi" in dest_lower or "india" in dest_lower:
        temp_c = 28.0
        cond = "Warm & Sunny"
        precip = 5
        humid = 40
        warn = "Warm afternoon sun; carry sunscreen and stay well-hydrated."
    else:
        temp_c = 21.0
        cond = "Fair & Mostly Sunny"
        precip = 10
        humid = 48
        warn = "Pleasant travel conditions throughout the scheduled itinerary."

    temp_f = round((temp_c * 9 / 5) + 32, 1)

    return WeatherObservation(
        date=f"{s_date} ({duration} days window)",
        location=dest.title(),
        temperature_celsius=temp_c,
        temperature_fahrenheit=temp_f,
        condition=cond,
        precipitation_probability=precip,
        humidity_percentage=humid,
        warning=warn,
        source="Mock Climatological Service [DEMO_DATA]",
        demo_data=True,
    )


def weather_agent_node(state: TravelState) -> Dict[str, Any]:
    """LangGraph node executing Weather Agent logic."""
    def _action() -> Dict[str, Any]:
        destination = state.get("destination") or "Destination City"
        start_date = state.get("start_date")
        duration = state.get("duration") or 5

        weather_obs = generate_mock_weather(
            destination=destination,
            start_date=start_date,
            duration=duration,
        )
        return {
            "weather": weather_obs.model_dump(),
        }

    delta, run_record = execute_agent_safely(
        agent_name="weather",
        action=_action,
        step=state.get("graph_step_count", 1) + 1,
        is_demo=True,
    )
    delta["agent_runs"] = [run_record]
    return delta
