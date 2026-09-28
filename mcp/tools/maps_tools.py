"""Maps MCP tools implementing spatial POI discovery, route computation, and travel-time estimates."""

from typing import List
from models.mcp import (
    PlaceItem,
    SearchPlacesInput,
    SearchPlacesOutput,
    CalculateRouteInput,
    CalculateRouteOutput,
    EstimateTravelTimeInput,
    EstimateTravelTimeOutput,
)


def mcp_search_places(params: SearchPlacesInput) -> SearchPlacesOutput:
    """Discover prominent attractions and cultural points of interest."""
    dest = params.location.title()

    places = [
        PlaceItem(
            name=f"{dest} Imperial Landmark & Historical Gardens",
            location=f"Central Quarter, {dest}",
            category="Cultural Landmark",
            rating=4.8,
            estimated_time_spent_hours=2.5,
            demo_data=True,
        ),
        PlaceItem(
            name=f"{dest} National Museum of Modern Art",
            location=f"Arts District, {dest}",
            category="Museum",
            rating=4.6,
            estimated_time_spent_hours=3.0,
            demo_data=True,
        ),
        PlaceItem(
            name=f"{dest} Panorama Sky Observatory Deck",
            location=f"Financial Heights, {dest}",
            category="Observation & Skyline",
            rating=4.7,
            estimated_time_spent_hours=1.5,
            demo_data=True,
        ),
    ]

    return SearchPlacesOutput(
        places=places[: params.limit],
        demo_data=True,
    )


def mcp_calculate_route(params: CalculateRouteInput) -> CalculateRouteOutput:
    """Compute transit corridor distance, duration, and turn-by-turn navigation steps."""
    mode = params.mode.lower()
    speed_factor = 45.0 if mode == "driving" else (30.0 if mode == "transit" else 4.5)
    distance_km = 12.4
    duration_mins = int(round((distance_km / speed_factor) * 60))

    steps = [
        f"Depart {params.origin} heading towards transit artery.",
        f"Board Metropolitan Express Route towards {params.destination}.",
        f"Arrive at destination terminal: {params.destination}.",
    ]

    return CalculateRouteOutput(
        origin=params.origin,
        destination=params.destination,
        mode=params.mode,
        distance_km=distance_km,
        duration_minutes=duration_mins,
        steps=steps,
        demo_data=True,
    )


def mcp_estimate_travel_time(params: EstimateTravelTimeInput) -> EstimateTravelTimeOutput:
    """Estimate transit duration between waypoints and suggest airport/transit transfer buffer."""
    is_airport = "airport" in params.origin.lower() or "airport" in params.destination.lower()
    duration = 45 if is_airport else 20
    buffer = 40 if is_airport else 15

    return EstimateTravelTimeOutput(
        origin=params.origin,
        destination=params.destination,
        mode=params.mode,
        duration_minutes=duration,
        buffer_minutes=buffer,
        demo_data=True,
    )
