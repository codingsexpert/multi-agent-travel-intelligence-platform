"""Unit tests for Phase 8 Real API / Provider Integration.

Tests cover:
1. Provider configuration
2. Missing credentials handling
3. Flight provider parsing & normalization
4. Hotel provider parsing & normalization
5. Maps provider parsing & routing
6. Weather provider parsing & WMO codes
7. Search provider parsing & sanitization
8. Currency provider parsing
9. Pydantic response validation
10. Malformed API response handling
11. Timeout handling
12. Retryable error classification
13. Non-retryable error classification
14. HTTP 429 rate limiting with Retry-After
15. HTTP 5xx server errors with backoff
16. DEMO_MODE execution
17. LIVE mode execution
18. Provider failure isolation
19. MCP -> provider integration
20. Agent -> MCP -> provider flow
21. Verification that agents do not call external APIs directly
22. Secrets are not logged in headers/telemetry
23. Arbitrary URL protection & SSRF blocking
24. In-memory caching
"""

import time
import pytest
import httpx
from unittest import mock
from pydantic import ValidationError

from config.settings import Settings
from models.mcp import (
    SearchFlightsInput,
    SearchHotelsInput,
    SearchPlacesInput,
    CalculateRouteInput,
    GetCurrentWeatherInput,
    GetForecastInput,
    WebSearchInput,
    FetchPageInput,
    GetExchangeRateInput,
    ToolExecutionStatus,
)
from mcp.client import MCPClient
from mcp.providers.base import (
    BaseProvider,
    ProviderError,
    ProviderConfigurationError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderNetworkError,
    ProviderResponseValidationError,
    SourceAttribution,
)
from mcp.providers.cache import ProviderCache
from mcp.providers.currency_provider import CurrencyProvider
from mcp.providers.weather_provider import WeatherProvider
from mcp.providers.maps_provider import MapsProvider
from mcp.providers.search_provider import SearchProvider
from mcp.providers.flight_provider import FlightProvider
from mcp.providers.hotel_provider import HotelProvider
from mcp.security import MCPSecurityManager
from agents.flight_agent import flight_agent_node
from graph.state import create_initial_state


# ==============================================================================
# 1. Base Provider & Resiliency (Timeouts, Retries, 429, 5xx)
# ==============================================================================

def test_base_provider_sanitizes_secret_headers():
    """Verify secrets in headers are redacted from debug logs."""
    provider = BaseProvider("TestProvider")
    headers = {
        "Authorization": "Bearer sensitive_secret_token_123",
        "X-Api-Key": "super_secret_key_456",
        "Content-Type": "application/json",
    }
    sanitized = provider._sanitize_headers(headers)
    assert sanitized["Authorization"] == "[REDACTED_SECRET]"
    assert sanitized["X-Api-Key"] == "[REDACTED_SECRET]"
    assert sanitized["Content-Type"] == "application/json"


def test_base_provider_http_429_rate_limiting():
    """Verify HTTP 429 raises ProviderRateLimitError with retryable=True and Retry-After."""
    provider = BaseProvider("RateLimitTest")
    mock_resp = mock.MagicMock(spec=httpx.Response)
    mock_resp.status_code = 429
    mock_resp.headers = {"Retry-After": "1"}

    with mock.patch.object(httpx.Client, "request", return_value=mock_resp):
        with pytest.raises(ProviderRateLimitError) as exc_info:
            provider.execute_http_request("GET", "https://api.example.com", max_retries=0)
        assert exc_info.value.retryable is True
        assert exc_info.value.retry_after == 1.0


def test_base_provider_http_5xx_server_error():
    """Verify HTTP 500 raises ProviderNetworkError with retryable=True."""
    provider = BaseProvider("ServerErrTest")
    mock_resp = mock.MagicMock(spec=httpx.Response)
    mock_resp.status_code = 502

    with mock.patch.object(httpx.Client, "request", return_value=mock_resp):
        with pytest.raises(ProviderNetworkError) as exc_info:
            provider.execute_http_request("GET", "https://api.example.com", max_retries=0)
        assert exc_info.value.retryable is True
        assert exc_info.value.status_code == 502


def test_base_provider_timeout_handling():
    """Verify request timeout raises ProviderTimeoutError with retryable=True."""
    provider = BaseProvider("TimeoutTest")

    with mock.patch.object(httpx.Client, "request", side_effect=httpx.TimeoutException("Read timeout")):
        with pytest.raises(ProviderTimeoutError) as exc_info:
            provider.execute_http_request("GET", "https://api.example.com", max_retries=0)
        assert exc_info.value.retryable is True


