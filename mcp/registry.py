"""Central registry for MCP tool descriptors, schemas, and execution handlers."""

from typing import Dict, Any, Callable, Type, List, Optional
from pydantic import BaseModel

from models.mcp import (
    SearchFlightsInput,
    SearchFlightsOutput,
    CompareFlightsInput,
    CompareFlightsOutput,
    GetFlightDetailsInput,
    GetFlightDetailsOutput,
    SearchHotelsInput,
    SearchHotelsOutput,
    GetHotelDetailsInput,
    GetHotelDetailsOutput,
    SearchPlacesInput,
    SearchPlacesOutput,
    CalculateRouteInput,
    CalculateRouteOutput,
    EstimateTravelTimeInput,
    EstimateTravelTimeOutput,
    GetCurrentWeatherInput,
    GetCurrentWeatherOutput,
    GetForecastInput,
    GetForecastOutput,
    GetWeatherAlertsInput,
    GetWeatherAlertsOutput,
    WebSearchInput,
    WebSearchOutput,
    FetchPageInput,
    FetchPageOutput,
    SearchNewsInput,
    SearchNewsOutput,
    GetExchangeRateInput,
    GetExchangeRateOutput,
)
from mcp.tools import (
    mcp_search_flights,
    mcp_compare_flights,
    mcp_get_flight_details,
    mcp_search_hotels,
    mcp_get_hotel_details,
    mcp_search_places,
    mcp_calculate_route,
    mcp_estimate_travel_time,
    mcp_get_current_weather,
    mcp_get_forecast,
    mcp_get_weather_alerts,
    mcp_web_search,
    mcp_fetch_page,
    mcp_search_news,
    mcp_get_exchange_rate,
)


class MCPToolDescriptor:
    """Metadata specification and handler binding for an MCP tool."""

    def __init__(
        self,
        name: str,
        description: str,
        domain: str,
        input_schema: Type[BaseModel],
        output_schema: Type[BaseModel],
        handler: Callable[[Any], BaseModel],
        timeout_seconds: float = 5.0,
        max_retries: int = 2,
    ):
        self.name = name
        self.description = description
        self.domain = domain
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.handler = handler
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries


class MCPToolRegistry:
    """In-memory registry of all available MCP tools."""

    _tools: Dict[str, MCPToolDescriptor] = {}

    @classmethod
    def register(cls, descriptor: MCPToolDescriptor) -> None:
        """Register a tool descriptor."""
        cls._tools[descriptor.name] = descriptor

    @classmethod
    def get_tool(cls, name: str) -> Optional[MCPToolDescriptor]:
        """Lookup tool descriptor by name."""
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> List[MCPToolDescriptor]:
        """List all registered MCP tool descriptors."""
        return list(cls._tools.values())

    @classmethod
    def list_tools_by_domain(cls, domain: str) -> List[MCPToolDescriptor]:
        """Filter registered tools by functional domain."""
        return [t for t in cls._tools.values() if t.domain == domain]


