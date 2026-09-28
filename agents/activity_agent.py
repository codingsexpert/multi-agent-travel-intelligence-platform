"""Activity Agent specializing in experience curation and point-of-interest discovery using mock data."""

from typing import Dict, Any, List
from graph.state import TravelState
from models.specialized_options import ActivityOption
from agents.base_agent import execute_agent_safely


def generate_mock_activities(
    destination: str,
    interests: List[str],
    currency: str = "USD",
) -> List[ActivityOption]:
    """Generate deterministic mock activities matching destination and personal interests."""
    dest = destination or "Tokyo"
    curr = currency or "USD"
    dest_lower = dest.lower()
    items: List[ActivityOption] = []

    cost_low = 25.0 if curr == "USD" else (2000.0 if curr == "INR" else 22.0)
    cost_med = 65.0 if curr == "USD" else (5000.0 if curr == "INR" else 60.0)
    cost_free = 0.0

    if "tokyo" in dest_lower or "japan" in dest_lower:
        items.append(
            ActivityOption(
                name="Senso-ji Temple & Asakusa Historic Quarter Walking Tour",
                location="Asakusa, Tokyo",
                category="Culture & Heritage",
                duration="2.5 hours",
                estimated_cost=cost_low,
                currency=curr,
                best_time="Morning",
                description="Explore Tokyo's oldest temple, stroll Nakamise-dori market, and experience traditional incense rituals.",
                source="Mock Experiences Catalog [DEMO_DATA]",
                demo_data=True,
            )
        )
        items.append(
            ActivityOption(
                name="Tsukiji Outer Market Culinary & Street Food Tasting",
                location="Tsukiji, Tokyo",
                category="Culinary & Dining",
                duration="3 hours",
                estimated_cost=cost_med,
                currency=curr,
                best_time="Early Morning",
                description="Taste fresh sushi, tamagoyaki, wagyu skewers, and matcha alongside an expert local guide.",
                source="Mock Experiences Catalog [DEMO_DATA]",
                demo_data=True,
            )
        )
        items.append(
            ActivityOption(
                name="teamLab Planets Immersive Digital Art Museum",
                location="Toyosu, Tokyo",
                category="Art & Modern Culture",
                duration="2 hours",
                estimated_cost=cost_low,
                currency=curr,
                best_time="Afternoon",
                description="Walk through water and interactive projection rooms in a world-renowned sensory digital art space.",
                source="Mock Experiences Catalog [DEMO_DATA]",
                demo_data=True,
            )
        )
        items.append(
            ActivityOption(
                name="Shinjuku Gyoen National Garden & Botanical Exploration",
                location="Shinjuku, Tokyo",
                category="Nature & Gardens",
                duration="2 hours",
                estimated_cost=5.0 if curr == "USD" else 400.0,
                currency=curr,
                best_time="Late Morning",
                description="Pristine landscape garden combining traditional Japanese, English landscape, and French formal styles.",
                source="Mock Experiences Catalog [DEMO_DATA]",
                demo_data=True,
            )
        )
    elif "paris" in dest_lower or "france" in dest_lower:
        items.append(
            ActivityOption(
                name="Louvre Museum Masterpieces Guided Walking Tour",
                location="1st Arrondissement, Paris",
                category="Art & History",
                duration="3 hours",
                estimated_cost=cost_med,
                currency=curr,
                best_time="Morning",
                description="Priority entry to see the Mona Lisa, Winged Victory, and Venus de Milo with an art historian.",
                source="Mock Experiences Catalog [DEMO_DATA]",
                demo_data=True,
            )
        )
        items.append(
            ActivityOption(
                name="Seine River Sunset Architectural Cruise",
                location="Pont Neuf, Paris",
                category="Sightseeing & Leisure",
                duration="1.5 hours",
                estimated_cost=cost_low,
                currency=curr,
                best_time="Sunset",
                description="Gliding past Notre-Dame, the Musée d'Orsay, and the sparkling Eiffel Tower at dusk.",
                source="Mock Experiences Catalog [DEMO_DATA]",
                demo_data=True,
            )
        )
    else:
        items.append(
            ActivityOption(
                name=f"Historic {dest.title()} City Center Heritage Walk",
                location=f"Old Town, {dest.title()}",
                category="Culture & Heritage",
                duration="2.5 hours",
                estimated_cost=cost_low,
                currency=curr,
                best_time="Morning",
                description=f"Discover iconic landmarks, architecture, and hidden courtyards across historic {dest.title()}.",
                source="Mock Experiences Catalog [DEMO_DATA]",
                demo_data=True,
            )
        )
        items.append(
            ActivityOption(
                name=f"{dest.title()} Street Food & Local Market Safari",
                location=f"Central Market, {dest.title()}",
                category="Culinary & Dining",
                duration="2 hours",
                estimated_cost=cost_med,
                currency=curr,
                best_time="Evening",
                description=f"Sample regional delicacies, street food stalls, and artisanal treats unique to {dest.title()}.",
                source="Mock Experiences Catalog [DEMO_DATA]",
                demo_data=True,
            )
        )

    return items


def activity_agent_node(state: TravelState) -> Dict[str, Any]:
    """LangGraph node executing Activity Agent logic."""
    def _action() -> Dict[str, Any]:
        destination = state.get("destination") or "Destination City"
        interests = state.get("interests") or []
        currency = state.get("currency") or "USD"

        activities = generate_mock_activities(
            destination=destination,
            interests=interests,
            currency=currency,
        )
        return {
            "activities": [a.model_dump() for a in activities],
        }

    delta, run_record = execute_agent_safely(
        agent_name="activity",
        action=_action,
        step=state.get("graph_step_count", 1) + 1,
        is_demo=True,
    )
    delta["agent_runs"] = [run_record]
    return delta
