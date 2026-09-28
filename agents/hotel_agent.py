"""Hotel Agent discovering lodging options via Hotel MCP Server."""

from typing import Dict, Any, List
from graph.state import TravelState
from models.specialized_options import HotelOption
from mcp.client import MCPClient
from agents.base_agent import execute_agent_safely


def generate_mock_hotels(
    destination: str,
    duration: int = 5,
    travelers: int = 1,
    currency: str = "USD",
    preference: str = "Hotel",
) -> List[HotelOption]:
    """Generate deterministic mock hotel candidates matching destination and duration."""
    dest = destination or "Tokyo"
    dur = max(1, duration or 5)
    curr = currency or "USD"
    pref = preference or "Hotel"

    dest_lower = dest.lower()
    if "tokyo" in dest_lower or "japan" in dest_lower:
        h1_name, h1_loc = "Park Hotel Tokyo Shiodome", "Minato, Tokyo"
        h2_name, h2_loc = "Candeo Hotels Tokyo Roppongi", "Roppongi, Tokyo"
    elif "paris" in dest_lower or "france" in dest_lower:
        h1_name, h1_loc = "Hotel Le Marais Signature", "Le Marais, Paris"
        h2_name, h2_loc = "CitizenM Paris Champs-Élysées", "8th Arrondissement, Paris"
    elif "london" in dest_lower or "uk" in dest_lower:
        h1_name, h1_loc = "The Bloomsbury Hotel", "Bloomsbury, London"
        h2_name, h2_loc = "Apex Temple Court Hotel", "City of London"
    else:
        h1_name, h1_loc = f"Grand {dest.title()} Central Hotel", f"Downtown {dest.title()}"
        h2_name, h2_loc = f"{dest.title()} Boutique Suites", f"Old Quarter, {dest.title()}"

    rate_1 = 180.0 if curr == "USD" else (14000.0 if curr == "INR" else 165.0)
    rate_2 = 120.0 if curr == "USD" else (9500.0 if curr == "INR" else 110.0)

    hotel_1 = HotelOption(
        name=h1_name,
        location=h1_loc,
        rating=4.7,
        stars=4,
        price_per_night=rate_1,
        total_price=round(rate_1 * dur, 2),
        currency=curr,
        amenities=["High-Speed WiFi", "Skyline View", "Full Buffet Breakfast", "Fitness Center"],
        room_type="Deluxe City View Room",
        source="Mock Hospitality Catalog [DEMO_DATA]",
        availability_status="Demo Available (3 rooms remaining)",
        demo_data=True,
    )

    hotel_2 = HotelOption(
        name=h2_name,
        location=h2_loc,
        rating=4.4,
        stars=3,
        price_per_night=rate_2,
        total_price=round(rate_2 * dur, 2),
        currency=curr,
        amenities=["Free WiFi", "Rooftop Sky Bar", "On-site Spa & Sauna", "24/7 Front Desk"],
        room_type="Standard Double Bed",
        source="Mock Hospitality Catalog [DEMO_DATA]",
        availability_status="Demo Available (6 rooms remaining)",
        demo_data=True,
    )

    return [hotel_1, hotel_2]


def hotel_agent_node(state: TravelState) -> Dict[str, Any]:
    """LangGraph node executing Hotel Agent reasoning through the Hotel MCP gateway."""
    def _action() -> Dict[str, Any]:
        destination = state.get("destination") or "Tokyo"
        start_date = str(state.get("start_date") or "2026-11-01")[:10]
        end_date = str(state.get("end_date") or "2026-11-06")[:10]
        duration = int(state.get("duration") or 5)
        travelers = max(int(state.get("travelers") or 1), 1)
        currency = str(state.get("currency") or "USD").upper()
        budget = float(state.get("budget")) if state.get("budget") is not None else None
        pref = state.get("accommodation_preference") or "Hotel"
        is_demo = state.get("is_demo", True)

        tool_calls: List[Dict[str, Any]] = []

        fallback_hotels = generate_mock_hotels(
            destination=destination,
            duration=duration,
            travelers=travelers,
            currency=currency,
            preference=pref,
        )

        # Invoke Hotel MCP: search_hotels
        search_res = MCPClient.call_tool(
            agent_name="hotel",
            tool_name="search_hotels",
            arguments={
                "destination": destination,
                "check_in": start_date,
                "check_out": end_date,
                "travellers": travelers,
                "rooms": 1,
                "budget": budget,
                "currency": currency,
                "preferences": [pref],
            },
            is_demo=is_demo,
        )

        if not search_res.success or not search_res.data:
            err_msg = search_res.error.message if search_res.error else "Hotel search failed"
            tool_calls.append({
                "tool_name": "search_hotels",
                "agent": "hotel",
                "status": "FAILED",
                "error": err_msg,
                "mode": search_res.mode,
            })
            hotels = [h.model_dump() for h in fallback_hotels]
        else:
            hotels = search_res.data.get("hotels", [])
            if not hotels:
                hotels = [h.model_dump() for h in fallback_hotels]
            tool_calls.append({
                "tool_name": "search_hotels",
                "agent": "hotel",
                "status": "SUCCESS",
                "latency_ms": search_res.latency_ms,
                "mode": search_res.mode,
                "items_returned": len(hotels),
            })

        return {
            "hotel_options": hotels,
            "tool_calls": tool_calls,
        }

    delta, run_record = execute_agent_safely(
        agent_name="hotel",
        action=_action,
        step=state.get("graph_step_count", 1) + 1,
        is_demo=state.get("is_demo", True),
    )
    delta["agent_runs"] = [run_record]
    return delta
