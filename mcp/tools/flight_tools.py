"""Flight MCP tools delegating to the Flight Provider adapter."""

from models.mcp import (
    SearchFlightsInput,
    SearchFlightsOutput,
    CompareFlightsInput,
    CompareFlightsOutput,
    GetFlightDetailsInput,
    GetFlightDetailsOutput,
)
from mcp.providers.flight_provider import flight_provider


def mcp_search_flights(params: SearchFlightsInput) -> SearchFlightsOutput:
    """Discover scheduled flight options matching corridor and budget constraints."""
    return flight_provider.search_flights(params)


def mcp_compare_flights(params: CompareFlightsInput) -> CompareFlightsOutput:
    """Compare candidate flight options and recommend optimal itinerary."""
    return flight_provider.compare_flights(params)


def mcp_get_flight_details(params: GetFlightDetailsInput) -> GetFlightDetailsOutput:
    """Retrieve detailed seat class, baggage allowance, and cancellation policy for a flight."""
    return flight_provider.get_flight_details(params)
