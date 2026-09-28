"""Weather MCP tools delegating to the Weather Provider adapter."""

from models.mcp import (
    GetCurrentWeatherInput,
    GetCurrentWeatherOutput,
    GetForecastInput,
    GetForecastOutput,
    GetWeatherAlertsInput,
    GetWeatherAlertsOutput,
)
from mcp.providers.weather_provider import weather_provider


def mcp_get_current_weather(params: GetCurrentWeatherInput) -> GetCurrentWeatherOutput:
    """Retrieve real-time meteorological observations for a destination."""
    return weather_provider.get_current_weather(location=params.location)


def mcp_get_forecast(params: GetForecastInput) -> GetForecastOutput:
    """Retrieve sequential multi-day daily forecasts across trip dates."""
    return weather_provider.get_forecast(
        location=params.location,
        start_date=params.start_date,
        end_date=params.end_date,
    )


def mcp_get_weather_alerts(params: GetWeatherAlertsInput) -> GetWeatherAlertsOutput:
    """Retrieve active severe meteorological warnings, storms, or typhoons."""
    return weather_provider.get_weather_alerts(location=params.location)
