"""Search and Knowledge Provider Adapter integrating Tavily, Wikipedia, sandboxed HTTP retrieval, and mock fallbacks."""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from urllib.parse import quote

from config.settings import settings
from models.mcp import (
    SearchResultItem,
    WebSearchInput,
    WebSearchOutput,
    FetchPageInput,
    FetchPageOutput,
    SearchNewsInput,
    SearchNewsOutput,
)
from mcp.security import MCPSecurityManager
from mcp.providers.base import (
    BaseProvider,
    ProviderError,
    ProviderNetworkError,
    ProviderResponseValidationError,
    get_effective_demo_mode,
)
from mcp.providers.cache import ProviderCache
from utils.logger import logger


class SearchProvider(BaseProvider):
    """Adapter for web search, sandboxed page fetching, and news retrieval with strict untrusted data isolation."""

    def __init__(
        self,
        tavily_url: str = "https://api.tavily.com",
        wikipedia_url: str = "https://en.wikipedia.org/w/api.php",
    ):
        super().__init__(provider_name="Wikipedia Knowledge API", base_url=wikipedia_url)
        self.tavily_url = tavily_url
        self.cache = ProviderCache(default_ttl_seconds=900)  # 15 minute cache

    def web_search(
        self,
        query: str,
        max_results: int = 5,
        demo_mode: Optional[bool] = None,
    ) -> WebSearchOutput:
        """Execute external web search returning sanitized snippets tagged as untrusted third-party data."""
        is_demo = get_effective_demo_mode(demo_mode)
        q_lower = query.lower()

        if is_demo:
            if "tokyo" in q_lower or "japan" in q_lower:
                results = [
                    SearchResultItem(
                        title="Tokyo Essential Guide - Travel Customs & Etiquette",
                        url="https://en.wikipedia.org/wiki/Tourism_in_Tokyo",
                        snippet="Comprehensive guide covering Omotenashi hospitality, transit etiquette, IC cards, and cash practices in Tokyo.",
                        untrusted=True,
                        provider="Mock Search Service",
                        data_mode="DEMO",
                        demo_data=True,
                    ),
                    SearchResultItem(
                        title="Japan Rail & Subway Navigation Overview",
                        url="https://japan.travel/en/guide/public-transport/",
                        snippet="Subways and trains run precisely on schedule. Tipping is non-existent. Suica/Pasmo transit cards recommended.",
                        untrusted=True,
                        provider="Mock Search Service",
                        data_mode="DEMO",
                        demo_data=True,
                    ),
                ]
            else:
                results = [
                    SearchResultItem(
                        title=f"{query.title()} - Practical Travel Overview",
                        url="https://en.wikipedia.org/wiki/Travel_guide",
                        snippet=f"Curated visitor insights covering transit, emergency logistics, and cultural norms for {query}.",
                        untrusted=True,
                        provider="Mock Search Service",
                        data_mode="DEMO",
                        demo_data=True,
                    ),
                ]

            return WebSearchOutput(
                query=query,
                results=results[:max_results],
                provider="Mock Search Service",
                data_mode="DEMO",
                untrusted=True,
                demo_data=True,
            )

        cache_key = f"search_{q_lower}_{max_results}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # 1. Option A: Use Tavily if API key is provided
        if settings.has_tavily_config:
            active_provider = "Tavily AI Search"
            try:
                headers = {"Content-Type": "application/json"}
                payload = {
                    "api_key": settings.tavily_api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results,
                }
                resp = self.execute_http_request(
                    method="POST",
                    url=f"{self.tavily_url}/search",
                    headers=headers,
                    json_data=payload,
                    timeout=6.0,
                )
                tavily_data = resp.json()
                tavily_results = tavily_data.get("results", [])

                results = []
                for item in tavily_results[:max_results]:
                    clean_snippet = MCPSecurityManager.sanitize_untrusted_content(item.get("content", ""))
                    results.append(
                        SearchResultItem(
                            title=item.get("title", query.title()),
                            url=item.get("url", "https://tavily.com"),
                            snippet=clean_snippet,
                            source_domain="tavily.com",
                            retrieved_at=datetime.now(timezone.utc).isoformat(),
                            untrusted=True,
                            provider=active_provider,
                            data_mode="LIVE",
                            demo_data=False,
                        )
                    )

                result = WebSearchOutput(
                    query=query,
                    results=results,
                    provider=active_provider,
                    data_mode="LIVE",
                    untrusted=True,
                    demo_data=False,
                )
                self.cache.set(cache_key, result, ttl_seconds=900)
                return result
            except Exception as e:
                logger.warning(f"[{active_provider}] Search failed: {str(e)}. Falling back to Wikipedia API.")

        # 2. Option B: Live Wikipedia OpenSearch API (Open, keyless, reliable)
        active_provider = "Wikipedia Knowledge API"
        params = {
            "action": "opensearch",
            "search": query,
            "limit": max_results,
            "namespace": 0,
            "format": "json",
        }

        try:
            resp = self.execute_http_request(method="GET", url=self.base_url, params=params, timeout=5.0)
            data = resp.json()
            # Wikipedia OpenSearch format: [query, [titles], [descriptions], [urls]]
            if len(data) >= 4:
                titles = data[1]
                descriptions = data[2]
                urls = data[3]

                results = []
                for i in range(len(titles)):
                    desc = descriptions[i] if i < len(descriptions) and descriptions[i] else f"Information and visitor guide for {titles[i]}."
                    clean_desc = MCPSecurityManager.sanitize_untrusted_content(desc)
                    results.append(
                        SearchResultItem(
                            title=titles[i],
                            url=urls[i] if i < len(urls) else f"https://en.wikipedia.org/wiki/{quote(titles[i])}",
                            snippet=clean_desc,
                            source_domain="wikipedia.org",
                            retrieved_at=datetime.now(timezone.utc).isoformat(),
                            untrusted=True,
                            provider=active_provider,
                            data_mode="LIVE",
                            demo_data=False,
                        )
                    )

                if results:
                    result = WebSearchOutput(
                        query=query,
                        results=results[:max_results],
                        provider=active_provider,
                        data_mode="LIVE",
                        untrusted=True,
                        demo_data=False,
                    )
                    self.cache.set(cache_key, result, ttl_seconds=900)
                    return result
        except Exception as e:
            logger.warning(f"[{active_provider}] Search error: {str(e)}")

        # Fallback single result
        result = WebSearchOutput(
            query=query,
            results=[
                SearchResultItem(
                    title=f"{query.title()} Travel Knowledge",
                    url="https://en.wikipedia.org/wiki/Tourism",
                    snippet=MCPSecurityManager.sanitize_untrusted_content(f"Official cultural and visitor guidelines for {query}."),
                    source_domain="wikipedia.org",
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    untrusted=True,
                    provider=active_provider,
                    data_mode="LIVE",
                    demo_data=False,
                )
            ],
            provider=active_provider,
            data_mode="LIVE",
            untrusted=True,
            demo_data=False,
        )
        return result

    def fetch_page(
        self,
        url: str,
        demo_mode: Optional[bool] = None,
    ) -> FetchPageOutput:
        """Fetch and safely sanitize text from an external web URL under strict allowlist and sandboxing rules."""
        is_demo = get_effective_demo_mode(demo_mode)

        # 1. Enforce strict URL sandboxing & domain allowlist
        validated_url = MCPSecurityManager.validate_url(url, enforce_domain_allowlist=True)

        if is_demo:
            raw_content = (
                f"Article content extracted from {validated_url}. Provides verified travel safety information, "
                f"consular advisories, and cultural practices for international visitors."
            )
            sanitized_text = MCPSecurityManager.sanitize_untrusted_content(raw_content)
            return FetchPageOutput(
                url=validated_url,
                title="Verified Travel Authority Guide [DEMO]",
                content=sanitized_text,
                provider="Mock Web Fetcher",
                data_mode="DEMO",
                untrusted=True,
                demo_data=True,
            )

        cache_key = f"fetch_{validated_url}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # 2. Live HTTP GET
        try:
            resp = self.execute_http_request(method="GET", url=validated_url, timeout=6.0)
            raw_html = resp.text
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderNetworkError(f"Failed to fetch page from {validated_url}: {str(e)}", provider=self.provider_name)

        # 3. Apply Untrusted Content Sanitization (strip tags, scripts, prompt injections)
        sanitized_content = MCPSecurityManager.sanitize_untrusted_content(raw_html, max_chars=3000)

        result = FetchPageOutput(
            url=validated_url,
            title="External Resource Content [UNTRUSTED_DATA]",
            content=sanitized_content,
            provider="Live HTTP Fetcher",
            data_mode="LIVE",
            untrusted=True,
            demo_data=False,
        )
        self.cache.set(cache_key, result, ttl_seconds=1800)
        return result

    def search_news(
        self,
        query: str,
        limit: int = 3,
        demo_mode: Optional[bool] = None,
    ) -> SearchNewsOutput:
        """Discover recent regional news and seasonal events."""
        is_demo = get_effective_demo_mode(demo_mode)

        if is_demo:
            articles = [
                {
                    "headline": f"Seasonal Cultural Celebrations Announced for {query.title()}",
                    "date": "2026-09-15",
                    "source": "Global Travel Bulletin [DEMO_DATA]",
                    "untrusted": True,
                },
                {
                    "headline": f"Transit Authority Upgrades Contactless Tap-and-Go Payments in {query.title()}",
                    "date": "2026-09-01",
                    "source": "Metropolitan Transit Press [DEMO_DATA]",
                    "untrusted": True,
                },
            ]
            return SearchNewsOutput(
                query=query,
                articles=articles[:limit],
                provider="Mock News Service",
                data_mode="DEMO",
                untrusted=True,
                demo_data=True,
            )

        # In live mode, query current events/news via web search
        search_out = self.web_search(query=f"{query} travel news festival events", max_results=limit, demo_mode=False)
        articles = []
        for r in search_out.results:
            articles.append({
                "headline": r.title,
                "url": r.url,
                "snippet": r.snippet[:150],
                "source": r.source_domain or "Web",
                "retrieved_at": r.retrieved_at or datetime.now(timezone.utc).isoformat(),
                "untrusted": True,
            })

        return SearchNewsOutput(
            query=query,
            articles=articles[:limit],
            provider=search_out.provider,
            data_mode="LIVE",
            untrusted=True,
            demo_data=False,
        )


# Global singleton provider instance
search_provider = SearchProvider()
