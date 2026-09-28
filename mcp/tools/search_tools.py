"""Search MCP tools delegating to the Search Provider adapter."""

from models.mcp import (
    WebSearchInput,
    WebSearchOutput,
    FetchPageInput,
    FetchPageOutput,
    SearchNewsInput,
    SearchNewsOutput,
)
from mcp.providers.search_provider import search_provider


def mcp_web_search(params: WebSearchInput) -> WebSearchOutput:
    """Execute external search returning snippets sanitized and tagged as untrusted third-party data."""
    return search_provider.web_search(
        query=params.query,
        destination=params.destination,
        recency=params.recency,
        language=params.language,
        max_results=params.max_results,
        allowed_domains=params.allowed_domains,
    )


def mcp_fetch_page(params: FetchPageInput) -> FetchPageOutput:
    """Fetch text from a validated web URL under strict sandboxing and sanitization rules."""
    return search_provider.fetch_page(
        url=params.url,
        max_length=params.max_length,
    )


def mcp_search_news(params: SearchNewsInput) -> SearchNewsOutput:
    """Discover seasonal events, cultural festivals, disruptions, and regional travel news."""
    return search_provider.search_news(
        query=params.query,
        destination=params.destination,
        recency=params.recency,
        limit=params.limit,
    )
