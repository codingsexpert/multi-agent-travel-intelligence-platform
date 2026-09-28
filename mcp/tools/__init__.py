"""MCP Tool registry exports."""

from mcp.tools.flight_tools import (
    mcp_search_flights,
    mcp_compare_flights,
    mcp_get_flight_details,
)
from mcp.tools.hotel_tools import (
    mcp_search_hotels,
    mcp_get_hotel_details,
)
from mcp.tools.maps_tools import (
    mcp_search_places,
    mcp_calculate_route,
    mcp_estimate_travel_time,
)
from mcp.tools.weather_tools import (
    mcp_get_current_weather,
    mcp_get_forecast,
    mcp_get_weather_alerts,
)
from mcp.tools.search_tools import (
    mcp_web_search,
    mcp_fetch_page,
    mcp_search_news,
)
from mcp.tools.currency_tools import (
    mcp_get_exchange_rate,
)

__all__ = [
    "mcp_search_flights",
    "mcp_compare_flights",
    "mcp_get_flight_details",
    "mcp_search_hotels",
    "mcp_get_hotel_details",
    "mcp_search_places",
    "mcp_calculate_route",
    "mcp_estimate_travel_time",
    "mcp_get_current_weather",
    "mcp_get_forecast",
    "mcp_get_weather_alerts",
    "mcp_web_search",
    "mcp_fetch_page",
    "mcp_search_news",
    "mcp_get_exchange_rate",
]
