"""Flight Agent specializing in flight discovery and schedule evaluation using mock data."""

from typing import Dict, Any, List
from graph.state import TravelState
from models.specialized_options import FlightOption
from agents.base_agent import execute_agent_safely


def generate_mock_flights(
    origin: str,
    destination: str,
    start_date: str,
    travelers: int = 1,
    currency: str = "USD",
) -> List[FlightOption]:
    """Generate deterministic mock flight candidates matching route and party size."""
    orig = origin or "SFO"
    dest = destination or "Tokyo"
    s_date = start_date or "2026-11-01"
    trav = max(1, travelers or 1)
    curr = currency or "USD"

    # Route-aware mock airline mapping
    dest_lower = dest.lower()
    if "tokyo" in dest_lower or "japan" in dest_lower:
        airline_a, code_a = "All Nippon Airways (ANA)", "NH"
        airline_b, code_b = "Japan Airlines (JAL)", "JL"
    elif "london" in dest_lower or "uk" in dest_lower or "britain" in dest_lower:
        airline_a, code_a = "British Airways", "BA"
        airline_b, code_b = "Virgin Atlantic", "VS"
    elif "paris" in dest_lower or "france" in dest_lower:
        airline_a, code_a = "Air France", "AF"
        airline_b, code_b = "Delta Air Lines", "DL"
    elif "delhi" in dest_lower or "india" in dest_lower:
        airline_a, code_a = "Air India", "AI"
        airline_b, code_b = "IndiGo Global", "6E"
    else:
        airline_a, code_a = "Global Airways", "GA"
        airline_b, code_b = "Skyline Express", "SE"

    # Base pricing per passenger
    base_price_nonstop = 850.0 if curr == "USD" else (70000.0 if curr == "INR" else 780.0)
    base_price_layover = 620.0 if curr == "USD" else (52000.0 if curr == "INR" else 580.0)

    option_1 = FlightOption(
        airline=airline_a,
        flight_number=f"{code_a}-108",
        departure_airport=f"{orig.upper()[:3]} Terminal 2",
        arrival_airport=f"{dest.upper()[:3]} Int'l",
        departure_time=f"{s_date} 10:45",
        arrival_time=f"{s_date} 15:30 (+1)",
        duration="10h 45m",
        stops=0,
        cabin_class="Economy",
        price=round(base_price_nonstop * trav, 2),
        currency=curr,
        source="Mock Flight Catalog [DEMO_DATA]",
        availability_status="Demo Available (9 seats)",
        demo_data=True,
    )

    option_2 = FlightOption(
        airline=airline_b,
        flight_number=f"{code_b}-402",
        departure_airport=f"{orig.upper()[:3]} Terminal 1",
        arrival_airport=f"{dest.upper()[:3]} Int'l",
        departure_time=f"{s_date} 14:15",
        arrival_time=f"{s_date} 21:00 (+1)",
        duration="13h 15m",
        stops=1,
        cabin_class="Economy",
        price=round(base_price_layover * trav, 2),
        currency=curr,
        source="Mock Flight Catalog [DEMO_DATA]",
        availability_status="Demo Available (4 seats)",
        demo_data=True,
    )

    return [option_1, option_2]


def flight_agent_node(state: TravelState) -> Dict[str, Any]:
    """LangGraph node executing Flight Agent logic."""
    def _action() -> Dict[str, Any]:
        origin = state.get("origin") or "Origin City"
        destination = state.get("destination") or "Destination City"
        start_date = state.get("start_date") or "2026-11-01"
        travelers = state.get("travelers") or 1
        currency = state.get("currency") or "USD"

        flights = generate_mock_flights(
            origin=origin,
            destination=destination,
            start_date=start_date,
            travelers=travelers,
            currency=currency,
        )
        return {
            "flight_options": [f.model_dump() for f in flights],
        }

    delta, run_record = execute_agent_safely(
        agent_name="flight",
        action=_action,
        step=state.get("graph_step_count", 1) + 1,
        is_demo=True,
    )
    delta["agent_runs"] = [run_record]
    return delta