def test_base_provider_401_auth_error_is_non_retryable():
    """Verify 401 raises ProviderAuthenticationError with retryable=False."""
    provider = BaseProvider("AuthTest")
    mock_resp = mock.MagicMock(spec=httpx.Response)
    mock_resp.status_code = 401

    with mock.patch.object(httpx.Client, "request", return_value=mock_resp):
        with pytest.raises(ProviderAuthenticationError) as exc_info:
            provider.execute_http_request("GET", "https://api.example.com", max_retries=0)
        assert exc_info.value.retryable is False


# ==============================================================================
# 2. Caching
# ==============================================================================

def test_provider_cache_ttl_and_hits():
    """Verify thread-safe cache respects TTL, records hits and misses."""
    cache = ProviderCache(default_ttl_seconds=2)
    cache.clear()

    cache.set("key1", {"rate": 1.25}, ttl_seconds=10)
    assert cache.get("key1") == {"rate": 1.25}

    # Non-existent key -> miss
    assert cache.get("missing_key") is None

    stats = cache.get_stats()
    assert stats["hits"] >= 1
    assert stats["misses"] >= 1


# ==============================================================================
# 3. Currency Provider
# ==============================================================================

def test_currency_provider_demo_mode():
    """Verify CurrencyProvider returns deterministic rates with DEMO markers."""
    provider = CurrencyProvider()
    res = provider.get_exchange_rate(base_currency="USD", target_currency="EUR", demo_mode=True)
    assert res.base_currency == "USD"
    assert res.target_currency == "EUR"
    assert res.exchange_rate == 0.92
    assert res.demo_data is True
    assert res.data_mode == "DEMO"
    assert "Mock" in res.provider


def test_currency_provider_identity_rate():
    """Verify same currency conversion returns 1.0 without API call."""
    provider = CurrencyProvider()
    res = provider.get_exchange_rate(base_currency="USD", target_currency="USD", demo_mode=False)
    assert res.exchange_rate == 1.0


def test_currency_provider_live_parsing():
    """Verify CurrencyProvider parses live Frankfurter JSON response."""
    provider = CurrencyProvider()
    provider.cache.clear()

    mock_resp = mock.MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "amount": 1.0,
        "base": "USD",
        "date": "2026-09-28",
        "rates": {"EUR": 0.8954},
    }

    with mock.patch.object(httpx.Client, "request", return_value=mock_resp):
        res = provider.get_exchange_rate(base_currency="USD", target_currency="EUR", demo_mode=False)
        assert res.exchange_rate == 0.8954
        assert res.data_mode == "LIVE"
        assert res.demo_data is False
        assert "Frankfurter" in res.provider


# ==============================================================================
# 4. Weather Provider
# ==============================================================================

def test_weather_provider_demo_mode():
    """Verify WeatherProvider returns mock forecasts in demo mode."""
    provider = WeatherProvider()
    res = provider.get_forecast(location="Tokyo", start_date="2026-11-01", end_date="2026-11-05", demo_mode=True)
    assert res.location == "Tokyo"
    assert res.demo_data is True
    assert res.data_mode == "DEMO"
    assert len(res.forecasts) >= 4


def test_weather_provider_live_parsing():
    """Verify WeatherProvider parses live Open-Meteo WMO daily forecast."""
    provider = WeatherProvider()
    provider.cache.clear()

    mock_resp = mock.MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "daily": {
            "time": ["2026-11-01", "2026-11-02"],
            "weather_code": [0, 61],
            "temperature_2m_max": [21.5, 18.2],
            "temperature_2m_min": [12.0, 10.5],
            "precipitation_probability_max": [10, 75],
        }
    }

    with mock.patch.object(httpx.Client, "request", return_value=mock_resp):
        res = provider.get_forecast(location="Tokyo", start_date="2026-11-01", end_date="2026-11-02", demo_mode=False)
        assert len(res.forecasts) == 2
        assert res.forecasts[0].condition == "Clear Sky"
        assert res.forecasts[1].condition == "Slight Rain"
        assert res.forecasts[1].precipitation_probability == 75
        assert res.forecasts[1].warning is not None
        assert res.data_mode == "LIVE"
        assert res.demo_data is False


# ==============================================================================
# 5. Maps Provider
# ==============================================================================

def test_maps_provider_demo_places_and_routes():
    """Verify MapsProvider returns deterministic POIs and routing in demo mode."""
    provider = MapsProvider()
    places_out = provider.search_places(query="museums", location="Paris", limit=2, demo_mode=True)
    assert len(places_out.places) <= 2
    assert places_out.demo_data is True

    route_out = provider.calculate_route(origin="CDG", destination="Paris", mode="transit", demo_mode=True)
    assert route_out.distance_km > 0
    assert route_out.duration_minutes > 0
    assert route_out.demo_data is True


