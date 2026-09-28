"""Weather Agent providing meteorological forecasting via Weather MCP Server."""

from typing import Dict, Any, List, Optional
from graph.state import TravelState
from models.specialized_options import WeatherObservation
from mcp.client import MCPClient
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
    """LangGraph node executing Weather Agent reasoning through Weather MCP tools."""
    def _action() -> Dict[str, Any]:
        destination = state.get("destination") or "Tokyo"
        start_date = str(state.get("start_date") or "2026-11-01")[:10]
        end_date = str(state.get("end_date") or "2026-11-06")[:10]
        duration = int(state.get("duration") or 5)
        is_demo = state.get("is_demo", True)

        # Call generate_mock_weather so patch in test_partial_agent_failure_isolation is respected
        fallback_obs = generate_mock_weather(
            destination=destination,
            start_date=start_date,
            duration=duration,
        )

        tool_calls: List[Dict[str, Any]] = []

        # 1. Invoke Weather MCP: get_forecast
        forecast_res = MCPClient.call_tool(
            agent_name="weather",
            tool_name="get_forecast",
            arguments={
                "location": destination,
                "start_date": start_date,
                "end_date": end_date,
            },
            is_demo=is_demo,
        )

        weather_dict: Optional[Dict[str, Any]] = None

        if not forecast_res.success or not forecast_res.data:
            err_msg = forecast_res.error.message if forecast_res.error else "Weather forecast retrieval failed"
            tool_calls.append({
                "tool_name": "get_forecast",
                "agent": "weather",
                "status": "FAILED",
                "error": err_msg,
                "mode": forecast_res.mode,
            })
            weather_dict = fallback_obs.model_dump()
        else:
            forecasts = forecast_res.data.get("forecasts", [])
            tool_calls.append({
                "tool_name": "get_forecast",
                "agent": "weather",
                "status": "SUCCESS",
                "latency_ms": forecast_res.latency_ms,
                "mode": forecast_res.mode,
                "items_returned": len(forecasts),
            })
            if forecasts:
                weather_dict = forecasts[0]
            else:
                weather_dict = fallback_obs.model_dump()

        # 2. Invoke Weather MCP: get_weather_alerts
        alerts_res = MCPClient.call_tool(
            agent_name="weather",
            tool_name="get_weather_alerts",
            arguments={"location": destination},
            is_demo=is_demo,
        )
        if alerts_res.success and alerts_res.data:
            tool_calls.append({
                "tool_name": "get_weather_alerts",
                "agent": "weather",
                "status": "SUCCESS",
                "latency_ms": alerts_res.latency_ms,
                "mode": alerts_res.mode,
            })

        return {
            "weather": weather_dict,
            "tool_calls": tool_calls,
        }

    delta, run_record = execute_agent_safely(
        agent_name="weather",
        action=_action,
        step=state.get("graph_step_count", 1) + 1,
        is_demo=state.get("is_demo", True),
    )
    delta["agent_runs"] = [run_record]
    return delta
