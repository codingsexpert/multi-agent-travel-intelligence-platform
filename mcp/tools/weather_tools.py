"""Weather MCP tools implementing snapshot meteorological queries, multi-day forecasting, and storm alerts."""

from datetime import datetime, date, timedelta
from typing import List
from models.specialized_options import WeatherObservation
from models.mcp import (
    GetCurrentWeatherInput,
    GetCurrentWeatherOutput,
    GetForecastInput,
    GetForecastOutput,
    GetWeatherAlertsInput,
    GetWeatherAlertsOutput,
)


def mcp_get_current_weather(params: GetCurrentWeatherInput) -> GetCurrentWeatherOutput:
    """Retrieve real-time meteorological observations for a destination."""
    return GetCurrentWeatherOutput(
        location=params.location.title(),
        temperature="21°C / 70°F",
        condition="Partly Cloudy",
        humidity_percent=55,
        wind_speed_kmh=14.0,
        demo_data=True,
    )


def mcp_get_forecast(params: GetForecastInput) -> GetForecastOutput:
    """Retrieve sequential multi-day daily forecasts across trip dates."""
    try:
        s_dt = date.fromisoformat(params.start_date)
        e_dt = date.fromisoformat(params.end_date)
        days = max((e_dt - s_dt).days, 1)
    except Exception:
        s_dt = date.today() + timedelta(days=14)
        days = 5

    conditions_cycle = [
        (19.0, 66.2, "Partly Cloudy", 15, "Optimal for walking tours and cultural excursions."),
        (22.0, 71.6, "Sunny & Clear", 5, "Clear skies with excellent visibility; ideal for outdoor sightseeing."),
        (18.0, 64.4, "Scattered Showers", 60, "Occasional afternoon showers; carry compact umbrella or visit museums."),
        (20.0, 68.0, "Mild & Breezy", 20, "Comfortable temperate climate throughout the day."),
        (23.0, 73.4, "Warm & Sunny", 10, "Warm afternoon temperatures; stay hydrated during excursions."),
    ]

    forecasts = []
    for i in range(min(days, 14)):
        current_d = (s_dt + timedelta(days=i)).isoformat()
        temp_c, temp_f, cond, precip, warn = conditions_cycle[i % len(conditions_cycle)]
        forecasts.append(
            WeatherObservation(
                date=current_d,
                location=params.location.title(),
                temperature_celsius=temp_c,
                temperature_fahrenheit=temp_f,
                condition=cond,
                precipitation_probability=precip,
                humidity_percentage=55,
                warning=warn,
                source="[DEMO_DATA] Weather MCP Server (Mock Meteorological Feed)",
                demo_data=True,
            )
        )

    return GetForecastOutput(
        location=params.location.title(),
        forecasts=forecasts,
        demo_data=True,
    )


def mcp_get_weather_alerts(params: GetWeatherAlertsInput) -> GetWeatherAlertsOutput:
    """Retrieve active severe meteorological warnings, storms, or typhoons."""
    return GetWeatherAlertsOutput(
        location=params.location.title(),
        alerts=["No active extreme meteorological warnings for this region."],
        severity="NONE",
        demo_data=True,
    )
