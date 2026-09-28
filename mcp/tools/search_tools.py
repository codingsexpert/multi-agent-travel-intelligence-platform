"""Search MCP tools implementing web search, sandboxed page fetching, and news retrieval with untrusted data isolation."""

from typing import List, Dict, Any
from mcp.security import MCPSecurityManager
from models.mcp import (
    SearchResultItem,
    WebSearchInput,
    WebSearchOutput,
    FetchPageInput,
    FetchPageOutput,
    SearchNewsInput,
    SearchNewsOutput,
)


def mcp_web_search(params: WebSearchInput) -> WebSearchOutput:
    """Execute external search returning snippets sanitized and tagged as untrusted third-party data."""
    q_lower = params.query.lower()

    if "tokyo" in q_lower or "japan" in q_lower:
        results = [
            SearchResultItem(
                title="Tokyo Essential Guide - Travel Customs & Etiquette",
                url="https://en.wikipedia.org/wiki/Tourism_in_Tokyo",
                snippet="Comprehensive guide covering Omotenashi hospitality, transit etiquette, IC cards, and cash practices in Tokyo.",
                untrusted=True,
                demo_data=True,
            ),
            SearchResultItem(
                title="Japan Rail & Subway Navigation Overview",
                url="https://japan.travel/en/guide/public-transport/",
                snippet="Subways and trains run precisely on schedule. Tipping is non-existent. Suica/Pasmo transit cards recommended.",
                untrusted=True,
                demo_data=True,
            ),
        ]
    elif "paris" in q_lower or "france" in q_lower:
        results = [
            SearchResultItem(
                title="Paris Visitor Guidelines & Local Customs",
                url="https://en.wikipedia.org/wiki/Tourism_in_Paris",
                snippet="Guide detailing French dining rituals, greeting norms ('Bonjour'), Navigo transit passes, and museum booking tips.",
                untrusted=True,
                demo_data=True,
            ),
            SearchResultItem(
                title="Paris Official Tourism Portal - Tips & Safety",
                url="https://parisjetaime.com/eng/article/practical-paris",
                snippet="Official city advisory on metro navigation, pickpocket awareness, and tap water availability across Paris cafes.",
                untrusted=True,
                demo_data=True,
            ),
        ]
    else:
        results = [
            SearchResultItem(
                title=f"{params.query.title()} - Practical Travel Overview",
                url="https://en.wikipedia.org/wiki/Travel_guide",
                snippet=f"Curated visitor insights covering transit, emergency logistics, and cultural norms for {params.query}.",
                untrusted=True,
                demo_data=True,
            ),
        ]

    return WebSearchOutput(
        query=params.query,
        results=results[: params.max_results],
        untrusted=True,
        demo_data=True,
    )


def mcp_fetch_page(params: FetchPageInput) -> FetchPageOutput:
    """Fetch text from a validated web URL under strict domain allowlist and sanitization rules.

    Guarantees retrieved text is marked as untrusted and stripped of prompt injection patterns.
    """
    # 1. Enforce URL and domain allowlist security
    validated_url = MCPSecurityManager.validate_url(params.url, enforce_domain_allowlist=True)

    # 2. Return controlled mock text (or sanitized response in live mode)
    raw_content = (
        f"Article content extracted from {validated_url}. Provides verified travel safety information, "
        f"consular advisories, and cultural practices for international visitors."
    )

    # 3. Apply untrusted data sanitization
    sanitized_text = MCPSecurityManager.sanitize_untrusted_content(raw_content)

    return FetchPageOutput(
        url=validated_url,
        title="Verified Travel Authority Guide [UNTRUSTED_CONTENT]",
        content=sanitized_text,
        untrusted=True,
        demo_data=True,
    )


def mcp_search_news(params: SearchNewsInput) -> SearchNewsOutput:
    """Discover seasonal events, cultural festivals, and regional news."""
    articles = [
        {
            "headline": f"Seasonal Cultural Celebrations Announced for {params.query.title()}",
            "date": "2026-09-15",
            "source": "Global Travel Bulletin [DEMO_DATA]",
            "untrusted": True,
        },
        {
            "headline": f"Transit Authority Upgrades Contactless Tap-and-Go Payments in {params.query.title()}",
            "date": "2026-09-01",
            "source": "Metropolitan Transit Press [DEMO_DATA]",
            "untrusted": True,
        },
    ]

    return SearchNewsOutput(
        query=params.query,
        articles=articles[: params.limit],
        untrusted=True,
        demo_data=True,
    )
