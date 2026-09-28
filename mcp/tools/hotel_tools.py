"""Hotel MCP tools implementing accommodation discovery and property specification."""

from datetime import date
from typing import List
from models.specialized_options import HotelOption
from models.mcp import (
    SearchHotelsInput,
    SearchHotelsOutput,
    GetHotelDetailsInput,
    GetHotelDetailsOutput,
)


def mcp_search_hotels(params: SearchHotelsInput) -> SearchHotelsOutput:
    """Discover lodging alternatives matching geographic and budgetary criteria."""
    try:
        s_dt = date.fromisoformat(params.check_in)
        e_dt = date.fromisoformat(params.check_out)
        nights = max((e_dt - s_dt).days, 1)
    except Exception:
        nights = 5

    base_nightly = 160.0 if params.currency == "USD" else 12500.0

    hotels = [
        HotelOption(
            name=f"The Grand Heritage Hotel {params.destination.title()}",
            location=f"Central District, {params.destination.title()}",
            rating=4.7,
            price_per_night=base_nightly,
            total_price=round(base_nightly * nights * params.rooms, 2),
            currency=params.currency,
            amenities=["High-Speed Wi-Fi", "Daily Breakfast Buffet", "Fitness Center & Spa", "24/7 Concierge"],
            source="[DEMO_DATA] Hotel MCP Server (Mock Lodging Aggregator)",
            availability_status="AVAILABLE (MOCK)",
            demo_data=True,
        ),
        HotelOption(
            name=f"{params.destination.title()} Boutique Suites & Terrace",
            location=f"Historic Quarter, {params.destination.title()}",
            rating=4.5,
            price_per_night=round(base_nightly * 0.82, 2),
            total_price=round(base_nightly * 0.82 * nights * params.rooms, 2),
            currency=params.currency,
            amenities=["Complimentary Espresso Bar", "City View Terrace", "Bicycle Rental", "Eco-Certified"],
            source="[DEMO_DATA] Hotel MCP Server (Mock Lodging Aggregator)",
            availability_status="AVAILABLE (MOCK)",
            demo_data=True,
        ),
    ]

    return SearchHotelsOutput(
        hotels=hotels,
        total_found=len(hotels),
        demo_data=True,
    )


def mcp_get_hotel_details(params: GetHotelDetailsInput) -> GetHotelDetailsOutput:
    """Retrieve detailed property specifications and check-in logistics."""
    hotel_opt = HotelOption(
        name=params.hotel_id,
        location="Prime District Center",
        rating=4.8,
        price_per_night=180.0,
        total_price=900.0,
        currency="USD",
        amenities=["Rooftop Pool", "Michelin-Starred Restaurant", "Free Airport Shuttle"],
        source="[DEMO_DATA] Hotel MCP Server",
        availability_status="AVAILABLE (MOCK)",
        demo_data=True,
    )

    return GetHotelDetailsOutput(
        hotel=hotel_opt,
        policies=[
            "Cancellation permitted up to 48 hours prior to arrival",
            "Valid government ID and credit card required at check-in",
            "Pet friendly rooms available upon request",
        ],
        check_in_time="15:00",
        check_out_time="11:00",
        demo_data=True,
    )
