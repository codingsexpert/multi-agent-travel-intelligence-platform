"""Research Agent synthesizing cultural etiquette, logistical tips, and destination context using mock data."""

from typing import Dict, Any, List
from graph.state import TravelState, WorkflowStatus
from models.specialized_options import DestinationResearch
from agents.base_agent import execute_agent_safely


def generate_mock_research(destination: str) -> DestinationResearch:
    """Generate deterministic destination research, cultural norms, and local customs."""
    dest = destination or "Tokyo"
    dest_lower = dest.lower()

    if "tokyo" in dest_lower or "japan" in dest_lower:
        overview = (
            "Tokyo is an electrifying metropolis blending futuristic architecture, seamless mass transit, "
            "and deeply revered historic sanctuaries. Renowned for culinary mastery, hyper-cleanliness, and extraordinary hospitality (omotenashi)."
        )
        cultural = [
            "Tipping is not customary in Japan and can cause confusion; exceptional service is considered standard.",
            "Bow slightly when greeting or expressing gratitude; a polite 'Arigato gozaimasu' is widely appreciated.",
            "Remove your shoes when entering traditional accommodations, tea houses, and ryokans.",
        ]
        tips = [
            "Get an IC Card (Suica or Pasmo on your phone) for seamless tap-and-go rides on all subway lines.",
            "Cash is still king at many small ramen shops, temple souvenir stands, and vending machines.",
            "Trains stop running around midnight; plan late-night departures or use registered taxis.",
        ]
        customs = [
            "Avoid walking while eating or drinking on busy public streets; consume food near the vendor.",
            "Keep voice volume low on trains and subways; phone calls are strictly discouraged inside carriages.",
            "Trash bins are rare in public areas; carry a small bag to pack out personal waste.",
        ]
        notes = [
            "Passport must be carried at all times by foreign visitors per Japanese immigration law.",
            "Emergency numbers: 110 (Police), 119 (Fire & Ambulance).",
        ]
    elif "paris" in dest_lower or "france" in dest_lower:
        overview = (
            "Paris, the City of Light, is a global epicenter of art, fashion, gastronomy, and architectural heritage. "
            "Structured around 20 spiraling arrondissements along the scenic River Seine."
        )
        cultural = [
            "Always greet shopkeepers and servers with 'Bonjour Madame/Monsieur' before asking questions.",
            "Dining is a relaxed, leisurely ritual; request the bill explicitly ('L'addition, s'il vous plaît').",
            "Dress neatly in casual-chic attire to blend in seamlessly with locals.",
        ]
        tips = [
            "Use the Metro with the Île-de-France Mobilités app or Navigo Easy pass for rapid citywide transit.",
            "Book Louvre, Eiffel Tower, and Musée d'Orsay tickets 3-4 weeks in advance to avoid long lines.",
            "Tap water ('une carafe d'eau') is free, pristine, and customary in all dining establishments.",
        ]
        customs = [
            "Speak at moderate volumes in cafes, metros, and bistros.",
            "Greet acquaintances with 'la bise' (two cheek air-kisses) in social gatherings.",
        ]
        notes = [
            "Emergency number: 112 (European universal emergency line).",
            "Be vigilant of pickpockets around major tourist landmarks and Metro stations.",
        ]
    else:
        overview = (
            f"{dest.title()} is a celebrated travel destination featuring distinctive cultural heritage, "
            f"vibrant neighborhood markets, and iconic landmarks."
        )
        cultural = [
            f"Respect local traditions, historic sites, and dress codes when visiting sacred places in {dest.title()}.",
            "A friendly greeting in the native language always fosters warm local interactions.",
        ]
        tips = [
            "Download offline maps before arrival to navigate comfortably without active data.",
            "Check local bank card acceptance; keep a nominal cash reserve for small markets.",
        ]
        customs = [
            "Observe local dining and tipping norms practiced across the region.",
            "Ask permission before photographing residents or private market stalls.",
        ]
        notes = [
            f"Review standard visa and health entry requirements for travel to {dest.title()}.",
            "Universal international emergency number: 112.",
        ]

    return DestinationResearch(
        destination=dest.title(),
        destination_overview=overview,
        cultural_notes=cultural,
        travel_tips=tips,
        local_customs=customs,
        important_notes=notes,
        sources=["Mock Destination Knowledge Graph [DEMO_DATA]", "Global Travel Standards Index"],
        demo_data=True,
    )


def research_agent_node(state: TravelState) -> Dict[str, Any]:
    """LangGraph node executing Research Agent logic and assessing overall multi-agent completion."""
    def _action() -> Dict[str, Any]:
        destination = state.get("destination") or "Destination City"
        research_data = generate_mock_research(destination=destination)

        # Inspect execution status across prior agent runs
        prior_runs = state.get("agent_runs", [])
        has_failure = any(r.get("status") == "FAILED" for r in prior_runs)

        final_status = (
            WorkflowStatus.PARTIAL_RESULTS.value
            if has_failure
            else WorkflowStatus.READY_FOR_VALIDATION.value
        )

        return {
            "research_results": research_data.model_dump(),
            "planning_status": final_status,
        }

    delta, run_record = execute_agent_safely(
        agent_name="research",
        action=_action,
        step=state.get("graph_step_count", 1) + 2,
        is_demo=True,
    )
    delta["agent_runs"] = [run_record]
    return delta
