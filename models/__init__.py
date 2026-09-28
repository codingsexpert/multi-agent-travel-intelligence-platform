"""Domain data models for the Multi-Agent Travel Intelligence Platform."""

from models.travel_request import (
    TravelRequest,
    TravelerPreferences,
    TripConstraints,
    TripMetadata,
)

from models.planner import (
    NormalizedTravelRequest,
    ClarificationRequest,
    PlannerResult,
)

from models.specialized_options import (
    FlightOption,
    HotelOption,
    ActivityOption,
    WeatherObservation,
    DestinationResearch,
)

__all__ = [
    "TravelRequest",
    "TravelerPreferences",
    "TripConstraints",
    "TripMetadata",
    "NormalizedTravelRequest",
    "ClarificationRequest",
    "PlannerResult",
    "FlightOption",
    "HotelOption",
    "ActivityOption",
    "WeatherObservation",
    "DestinationResearch",
]
