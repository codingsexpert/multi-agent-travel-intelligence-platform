"""Search and Knowledge Provider Adapter integrating Tavily, Brave, Wikipedia, sandboxed HTTP retrieval, and mock fallbacks."""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from urllib.parse import quote, urlparse
import re

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
from models.research import (
    SourceTrustCategory,
    classify_domain_trust,
)
from mcp.security import MCPSecurityManager
from mcp.providers.base import (
    BaseProvider,
    ProviderError,
    ProviderConfigurationError,
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
        require_api_key: bool = False,
    ):
        super().__init__(provider_name="Search & Knowledge Provider", base_url=wikipedia_url)
        self.tavily_url = tavily_url
        self.require_api_key = require_api_key
        self.cache = ProviderCache(default_ttl_seconds=900)  # 15 minute cache

    def web_search(
        self,
        query: str,
        destination: Optional[str] = None,
        recency: Optional[str] = None,
        language: str = "en",
        max_results: int = 5,
        allowed_domains: Optional[List[str]] = None,
        demo_mode: Optional[bool] = None,
    ) -> WebSearchOutput:
        """Execute external web search returning sanitized snippets tagged as untrusted third-party data."""
        is_demo = get_effective_demo_mode(demo_mode)
        
        # Validate query safety
        clean_query = MCPSecurityManager.validate_search_query(query)
        q_lower = clean_query.lower()
        dest_context = (destination or "").strip()

        if is_demo:
            results = self._generate_mock_web_search(clean_query, dest_context, recency, max_results)
            return WebSearchOutput(
                query=clean_query,
                destination=dest_context or None,
                recency=recency,
                results=results[:max_results],
                provider="Mock Search Service",
                data_mode="DEMO",
                untrusted=True,
                demo_data=True,
            )

        cache_key = f"search_{q_lower}_{dest_context}_{recency}_{max_results}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # 1. Option A: Use Tavily if API key is provided
        if settings.has_tavily_config:
            active_provider = "Tavily AI Search"
            try:
                headers = {"Content-Type": "application/json"}
                payload: Dict[str, Any] = {
                    "api_key": settings.tavily_api_key.get_secret_value() if settings.tavily_api_key else "",
                    "query": clean_query,
                    "search_depth": "basic",
                    "max_results": max_results,
                }
                if recency in ("today", "24h", "1d"):
                    payload["days"] = 1
                elif recency in ("7d", "week"):
                    payload["days"] = 7
                elif recency in ("30d", "month"):
                    payload["days"] = 30

                if allowed_domains:
                    payload["include_domains"] = allowed_domains

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
                    u = item.get("url", "https://tavily.com")
                    clean_snippet = MCPSecurityManager.sanitize_untrusted_content(item.get("content", ""))
                    domain = urlparse(u).hostname or "web"
                    trust_cat = classify_domain_trust(u)

                    results.append(
                        SearchResultItem(
                            title=item.get("title", clean_query.title()),
                            url=u,
                            snippet=clean_snippet,
                            source_domain=domain,
                            source_type=trust_cat.value,
                            published_at=item.get("published_date"),
                            retrieved_at=datetime.now(timezone.utc).isoformat(),
                            relevance_score=float(item.get("score", 0.85)),
                            untrusted=True,
                            provider=active_provider,
                            data_mode="LIVE",
                            demo_data=False,
                        )
                    )

                result = WebSearchOutput(
                    query=clean_query,
                    destination=dest_context or None,
                    recency=recency,
                    results=results,
                    provider=active_provider,
                    data_mode="LIVE",
                    untrusted=True,
                    demo_data=False,
                )
                self.cache.set(cache_key, result, ttl_seconds=900)
                return result
            except ProviderError:
                raise
            except Exception as e:
                logger.warning(f"[{active_provider}] Search failed: {str(e)}.")
                raise ProviderNetworkError(f"Tavily search network failure: {str(e)}", provider=active_provider)

        # 2. Option B: Use Brave Search if API key is provided
        if settings.has_brave_search_config:
            active_provider = "Brave Search API"
            try:
                headers = {
                    "Accept": "application/json",
                    "X-Subscription-Token": settings.brave_search_api_key.get_secret_value() if settings.brave_search_api_key else "",
                }
                params: Dict[str, Any] = {
                    "q": clean_query,
                    "count": max_results,
                }
                if recency in ("today", "24h", "1d"):
                    params["freshness"] = "pd"
                elif recency in ("7d", "week"):
                    params["freshness"] = "pw"
                elif recency in ("30d", "month"):
                    params["freshness"] = "pm"

                resp = self.execute_http_request(
                    method="GET",
                    url="https://api.search.brave.com/res/v1/web/search",
                    headers=headers,
                    params=params,
                    timeout=6.0,
                )
                brave_data = resp.json()
                brave_results = brave_data.get("web", {}).get("results", [])

                results = []
                for item in brave_results[:max_results]:
                    u = item.get("url", "")
                    clean_snippet = MCPSecurityManager.sanitize_untrusted_content(item.get("description", ""))
                    domain = urlparse(u).hostname or "web"
                    trust_cat = classify_domain_trust(u)

                    results.append(
                        SearchResultItem(
                            title=item.get("title", clean_query.title()),
                            url=u,
                            snippet=clean_snippet,
                            source_domain=domain,
                            source_type=trust_cat.value,
                            published_at=item.get("page_age"),
                            retrieved_at=datetime.now(timezone.utc).isoformat(),
                            relevance_score=0.90,
                            untrusted=True,
                            provider=active_provider,
                            data_mode="LIVE",
                            demo_data=False,
                        )
                    )

                result = WebSearchOutput(
                    query=clean_query,
                    destination=dest_context or None,
                    recency=recency,
                    results=results,
                    provider=active_provider,
                    data_mode="LIVE",
                    untrusted=True,
                    demo_data=False,
                )
                self.cache.set(cache_key, result, ttl_seconds=900)
                return result
            except ProviderError:
                raise
            except Exception as e:
                logger.warning(f"[{active_provider}] Search failed: {str(e)}.")
                raise ProviderNetworkError(f"Brave search network failure: {str(e)}", provider=active_provider)

        # 3. Option C: Keyless Wikipedia OpenSearch API fallback (when not strictly requiring API key)
        if not self.require_api_key:
            active_provider = "Wikipedia Knowledge API"
            params = {
                "action": "opensearch",
                "search": clean_query,
                "limit": max_results,
                "namespace": 0,
                "format": "json",
            }
            try:
                resp = self.execute_http_request(method="GET", url=self.base_url, params=params, timeout=5.0)
                data = resp.json()
                if len(data) >= 4:
                    titles = data[1]
                    descriptions = data[2]
                    urls = data[3]

                    results = []
                    for i in range(len(titles)):
                        desc = descriptions[i] if i < len(descriptions) and descriptions[i] else f"Information for {titles[i]}."
                        clean_desc = MCPSecurityManager.sanitize_untrusted_content(desc)
                        target_url = urls[i] if i < len(urls) else f"https://en.wikipedia.org/wiki/{quote(titles[i])}"
                        results.append(
                            SearchResultItem(
                                title=titles[i],
                                url=target_url,
                                snippet=clean_desc,
                                source_domain="wikipedia.org",
                                source_type=SourceTrustCategory.REFERENCE.value,
                                retrieved_at=datetime.now(timezone.utc).isoformat(),
                                untrusted=True,
                                provider=active_provider,
                                data_mode="LIVE",
                                demo_data=False,
                            )
                        )

                    if results:
                        result = WebSearchOutput(
                            query=clean_query,
                            destination=dest_context or None,
                            recency=recency,
                            results=results[:max_results],
                            provider=active_provider,
                            data_mode="LIVE",
                            untrusted=True,
                            demo_data=False,
                        )
                        self.cache.set(cache_key, result, ttl_seconds=900)
                        return result
            except ProviderError:
                raise
            except Exception as e:
                logger.warning(f"[{active_provider}] Search error: {str(e)}")

        # 4. No live search provider configured: raise explicit configuration error
        raise ProviderConfigurationError(
            message="Live search provider credentials missing. Configure TAVILY_API_KEY or "
            "BRAVE_SEARCH_API_KEY in .env or switch to DEMO_MODE=true.",
            provider=self.provider_name,
        )

    def fetch_page(
        self,
        url: str,
        max_length: int = 3000,
        demo_mode: Optional[bool] = None,
    ) -> FetchPageOutput:
        """Fetch and safely sanitize text from an external web URL under strict allowlist and sandboxing rules."""
        is_demo = get_effective_demo_mode(demo_mode)

        # 1. Enforce strict URL sandboxing (SSRF prevention, protocol validation, domain allowlist)
        validated_url = MCPSecurityManager.validate_url(url, enforce_domain_allowlist=True)
        domain = urlparse(validated_url).hostname or "web"
        trust_cat = classify_domain_trust(validated_url)

        if is_demo:
            raw_content = (
                f"Official visitor briefing extracted from {domain}. Highlights seasonal operating hours, "
                f"entry requirements, transport connections, and current regional advisory notices."
            )
            extracted = MCPSecurityManager.extract_clean_web_content(
                f"<html><head><title>{domain.title()} Advisory</title></head><body><h1>Official Guide</h1><p>{raw_content}</p></body></html>",
                max_chars=max_length,
            )
            return FetchPageOutput(
                url=validated_url,
                title=f"{extracted['title']} [DEMO]",
                headings=extracted["headings"] or ["Overview"],
                content=extracted["content"],
                source_domain=domain,
                source_type=trust_cat.value,
                published_at="2026-09-01",
                retrieved_at=datetime.now(timezone.utc).isoformat(),
                provider="Mock Web Fetcher",
                data_mode="DEMO",
                untrusted=True,
                demo_data=True,
            )

        cache_key = f"fetch_{validated_url}_{max_length}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # 2. Live HTTP GET with bounded timeout and size limit
        try:
            resp = self.execute_http_request(method="GET", url=validated_url, timeout=5.0)
            # Guard against massive file downloads (> 500KB)
            if len(resp.content) > 500_000:
                raw_html = resp.text[:500_000]
            else:
                raw_html = resp.text
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderNetworkError(f"Failed to fetch page from {validated_url}: {str(e)}", provider=self.provider_name)

        # 3. Clean and structured HTML extraction
        extracted = MCPSecurityManager.extract_clean_web_content(raw_html, max_chars=max_length)

        result = FetchPageOutput(
            url=validated_url,
            title=extracted["title"],
            headings=extracted["headings"],
            content=extracted["content"],
            source_domain=domain,
            source_type=trust_cat.value,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
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
        destination: Optional[str] = None,
        recency: Optional[str] = "7d",
        limit: int = 3,
        demo_mode: Optional[bool] = None,
    ) -> SearchNewsOutput:
        """Discover recent regional travel news, disruptions, and seasonal events."""
        is_demo = get_effective_demo_mode(demo_mode)
        clean_query = MCPSecurityManager.validate_search_query(query)
        dest_context = (destination or "").strip()

        if is_demo:
            articles = self._generate_mock_news(clean_query, dest_context, limit)
            return SearchNewsOutput(
                query=clean_query,
                destination=dest_context or None,
                recency=recency or "7d",
                articles=articles[:limit],
                provider="Mock News Service",
                data_mode="DEMO",
                untrusted=True,
                demo_data=True,
            )

        cache_key = f"news_{clean_query.lower()}_{dest_context}_{recency}_{limit}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # In live mode, query current events/news via web search with recency
        combined_q = f"{clean_query} {dest_context} travel news festival disruption advisory".strip()
        search_out = self.web_search(
            query=combined_q,
            destination=dest_context or None,
            recency=recency or "7d",
            max_results=limit,
            demo_mode=False,
        )

        articles = []
        for r in search_out.results:
            articles.append({
                "headline": r.title,
                "url": r.url,
                "snippet": r.snippet[:180],
                "source": r.source_domain or "Web News",
                "source_type": r.source_type,
                "published_at": r.published_at or "Recent",
                "retrieved_at": r.retrieved_at or datetime.now(timezone.utc).isoformat(),
                "untrusted": True,
            })

        result = SearchNewsOutput(
            query=clean_query,
            destination=dest_context or None,
            recency=recency or "7d",
            articles=articles[:limit],
            provider=search_out.provider,
            data_mode="LIVE",
            untrusted=True,
            demo_data=False,
        )
        self.cache.set(cache_key, result, ttl_seconds=600)
        return result

    # --------------------------------------------------------------------------
    # Mock / DEMO Generators
    # --------------------------------------------------------------------------
    def _generate_mock_web_search(
        self,
        query: str,
        destination: str,
        recency: Optional[str],
        max_results: int,
    ) -> List[SearchResultItem]:
        """Generate realistic, deterministic mock search results matching destination and topic."""
        target = (destination or query).lower()
        now_iso = datetime.now(timezone.utc).isoformat()

        if "tokyo" in target or "japan" in target:
            return [
                SearchResultItem(
                    title="Japan National Tourism Organization (JNTO) - Official Travel Guidance",
                    url="https://www.japan.travel/en/advisory/2026/",
                    snippet="Official travel advisory: Autumn cultural festivals active across Tokyo. IC card supply stabilized. No COVID border restrictions in effect.",
                    source_domain="japan.travel",
                    source_type=SourceTrustCategory.OFFICIAL.value,
                    published_at="2026-09-20",
                    retrieved_at=now_iso,
                    relevance_score=0.96,
                    untrusted=True,
                    provider="Mock Search Service",
                    data_mode="DEMO",
                    demo_data=True,
                ),
                SearchResultItem(
                    title="Tokyo Metropolitan Government: Shinjuku & Asakusa Autumn Festival Dates",
                    url="https://metro.tokyo.jp/events/autumn-2026.html",
                    snippet="Annual Meiji Shrine Autumn Grand Festival scheduled for early November. Historic Senso-ji temple grounds operating standard hours.",
                    source_domain="metro.tokyo.jp",
                    source_type=SourceTrustCategory.OFFICIAL.value,
                    published_at="2026-09-18",
                    retrieved_at=now_iso,
                    relevance_score=0.92,
                    untrusted=True,
                    provider="Mock Search Service",
                    data_mode="DEMO",
                    demo_data=True,
                ),
                SearchResultItem(
                    title="Japan Times: Haneda Airport Runway Maintenance Advisory",
                    url="https://japantimes.co.jp/travel/haneda-runway-maintenance-update",
                    snippet="Nightly runway resurfacing at Haneda Airport causes minor 15-minute taxi delays on select late-night international arrivals.",
                    source_domain="japantimes.co.jp",
                    source_type=SourceTrustCategory.NEWS.value,
                    published_at="2026-09-25",
                    retrieved_at=now_iso,
                    relevance_score=0.88,
                    untrusted=True,
                    provider="Mock Search Service",
                    data_mode="DEMO",
                    demo_data=True,
                ),
                SearchResultItem(
                    title="Wikivoyage: Tokyo Public Transportation & Pass Logistics",
                    url="https://en.wikivoyage.org/wiki/Tokyo#Get_around",
                    snippet="Subway fare gates accept digital Suica and Pasmo via Apple/Google Wallet. Tokyo Metro 24/48/72-hour tourist passes available at major hubs.",
                    source_domain="wikivoyage.org",
                    source_type=SourceTrustCategory.REFERENCE.value,
                    published_at="2026-08-15",
                    retrieved_at=now_iso,
                    relevance_score=0.84,
                    untrusted=True,
                    provider="Mock Search Service",
                    data_mode="DEMO",
                    demo_data=True,
                ),
            ]
        elif "paris" in target or "france" in target:
            return [
                SearchResultItem(
                    title="Paris Je T'Aime - Official Tourism Board: Seine River Promenade Guidelines",
                    url="https://parisjetaime.com/eng/article/seine-river-promenade-guidance",
                    snippet="Official guidelines for visitor access along the Seine river banks. Timed ticket reservations mandatory for Louvre and Eiffel Tower summits.",
                    source_domain="parisjetaime.com",
                    source_type=SourceTrustCategory.OFFICIAL.value,
                    published_at="2026-09-10",
                    retrieved_at=now_iso,
                    relevance_score=0.95,
                    untrusted=True,
                    provider="Mock Search Service",
                    data_mode="DEMO",
                    demo_data=True,
                ),
                SearchResultItem(
                    title="France24: Paris Metro Line 14 Extension & Navigo Updates",
                    url="https://france24.com/en/france/paris-metro-line-14-extension-updates",
                    snippet="Line 14 extension directly connecting Orly Airport to Central Paris operational. Navigo Easy passes supported on all smartphones.",
                    source_domain="france24.com",
                    source_type=SourceTrustCategory.NEWS.value,
                    published_at="2026-09-22",
                    retrieved_at=now_iso,
                    relevance_score=0.89,
                    untrusted=True,
                    provider="Mock Search Service",
                    data_mode="DEMO",
                    demo_data=True,
                ),
                SearchResultItem(
                    title="US Department of State: France Travel Advisory Level 2",
                    url="https://travel.state.gov/content/travel/en/traveladvisories/france-travel-advisory.html",
                    snippet="Exercise increased caution in France due to potential civil demonstrations and pickpocketing in tourist corridors.",
                    source_domain="travel.state.gov",
                    source_type=SourceTrustCategory.OFFICIAL.value,
                    published_at="2026-09-01",
                    retrieved_at=now_iso,
                    relevance_score=0.94,
                    untrusted=True,
                    provider="Mock Search Service",
                    data_mode="DEMO",
                    demo_data=True,
                ),
            ]
        elif "london" in target or "uk" in target:
            return [
                SearchResultItem(
                    title="VisitBritain: UK Electronic Travel Authorisation (ETA) Requirement",
                    url="https://visitbritain.com/en/plan-your-trip/visas-and-entry-requirements",
                    snippet="Official entry advisory: All non-visa international visitors require valid UK ETA prior to boarding flights to London airports.",
                    source_domain="visitbritain.com",
                    source_type=SourceTrustCategory.OFFICIAL.value,
                    published_at="2026-09-12",
                    retrieved_at=now_iso,
                    relevance_score=0.97,
                    untrusted=True,
                    provider="Mock Search Service",
                    data_mode="DEMO",
                    demo_data=True,
                ),
                SearchResultItem(
                    title="BBC News: Transport for London Weekend Tube Engineering Works",
                    url="https://bbc.com/news/uk-england-london-transit-upgrades",
                    snippet="Central Line track replacement work on select weekends with replacement bus shuttles between Stratford and Liverpool Street.",
                    source_domain="bbc.com",
                    source_type=SourceTrustCategory.NEWS.value,
                    published_at="2026-09-26",
                    retrieved_at=now_iso,
                    relevance_score=0.91,
                    untrusted=True,
                    provider="Mock Search Service",
                    data_mode="DEMO",
                    demo_data=True,
                ),
            ]
        else:
            return [
                SearchResultItem(
                    title=f"Official Visitor Bureau Guidance for {query.title()}",
                    url=f"https://en.wikipedia.org/wiki/{quote(query)}",
                    snippet=f"Comprehensive visitor insights, cultural highlights, and practical logistics for travel in {query}.",
                    source_domain="wikipedia.org",
                    source_type=SourceTrustCategory.REFERENCE.value,
                    published_at="2026-08-01",
                    retrieved_at=now_iso,
                    relevance_score=0.85,
                    untrusted=True,
                    provider="Mock Search Service",
                    data_mode="DEMO",
                    demo_data=True,
                )
            ]

    def _generate_mock_news(
        self,
        query: str,
        destination: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Generate realistic mock travel news and events."""
        target = (destination or query).lower()
        now_iso = datetime.now(timezone.utc).isoformat()

        if "tokyo" in target or "japan" in target:
            return [
                {
                    "headline": "Tokyo Autumn Illuminations and Cultural Festivals Announced for 2026",
                    "url": "https://metro.tokyo.jp/news/autumn-illuminations",
                    "snippet": "Roppongi Hills and Tokyo Midtown announce synchronized LED installations starting October 28.",
                    "source": "metro.tokyo.jp",
                    "source_type": SourceTrustCategory.OFFICIAL.value,
                    "published_at": "2026-09-24",
                    "retrieved_at": now_iso,
                    "untrusted": True,
                },
                {
                    "headline": "JR East Completes Contactless Smartphone Gate Rollout",
                    "url": "https://japantimes.co.jp/business/jr-east-smartphone-ticketing",
                    "snippet": "All Yamanote line stations now support QR and NFC digital passes directly through mobile wallets.",
                    "source": "japantimes.co.jp",
                    "source_type": SourceTrustCategory.NEWS.value,
                    "published_at": "2026-09-20",
                    "retrieved_at": now_iso,
                    "untrusted": True,
                },
                {
                    "headline": "Mount Fuji Climbing Season Closes for Winter Transition",
                    "url": "https://japan.travel/news/mount-fuji-seasonal-closure",
                    "snippet": "Official trails on Mount Fuji are closed until July 2027; off-season climbing is strictly prohibited.",
                    "source": "japan.travel",
                    "source_type": SourceTrustCategory.OFFICIAL.value,
                    "published_at": "2026-09-15",
                    "retrieved_at": now_iso,
                    "untrusted": True,
                },
            ]
        elif "paris" in target or "france" in target:
            return [
                {
                    "headline": "Nuit Blanche 2026 All-Night Contemporary Arts Festival Announced",
                    "url": "https://paris.fr/actualites/nuit-blanche-2026",
                    "snippet": "Over 200 public monuments, bridges, and gardens will host open-air light and art installations.",
                    "source": "paris.fr",
                    "source_type": SourceTrustCategory.OFFICIAL.value,
                    "published_at": "2026-09-23",
                    "retrieved_at": now_iso,
                    "untrusted": True,
                },
                {
                    "headline": "Louvre Museum Introduces Enhanced Morning Digital Entry Slots",
                    "url": "https://lemonde.fr/culture/louvre-billetterie-matinale",
                    "snippet": "New 09:00 AM dedicated entry slots opened to reduce afternoon overcrowding in the Denon wing.",
                    "source": "lemonde.fr",
                    "source_type": SourceTrustCategory.NEWS.value,
                    "published_at": "2026-09-19",
                    "retrieved_at": now_iso,
                    "untrusted": True,
                },
            ]
        else:
            return [
                {
                    "headline": f"Regional Cultural Festivals & Tourism Events Announced in {query.title()}",
                    "url": "https://en.wikipedia.org/wiki/Tourism",
                    "snippet": f"Local authorities in {query.title()} publish seasonal events schedule and transportation advisories.",
                    "source": "Global Travel Bulletin",
                    "source_type": SourceTrustCategory.REFERENCE.value,
                    "published_at": "2026-09-15",
                    "retrieved_at": now_iso,
                    "untrusted": True,
                }
            ]


# Global singleton provider instance
search_provider = SearchProvider()