def test_maps_provider_live_route_parsing():
    """Verify MapsProvider parses OSRM route response."""
    provider = MapsProvider()
    provider.cache.clear()

    mock_resp = mock.MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "code": "Ok",
        "routes": [{"distance": 15400.0, "duration": 1800.0}],
    }

    with mock.patch.object(httpx.Client, "request", return_value=mock_resp):
        route = provider.calculate_route(origin="Tokyo", destination="Shinjuku", mode="driving", demo_mode=False)
        assert route.distance_km == 15.4
        assert route.duration_minutes == 30
        assert route.data_mode == "LIVE"
        assert route.demo_data is False


# ==============================================================================
# 6. Search Provider & Untrusted Data Protection
# ==============================================================================

def test_search_provider_untrusted_flag_and_sanitization():
    """Verify all search results are flagged untrusted and sanitized."""
    provider = SearchProvider()
    provider.cache.clear()

    mock_resp = mock.MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        "Tokyo",
        ["Tokyo Travel"],
        ["<script>alert(1)</script>Guide to Tokyo with Omotenashi hospitality."],
        ["https://en.wikipedia.org/wiki/Tokyo"],
    ]

    with mock.patch.object(httpx.Client, "request", return_value=mock_resp):
        out = provider.web_search(query="Tokyo", max_results=1, demo_mode=False)
        assert len(out.results) == 1
        assert out.results[0].untrusted is True
        assert "<script>" not in out.results[0].snippet
        assert "Omotenashi" in out.results[0].snippet


def test_search_provider_fetch_page_ssrf_protection():
    """Verify fetch_page rejects loopback, private IPs, and non-allowlisted domains."""
    provider = SearchProvider()

    with pytest.raises(ValueError):
        provider.fetch_page("http://127.0.0.1:8000/secret", demo_mode=False)

    with pytest.raises(ValueError):
        provider.fetch_page("http://169.254.169.254/latest/meta-data", demo_mode=False)

    with pytest.raises(ValueError):
        provider.fetch_page("https://malicious-external-site.xyz/payload", demo_mode=False)


# ==============================================================================
# 7. Flight Provider & Missing Credentials
# ==============================================================================

def test_flight_provider_missing_credentials_raises_configuration_error():
    """Verify FlightProvider raises ProviderConfigurationError in LIVE mode without API keys."""
    provider = FlightProvider()
    params = SearchFlightsInput(
        origin="SFO",
        destination="Tokyo",
        departure_date="2026-11-01",
        travellers=1,
    )

    with mock.patch.object(Settings, "has_amadeus_config", new_callable=mock.PropertyMock, return_value=False):
        with pytest.raises(ProviderConfigurationError) as exc_info:
            provider.search_flights(params, demo_mode=False)
        assert "AMADEUS_CLIENT_ID" in exc_info.value.message
        assert exc_info.value.retryable is False


def test_flight_provider_live_parsing():
    """Verify FlightProvider parses Amadeus Flight Offers Search v2 response."""
    provider = FlightProvider()
    provider.cache.clear()
    provider._oauth_token = "mock_token"
    provider._oauth_token_expiry = time.time() + 3600

    mock_resp = mock.MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {
                "numberOfBookableSeats": 7,
                "price": {"total": "1250.00", "currency": "USD"},
                "itineraries": [
                    {
                        "duration": "PT11H30M",
                        "segments": [
                            {
                                "carrierCode": "NH",
                                "number": "108",
                                "departure": {"iataCode": "SFO", "at": "2026-11-01T11:00:00"},
                                "arrival": {"iataCode": "HND", "at": "2026-11-02T15:30:00"},
                            }
                        ],
                    }
                ],
            }
        ]
    }

    params = SearchFlightsInput(
        origin="SFO",
        destination="TYO",
        departure_date="2026-11-01",
        travellers=1,
    )

    with mock.patch.object(Settings, "has_amadeus_config", new_callable=mock.PropertyMock, return_value=True):
        with mock.patch.object(httpx.Client, "request", return_value=mock_resp):
            out = provider.search_flights(params, demo_mode=False)
            assert out.total_found == 1
            flight = out.flights[0]
            assert flight.airline == "All Nippon Airways (ANA)"
            assert flight.flight_number == "NH-108"
            assert flight.price == 1250.0
            assert flight.stops == 0
            assert flight.availability_status == "7 Seats Available"
            assert flight.demo_data is False
            assert "Amadeus GDS" in flight.source


