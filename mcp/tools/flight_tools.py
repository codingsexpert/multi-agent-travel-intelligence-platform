"""Flight MCP tools implementing aviation search, comparative ranking, and itinerary specifications."""

from typing import List, Dict, Any
from models.specialized_options import FlightOption
from models.mcp import (
    SearchFlightsInput,
    SearchFlightsOutput,
    CompareFlightsInput,
    CompareFlightsOutput,
    GetFlightDetailsInput,
    GetFlightDetailsOutput,
)


def mcp_search_flights(params: SearchFlightsInput) -> SearchFlightsOutput:
    """Discover scheduled flight options matching corridor and budget constraints."""
    origin_code = params.origin[:3].upper() if len(params.origin) >= 3 else "ORG"
    dest_code = params.destination[:3].upper() if len(params.destination) >= 3 else "DST"

    base_rate = 650.0 if params.currency == "USD" else 55000.0
    multiplier = 1.0 if params.cabin_class == "economy" else (1.6 if params.cabin_class == "premium_economy" else 2.8)

    f1_price = round(base_rate * multiplier * params.travellers, 2)
    f2_price = round((base_rate * 0.88) * multiplier * params.travellers, 2)

    flights = [
        FlightOption(
            airline=f"Global {params.destination.title()} Express",
            flight_number=f"{dest_code}-101",
            departure_airport=f"{origin_code} Terminal 2",
            arrival_airport=f"{dest_code} Int'l",
            departure_time=f"{params.departure_date} 08:30",
            arrival_time=f"{params.departure_date} 14:45",
            duration="11h 15m",
            stops=0,
            cabin_class=params.cabin_class.title(),
            price=f1_price,
            currency=params.currency,
            source="[DEMO_DATA] Flight MCP Server (Mock Global GDS)",
            availability_status="AVAILABLE (MOCK)",
            demo_data=True,
        ),
        FlightOption(
            airline=f"{params.origin.title()} Airways",
            flight_number=f"{origin_code}-404",
            departure_airport=f"{origin_code} Terminal 1",
            arrival_airport=f"{dest_code} Int'l",
            departure_time=f"{params.departure_date} 13:15",
            arrival_time=f"{params.departure_date} 21:00",
            duration="12h 45m",
            stops=1,
            cabin_class=params.cabin_class.title(),
            price=f2_price,
            currency=params.currency,
            source="[DEMO_DATA] Flight MCP Server (Mock Global GDS)",
            availability_status="AVAILABLE (MOCK)",
            demo_data=True,
        ),
    ]

    return SearchFlightsOutput(
        flights=flights,
        total_found=len(flights),
        demo_data=True,
    )


def mcp_compare_flights(params: CompareFlightsInput) -> CompareFlightsOutput:
    """Compare candidate flight options and recommend optimal itinerary."""
    comparisons = []
    for fid in params.flight_ids:
        comparisons.append({
            "flight_id": fid,
            "metric": params.sort_by,
            "score": 9.2 if "101" in fid else 8.5,
            "value_assessment": "Direct flight with optimal daylight arrival" if "101" in fid else "Budget-friendly with single layover",
        })

    recommended = params.flight_ids[0] if params.flight_ids else None
    return CompareFlightsOutput(
        comparisons=comparisons,
        recommended_id=recommended,
        demo_data=True,
    )


def mcp_get_flight_details(params: GetFlightDetailsInput) -> GetFlightDetailsOutput:
    """Retrieve detailed seat class, baggage allowance, and cancellation policy for a flight."""
    flight_opt = FlightOption(
        airline="Premier Transatlantic Airways",
        flight_number=params.flight_id,
        departure_airport="JFK Terminal 4",
        arrival_airport="LHR Terminal 5",
        departure_time="2026-10-15 08:30",
        arrival_time="2026-10-15 14:45",
        duration="11h 15m",
        stops=0,
        cabin_class="Economy",
        price=1200.0,
        currency="USD",
        source="[DEMO_DATA] Flight MCP Server",
        availability_status="CONFIRMED (MOCK)",
        demo_data=True,
    )

    return GetFlightDetailsOutput(
        flight=flight_opt,
        baggage_allowance="1 personal item + 1 carry-on (10kg) + 2 checked bags (23kg each)",
        cancellation_policy="Full refund within 24h of booking; thereafter date change permitted with $50 fee",
        demo_data=True,
    )