# Initialize and populate default MCP tools
def _init_default_registry():
    # 1. Flight Tools
    MCPToolRegistry.register(
        MCPToolDescriptor(
            name="search_flights",
            description="Search scheduled air travel corridors by origin, destination, dates, and budget.",
            domain="flight",
            input_schema=SearchFlightsInput,
            output_schema=SearchFlightsOutput,
            handler=mcp_search_flights,
        )
    )
    MCPToolRegistry.register(
        MCPToolDescriptor(
            name="compare_flights",
            description="Evaluate and rank multiple flight options by price, duration, or stops.",
            domain="flight",
            input_schema=CompareFlightsInput,
            output_schema=CompareFlightsOutput,
            handler=mcp_compare_flights,
        )
    )
    MCPToolRegistry.register(
        MCPToolDescriptor(
            name="get_flight_details",
            description="Retrieve detailed baggage allowance and cancellation policies for a flight.",
            domain="flight",
            input_schema=GetFlightDetailsInput,
            output_schema=GetFlightDetailsOutput,
            handler=mcp_get_flight_details,
        )
    )

    # 2. Hotel Tools
    MCPToolRegistry.register(
        MCPToolDescriptor(
            name="search_hotels",
            description="Discover lodging options by destination, dates, guests, and preferences.",
            domain="hotel",
            input_schema=SearchHotelsInput,
            output_schema=SearchHotelsOutput,
            handler=mcp_search_hotels,
        )
    )
    MCPToolRegistry.register(
        MCPToolDescriptor(
            name="get_hotel_details",
            description="Inspect property amenities, policies, and check-in logistics.",
            domain="hotel",
            input_schema=GetHotelDetailsInput,
            output_schema=GetHotelDetailsOutput,
            handler=mcp_get_hotel_details,
        )
    )

    # 3. Maps Tools
    MCPToolRegistry.register(
        MCPToolDescriptor(
            name="search_places",
            description="Discover points of interest, cultural landmarks, and attractions in a destination.",
            domain="maps",
            input_schema=SearchPlacesInput,
            output_schema=SearchPlacesOutput,
            handler=mcp_search_places,
        )
    )
    MCPToolRegistry.register(
        MCPToolDescriptor(
            name="calculate_route",
            description="Calculate distance, duration, and transit directions between two waypoints.",
            domain="maps",
            input_schema=CalculateRouteInput,
            output_schema=CalculateRouteOutput,
            handler=mcp_calculate_route,
        )
    )
    MCPToolRegistry.register(
        MCPToolDescriptor(
            name="estimate_travel_time",
            description="Estimate transit travel time and safety buffer between locations.",
            domain="maps",
            input_schema=EstimateTravelTimeInput,
            output_schema=EstimateTravelTimeOutput,
            handler=mcp_estimate_travel_time,
        )
    )

    # 4. Weather Tools
    MCPToolRegistry.register(
        MCPToolDescriptor(
            name="get_current_weather",
            description="Retrieve real-time meteorological conditions for a city.",
            domain="weather",
            input_schema=GetCurrentWeatherInput,
            output_schema=GetCurrentWeatherOutput,
            handler=mcp_get_current_weather,
        )
    )
    MCPToolRegistry.register(
        MCPToolDescriptor(
            name="get_forecast",
            description="Retrieve multi-day daily weather forecast and hazard advisories.",
            domain="weather",
            input_schema=GetForecastInput,
            output_schema=GetForecastOutput,
            handler=mcp_get_forecast,
        )
    )
    MCPToolRegistry.register(
        MCPToolDescriptor(
            name="get_weather_alerts",
            description="Check for active extreme meteorological warnings or storm alerts.",
            domain="weather",
            input_schema=GetWeatherAlertsInput,
            output_schema=GetWeatherAlertsOutput,
            handler=mcp_get_weather_alerts,
        )
    )

    # 5. Search Tools
    MCPToolRegistry.register(
        MCPToolDescriptor(
            name="web_search",
            description="Execute search returning third-party web snippets marked as untrusted data.",
            domain="search",
            input_schema=WebSearchInput,
            output_schema=WebSearchOutput,
            handler=mcp_web_search,
        )
    )
    MCPToolRegistry.register(
        MCPToolDescriptor(
            name="fetch_page",
            description="Fetch text from an allowed domain under strict sandboxing and sanitization.",
            domain="search",
            input_schema=FetchPageInput,
            output_schema=FetchPageOutput,
            handler=mcp_fetch_page,
        )
    )
    MCPToolRegistry.register(
        MCPToolDescriptor(
            name="search_news",
            description="Search regional news, events, and festivals for a destination.",
            domain="search",
            input_schema=SearchNewsInput,
            output_schema=SearchNewsOutput,
            handler=mcp_search_news,
        )
    )

    # 6. Currency Tools
    MCPToolRegistry.register(
        MCPToolDescriptor(
            name="get_exchange_rate",
            description="Retrieve normalized foreign exchange conversion rate between two currencies.",
            domain="currency",
            input_schema=GetExchangeRateInput,
            output_schema=GetExchangeRateOutput,
            handler=mcp_get_exchange_rate,
        )
    )


_init_default_registry()
