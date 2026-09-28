"""Maps MCP tools delegating to the Maps and Places Provider adapter."""

from models.mcp import (
    SearchPlacesInput,
    SearchPlacesOutput,
    CalculateRouteInput,
    CalculateRouteOutput,
    EstimateTravelTimeInput,
    EstimateTravelTimeOutput,
)
from mcp.providers.maps_provider import maps_provider


def mcp_search_places(params: SearchPlacesInput) -> SearchPlacesOutput:
    """Discover prominent attractions and cultural points of interest."""
    return maps_provider.search_places(
        query=params.query,
        location=params.location,
        category=params.category,
        limit=params.limit,
    )


def mcp_calculate_route(params: CalculateRouteInput) -> CalculateRouteOutput:
    """Compute transit corridor distance, duration, and turn-by-turn navigation steps."""
    return maps_provider.calculate_route(
        origin=params.origin,
        destination=params.destination,
        mode=params.mode,
    )


def mcp_estimate_travel_time(params: EstimateTravelTimeInput) -> EstimateTravelTimeOutput:
    """Estimate transit duration between waypoints and suggest airport/transit transfer buffer."""
    return maps_provider.estimate_travel_time(
        origin=params.origin,
        destination=params.destination,
        mode=params.mode,
    )