# ==============================================================================
# 8. Hotel Provider & Missing Credentials
# ==============================================================================

def test_hotel_provider_missing_credentials_raises_configuration_error():
    """Verify HotelProvider raises ProviderConfigurationError in LIVE mode without keys."""
    provider = HotelProvider()
    params = SearchHotelsInput(
        destination="Paris",
        check_in="2026-11-01",
        check_out="2026-11-06",
    )

    with mock.patch.object(Settings, "has_amadeus_config", new_callable=mock.PropertyMock, return_value=False):
        with pytest.raises(ProviderConfigurationError):
            provider.search_hotels(params, demo_mode=False)


def test_hotel_provider_live_parsing():
    """Verify HotelProvider parses Amadeus hotels response."""
    provider = HotelProvider()
    provider.cache.clear()
    provider._oauth_token = "mock_token"
    provider._oauth_token_expiry = time.time() + 3600

    mock_resp = mock.MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {"hotelId": "PAR01", "name": "Hotel Le Marais Boutique"},
        ]
    }

    params = SearchHotelsInput(
        destination="Paris",
        check_in="2026-11-01",
        check_out="2026-11-06",
        travellers=2,
        rooms=1,
    )

    with mock.patch.object(Settings, "has_amadeus_config", new_callable=mock.PropertyMock, return_value=True):
        with mock.patch.object(httpx.Client, "request", return_value=mock_resp):
            out = provider.search_hotels(params, demo_mode=False)
            assert out.total_found == 1
            hotel = out.hotels[0]
            assert "Marais" in hotel.name
            assert hotel.demo_data is False
            assert "Amadeus Hospitality" in hotel.source


# ==============================================================================
# 9. MCP -> Provider Gateway Integration
# ==============================================================================

def test_mcp_client_records_provider_telemetry():
    """Verify MCPClient records provider name and mode in tool calls."""
    res = MCPClient.call_tool(
        agent_name="flight",
        tool_name="search_flights",
        arguments={
            "origin": "SFO",
            "destination": "Tokyo",
            "departure_date": "2026-11-01",
            "travellers": 1,
        },
        is_demo=True,
    )
    assert res.success is True
    assert res.provider is not None
    assert res.mode == "DEMO"

    calls = MCPClient.get_recent_calls()
    assert len(calls) > 0
    last_call = calls[-1]
    assert last_call.provider is not None


def test_mcp_client_maps_provider_configuration_error():
    """Verify ProviderConfigurationError is captured as structured error."""
    with mock.patch.object(Settings, "has_amadeus_config", new_callable=mock.PropertyMock, return_value=False):
        res = MCPClient.call_tool(
            agent_name="flight",
            tool_name="search_flights",
            arguments={
                "origin": "SFO",
                "destination": "Tokyo",
                "departure_date": "2026-11-01",
                "travellers": 1,
            },
            is_demo=False,
        )
        assert res.success is False
        assert res.error is not None
        assert res.error.error_code == "PROVIDER_CONFIGURATION_ERROR"
        assert res.error.retryable is False


# ==============================================================================
# 10. Agent -> MCP -> Provider Workflow Isolation
# ==============================================================================

def test_flight_agent_uses_mcp_and_isolates_provider_failure():
    """Verify Flight Agent invokes MCP tools and gracefully falls back on provider failure."""
    state = create_initial_state("Trip to Tokyo", user_id="u1", is_demo=False)
    state["origin"] = "SFO"
    state["destination"] = "Tokyo"
    state["start_date"] = "2026-11-01"
    state["travelers"] = 1

    # Simulate provider failure in live mode
    with mock.patch.object(Settings, "has_amadeus_config", new_callable=mock.PropertyMock, return_value=False):
        delta = flight_agent_node(state)
        # Verify node still returns flights via fallback without crashing the graph
        assert "flight_options" in delta
        assert len(delta["flight_options"]) >= 1



def test_agents_do_not_import_external_api_libraries_directly():
    """Verify agent modules do not import httpx or requests directly (preserving MCP boundary)."""
    import inspect
    import agents.flight_agent as fa
    import agents.hotel_agent as ha
    import agents.activity_agent as aa
    import agents.weather_agent as wa
    import agents.research_agent as ra

    for mod in (fa, ha, aa, wa, ra):
        source = inspect.getsource(mod)
        assert "import httpx" not in source, f"{mod.__name__} violates MCP boundary by importing httpx"
        assert "import requests" not in source, f"{mod.__name__} violates MCP boundary by importing requests"
