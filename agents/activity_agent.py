"""Activity Agent curating local experiences and points of interest via Maps MCP Server."""

from typing import Dict, Any, List
from graph.state import TravelState
from models.specialized_options import ActivityOption
from models.rag import RAGRetrievalQuery
from rag.retriever import travel_knowledge_retriever
from mcp.client import MCPClient
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
    """LangGraph node executing Activity Agent reasoning through Maps MCP tools."""
    def _action() -> Dict[str, Any]:
        destination = state.get("destination") or "Tokyo"
        interests = state.get("interests") or ["Culture"]
        currency = str(state.get("currency") or "USD").upper()
        is_demo = state.get("is_demo", True)

        tool_calls: List[Dict[str, Any]] = []

        fallback_acts = generate_mock_activities(
            destination=destination,
            interests=interests,
            currency=currency,
        )

        # 1. RAG Knowledge Retrieval: Curated cultural & attraction intelligence
        rag_query = RAGRetrievalQuery(
            query=f"{destination} historic landmarks cultural attractions experiences",
            destination=destination,
            category="attractions",
            top_k=3,
        )
        rag_res = travel_knowledge_retriever.retrieve(rag_query)

        rag_telemetry: Dict[str, Any] = {
            "agent_name": "activity",
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
            "agent": "activity",
            "status": "SUCCESS" if rag_res.results else "EMPTY",
            "latency_ms": rag_res.latency_ms,
            "mode": rag_res.mode,
            "details": f"{len(rag_res.results)} curated chunks retrieved (top score: {rag_res.top_score})",
        })

        # 2. Invoke Maps MCP: search_places
        places_res = MCPClient.call_tool(
            agent_name="activity",
            tool_name="search_places",
            arguments={
                "query": "historic landmarks, cultural sites & museums",
                "location": destination,
                "limit": 4,
            },
            is_demo=is_demo,
        )

        activities: List[Dict[str, Any]] = []

        if places_res.success and places_res.data:
            tool_calls.append({
                "tool_name": "search_places",
                "agent": "activity",
                "status": "SUCCESS",
                "latency_ms": places_res.latency_ms,
                "mode": places_res.mode,
            })

            places = places_res.data.get("places", [])
            for idx, p in enumerate(places):
                # 3. Invoke Maps MCP: estimate_travel_time
                tt_res = MCPClient.call_tool(
                    agent_name="activity",
                    tool_name="estimate_travel_time",
                    arguments={
                        "origin": f"{destination} City Center",
                        "destination": p.get("location", destination),
                        "mode": "transit",
                    },
                    is_demo=is_demo,
                )
                if tt_res.success and tt_res.data:
                    tool_calls.append({
                        "tool_name": "estimate_travel_time",
                        "agent": "activity",
                        "status": "SUCCESS",
                        "latency_ms": tt_res.latency_ms,
                        "mode": tt_res.mode,
                    })

                slot = "Morning (09:30 - 12:00)" if idx % 2 == 0 else "Afternoon (14:00 - 16:30)"
                cost = 25.0 if currency == "USD" else (2000.0 if currency == "INR" else 22.0)
                if idx == 0:
                    cost = 0.0

                desc = f"Curated experience in {destination} featuring authentic architecture and cultural heritage."
                source_label = "[DEMO_DATA] Maps MCP Server (Mock Places Directory)"
                if rag_res.results:
                    # Enrich with top curated RAG chunk context
                    matching_chunk = rag_res.results[idx % len(rag_res.results)]
                    desc = f"{matching_chunk.content[:160]}..."
                    source_label = matching_chunk.citation_str

                activities.append(
                    ActivityOption(
                        name=p.get("name", f"{destination} Heritage Site"),
                        location=p.get("location", destination),
                        category=p.get("category", "Culture & Heritage"),
                        duration=f"{p.get('estimated_time_spent_hours', 2.0)} hours",
                        estimated_cost=cost,
                        currency=currency,
                        best_time=slot,
                        description=desc,
                        source=source_label,
                        demo_data=True,
                    ).model_dump()
                )
        else:
            err_msg = places_res.error.message if places_res.error else "Place search failed"
            tool_calls.append({
                "tool_name": "search_places",
                "agent": "activity",
                "status": "FAILED",
                "error": err_msg,
                "mode": places_res.mode,
            })
            activities = [a.model_dump() for a in fallback_acts]

        if len(activities) < 3:
            for fallback_item in fallback_acts:
                if not any(a["name"] == fallback_item.name for a in activities):
                    activities.append(fallback_item.model_dump())

        return {
            "activities": activities,
            "tool_calls": tool_calls,
            "rag_retrievals": [rag_telemetry],
        }

    delta, run_record = execute_agent_safely(
        agent_name="activity",
        action=_action,
        step=state.get("graph_step_count", 1) + 1,
        is_demo=state.get("is_demo", True),
    )
    delta["agent_runs"] = [run_record]
    return delta
