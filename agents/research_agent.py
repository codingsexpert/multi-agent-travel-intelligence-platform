"""Research Agent synthesizing cultural etiquette, tips, and destination intelligence via Search MCP Server."""

from typing import Dict, Any, List
from graph.state import TravelState, WorkflowStatus
from models.specialized_options import DestinationResearch
from models.rag import RAGRetrievalQuery
from rag.retriever import travel_knowledge_retriever
from mcp.client import MCPClient
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
    """LangGraph node executing Research Agent reasoning through Search MCP tools."""
    def _action() -> Dict[str, Any]:
        destination = state.get("destination") or "Tokyo"
        is_demo = state.get("is_demo", True)

        tool_calls: List[Dict[str, Any]] = []

        # 1. RAG Knowledge Retrieval: Curated cultural norms, etiquette & tips
        rag_query = RAGRetrievalQuery(
            query=f"{destination} customs etiquette tips cultural norms rules",
            destination=destination,
            category="customs",
            top_k=3,
        )
        rag_res = travel_knowledge_retriever.retrieve(rag_query)

        rag_telemetry: Dict[str, Any] = {
            "agent_name": "research",
            "query": rag_query.query,
            "destination": destination,
            "chunks_retrieved": len(rag_res.results),
            "top_score": rag_res.top_score,
            "sources_count": len(rag_res.sources),
            "mode": rag_res.mode,
            "latency_ms": rag_res.latency_ms,
        }

        tool_calls.append({
            "tool_name": "rag_knowledge_retrieval",
            "agent": "research",
            "status": "SUCCESS" if rag_res.results else "EMPTY",
            "latency_ms": rag_res.latency_ms,
            "mode": rag_res.mode,
            "details": f"{len(rag_res.results)} curated chunks retrieved (top score: {rag_res.top_score})",
        })

        # 2. Invoke Search MCP: web_search
        search_res = MCPClient.call_tool(
            agent_name="research",
            tool_name="web_search",
            arguments={"query": f"{destination} travel etiquette customs safety", "max_results": 3},
            is_demo=is_demo,
        )

        sources = ["[DEMO_DATA] Search MCP Server (Mock Web Index)"]
        # Include verified RAG sources without fabricating URLs
        for s in rag_res.sources:
            if s not in sources:
                sources.append(s)

        if search_res.success and search_res.data:
            tool_calls.append({
                "tool_name": "web_search",
                "agent": "research",
                "status": "SUCCESS",
                "latency_ms": search_res.latency_ms,
                "mode": search_res.mode,
            })
            for item in search_res.data.get("results", []):
                if item.get("url"):
                    sources.append(item["url"])

        # 3. Invoke Search MCP: search_news
        news_res = MCPClient.call_tool(
            agent_name="research",
            tool_name="search_news",
            arguments={"query": destination, "limit": 2},
            is_demo=is_demo,
        )
        if news_res.success and news_res.data:
            tool_calls.append({
                "tool_name": "search_news",
                "agent": "research",
                "status": "SUCCESS",
                "latency_ms": news_res.latency_ms,
                "mode": news_res.mode,
            })

        dest_lower = destination.lower()
        if "tokyo" in dest_lower or "japan" in dest_lower:
            overview = (
                "Tokyo is an electrifying metropolis blending futuristic architecture, seamless mass transit, "
                "and deeply revered historic sanctuaries. Renowned for culinary mastery and omotenashi hospitality."
            )
            cultural = [
                "Tipping is not customary in Japan and can cause confusion; service is built into pricing.",
                "Bow slightly when greeting or expressing gratitude; 'Arigato gozaimasu' is polite.",
                "Remove shoes when entering traditional tatami accommodations, tea houses, and ryokans.",
            ]
            tips = [
                "Acquire a mobile IC Card (Suica/Pasmo) for seamless tap-and-go rides on all subway lines.",
                "Carry a modest cash reserve for traditional ramen stalls, temples, and small markets.",
                "Subway trains cease operations around midnight; plan evening returns accordingly.",
            ]
            customs = [
                "Avoid walking while consuming food or beverages on busy streets.",
                "Keep voice volume low on public transport; phone calls are prohibited inside carriages.",
                "Public trash receptacles are rare; carry a small pouch for personal litter.",
            ]
            notes = [
                "Passport must be carried at all times by foreign visitors per immigration regulations.",
                "Emergency lines: 110 (Police), 119 (Medical & Fire).",
            ]
        elif "paris" in dest_lower or "france" in dest_lower:
            overview = (
                "Paris, the City of Light, is a world capital of art, gastronomy, and cultural heritage, "
                "organized across 20 distinct arrondissements along the scenic River Seine."
            )
            cultural = [
                "Always initiate interactions with shopkeepers and waitstaff with 'Bonjour Madame/Monsieur'.",
                "Dining is an unhurried cultural ritual; request the bill explicitly ('L'addition, s'il vous plaît').",
                "Casual-chic attire is standard; avoid overly informal athletic wear in evening bistros.",
            ]
            tips = [
                "Utilize the Metro with the Île-de-France Mobilités digital pass for rapid travel.",
                "Reserve Louvre and Eiffel Tower slots at least 2-3 weeks in advance.",
                "Tap water ('une carafe d'eau') is free, chilled, and standard in all restaurants.",
            ]
            customs = [
                "Keep voices low and conversational in cafes, bistros, and public transit.",
                "Be attentive to personal belongings around tourist landmarks and transport hubs.",
            ]
            notes = [
                "Universal European emergency telephone number: 112.",
            ]
        else:
            overview = (
                f"{destination.title()} is a celebrated travel destination featuring distinctive cultural heritage, "
                f"vibrant neighborhood markets, and iconic landmarks."
            )
            cultural = [
                f"Observe local customs and dress codes when visiting historical and sacred sites in {destination.title()}.",
                "A polite greeting in the native tongue is warmly welcomed by local hosts.",
            ]
            tips = [
                "Download offline mapping applications before arrival for reliable offline orientation.",
                "Confirm local card acceptance policies and maintain modest cash reserves.",
            ]
            customs = [
                "Respect local dining norms and tipping conventions.",
                "Request permission before photographing residents or private vendors.",
            ]
            notes = [
                f"Verify visa entry requirements for travel to {destination.title()}.",
                "International emergency telephone number: 112.",
            ]

        research_model = DestinationResearch(
            destination=destination.title(),
            destination_overview=overview,
            cultural_notes=cultural,
            travel_tips=tips,
            local_customs=customs,
            important_notes=notes,
            sources=sources,
            demo_data=True,
        )

        prior_runs = state.get("agent_runs", [])
        has_failure = any(r.get("status") == "FAILED" for r in prior_runs)

        return {
            "research_results": research_model.model_dump(),
            "planning_status": WorkflowStatus.PARTIAL_RESULTS.value if has_failure else WorkflowStatus.READY_FOR_VALIDATION.value,
            "tool_calls": tool_calls,
            "rag_retrievals": [rag_telemetry],
        }

    delta, run_record = execute_agent_safely(
        agent_name="research",
        action=_action,
        step=state.get("graph_step_count", 1) + 2,
        is_demo=state.get("is_demo", True),
    )
    delta["agent_runs"] = [run_record]
    return delta
