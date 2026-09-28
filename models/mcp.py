"""Pydantic v2 schemas for Model Context Protocol (MCP) tools, inputs, outputs, and telemetry."""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from models.specialized_options import FlightOption, HotelOption, WeatherObservation


# ==============================================================================
# Universal MCP Infrastructure & Telemetry Schemas
# ==============================================================================

class ToolExecutionStatus(str, Enum):
    """Execution status for MCP tool invocations."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    UNAUTHORIZED = "UNAUTHORIZED"


class ToolExecutionError(BaseModel):
    """Machine-readable structured error representing an MCP execution failure."""

    tool_name: str = Field(description="Name of the MCP tool that failed.")
    error_code: str = Field(description="Categorical error code (e.g., TIMEOUT, PERMISSION_DENIED).")
    message: str = Field(description="Human-readable explanation of the error.")
    retryable: bool = Field(default=False, description="Whether repeating the call with backoff is viable.")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    execution_id: Optional[str] = Field(default=None, description="Unique trace identifier for this tool call.")


class MCPToolCall(BaseModel):
    """Audit record capturing an individual MCP tool invocation."""

    execution_id: str
    tool_name: str
    agent_name: str
    status: ToolExecutionStatus
    duration_ms: float
    input_metadata: Dict[str, Any] = Field(default_factory=dict, description="Sanitized arguments (zero secrets).")
    retries: int = 0
    mode: str = "DEMO"
    provider: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MCPToolResult(BaseModel):
    """Standardized wrapper for all MCP tool output responses."""

    success: bool
    tool_name: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[ToolExecutionError] = None
    latency_ms: float = 0.0
    mode: str = "DEMO"
    provider: Optional[str] = None
    demo_data: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==============================================================================
# 1. Flight MCP Schemas
# ==============================================================================

class SearchFlightsInput(BaseModel):
    """Parameters for searching scheduled air travel corridors."""

    origin: str = Field(min_length=2, max_length=50, description="Departure airport or city name.")
    destination: str = Field(min_length=2, max_length=50, description="Arrival airport or city name.")
    departure_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="Departure date in YYYY-MM-DD.")
    return_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Optional return date.")
    travellers: int = Field(default=1, ge=1, le=20, description="Passenger count.")
    cabin_class: str = Field(default="economy", description="Cabin class: economy, premium_economy, business, first.")
    max_budget: Optional[float] = Field(default=None, ge=0.0, description="Maximum ceiling budget for flights.")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="ISO currency code.")


class SearchFlightsOutput(BaseModel):
    """Structured flight search response."""

    flights: List[FlightOption] = Field(default_factory=list)
    total_found: int
    search_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provider: str = "Mock Flight Catalog"
    data_mode: str = "DEMO"
    demo_data: bool = True


class CompareFlightsInput(BaseModel):
    """Parameters to evaluate and rank flight options."""

    flight_ids: List[str] = Field(min_length=1, description="List of flight numbers or identifiers to compare.")
    sort_by: str = Field(default="price", description="Ranking metric: price, duration, stops.")


class CompareFlightsOutput(BaseModel):
    """Comparative analysis across flight alternatives."""

    comparisons: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_id: Optional[str] = None
    provider: str = "Flight Comparator"
    data_mode: str = "DEMO"
    demo_data: bool = True


class GetFlightDetailsInput(BaseModel):
    """Parameters to retrieve comprehensive itinerary for a single flight."""

    flight_id: str = Field(min_length=2, description="Flight number or carrier identifier.")


class GetFlightDetailsOutput(BaseModel):
    """Detailed flight specifications, baggage rules, and cancellation terms."""

    flight: FlightOption
    baggage_allowance: str = "1 carry-on (8kg) + 1 checked bag (23kg)"
    cancellation_policy: str = "Standard refundable with fee up to 24h before departure"
    provider: str = "Flight Detail Service"
    data_mode: str = "DEMO"
    demo_data: bool = True


# ==============================================================================
# 2. Hotel MCP Schemas
# ==============================================================================

class SearchHotelsInput(BaseModel):
    """Parameters for discovering lodging options."""

    destination: str = Field(min_length=2, max_length=50, description="Target city or neighborhood.")
    check_in: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="Check-in date.")
    check_out: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="Check-out date.")
    travellers: int = Field(default=1, ge=1, le=20, description="Guest headcount.")
    rooms: int = Field(default=1, ge=1, le=10, description="Room count required.")
    budget: Optional[float] = Field(default=None, ge=0.0, description="Total budget ceiling for lodging.")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    preferences: List[str] = Field(default_factory=list, description="Style preferences e.g. Boutique, Central.")


class SearchHotelsOutput(BaseModel):
    """Discovered lodging options."""

    hotels: List[HotelOption] = Field(default_factory=list)
    total_found: int
    provider: str = "Mock Hospitality Catalog"
    data_mode: str = "DEMO"
    demo_data: bool = True


class GetHotelDetailsInput(BaseModel):
    """Parameters to inspect property amenities and check-in logistics."""

    hotel_id: str = Field(min_length=2, description="Property identifier or name.")


class GetHotelDetailsOutput(BaseModel):
    """Detailed property information."""

    hotel: HotelOption
    policies: List[str] = Field(default_factory=lambda: ["Smoke-free property", "24/7 Front Desk concierge"])
    check_in_time: str = "15:00"
    check_out_time: str = "11:00"
    provider: str = "Hotel Detail Service"
    data_mode: str = "DEMO"
    demo_data: bool = True


# ==============================================================================
# 3. Maps MCP Schemas
# ==============================================================================

class PlaceItem(BaseModel):
    """Geographic point of interest or venue."""

    name: str
    location: str
    category: str
    rating: float = Field(ge=0.0, le=5.0)
    estimated_time_spent_hours: float = 2.0
    provider: str = "Mock Places Catalog"
    data_mode: str = "DEMO"
    demo_data: bool = True


class SearchPlacesInput(BaseModel):
    """Parameters to discover attractions and local experiences."""

    query: str = Field(min_length=2, max_length=100, description="Search term e.g. 'art museum'.")
    location: str = Field(min_length=2, max_length=50, description="Destination city.")
    category: Optional[str] = Field(default=None, description="Category filter.")
    limit: int = Field(default=5, ge=1, le=20)


class SearchPlacesOutput(BaseModel):
    """Discovered points of interest."""

    places: List[PlaceItem] = Field(default_factory=list)
    provider: str = "Mock Places Catalog"
    data_mode: str = "DEMO"
    demo_data: bool = True


class CalculateRouteInput(BaseModel):
    """Parameters for routing between waypoints."""

    origin: str = Field(min_length=2, max_length=100)
    destination: str = Field(min_length=2, max_length=100)
    mode: str = Field(default="transit", description="Transit mode: transit, driving, walking.")


class CalculateRouteOutput(BaseModel):
    """Calculated corridor distance, duration, and transit steps."""

    origin: str
    destination: str
    mode: str
    distance_km: float
    duration_minutes: int
    steps: List[str] = Field(default_factory=list)
    provider: str = "Mock Routing Service"
    data_mode: str = "DEMO"
    demo_data: bool = True


class EstimateTravelTimeInput(BaseModel):
    """Quick transit duration estimation between points."""

    origin: str = Field(min_length=2, max_length=100)
    destination: str = Field(min_length=2, max_length=100)
    mode: str = Field(default="transit")


class EstimateTravelTimeOutput(BaseModel):
    """Estimated duration and recommended safety buffer."""

    origin: str
    destination: str
    mode: str
    duration_minutes: int
    buffer_minutes: int = 15
    provider: str = "Travel Time Estimator"
    data_mode: str = "DEMO"
    demo_data: bool = True


# ==============================================================================
# 4. Weather MCP Schemas
# ==============================================================================

class GetCurrentWeatherInput(BaseModel):
    """Parameters for real-time conditions query."""

    location: str = Field(min_length=2, max_length=50)


class GetCurrentWeatherOutput(BaseModel):
    """Snapshot meteorological observations."""

    location: str
    temperature: str
    condition: str
    humidity_percent: int = 60
    wind_speed_kmh: float = 12.0
    provider: str = "Mock Climatological Service"
    data_mode: str = "DEMO"
    demo_data: bool = True


class GetForecastInput(BaseModel):
    """Parameters for multi-day weather forecasts."""

    location: str = Field(min_length=2, max_length=50)
    start_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class GetForecastOutput(BaseModel):
    """Sequential daily climatological observations."""

    location: str
    forecasts: List[WeatherObservation] = Field(default_factory=list)
    provider: str = "Mock Climatological Service"
    data_mode: str = "DEMO"
    demo_data: bool = True


class GetWeatherAlertsInput(BaseModel):
    """Parameters for meteorological hazard and storm warnings."""

    location: str = Field(min_length=2, max_length=50)


class GetWeatherAlertsOutput(BaseModel):
    """Active storm or climate advisories."""

    location: str
    alerts: List[str] = Field(default_factory=list)
    severity: str = "NONE"
    provider: str = "Mock Climatological Service"
    data_mode: str = "DEMO"
    demo_data: bool = True


# ==============================================================================
# 5. Search MCP Schemas (Untrusted Content Isolation)
# ==============================================================================

class SearchResultItem(BaseModel):
    """Individual web search snippet marked explicitly as untrusted."""

    title: str
    url: str
    snippet: str
    source_domain: Optional[str] = None
    source_type: str = Field(default="UNKNOWN", description="Source classification: OFFICIAL, NEWS, REFERENCE, COMMUNITY, UNKNOWN")
    published_at: Optional[str] = None
    retrieved_at: Optional[str] = None
    relevance_score: Optional[float] = None
    untrusted: bool = Field(default=True, description="Indicates third-party content requiring sanitization.")
    provider: str = "Mock Search Service"
    data_mode: str = "DEMO"
    demo_data: bool = True


class WebSearchInput(BaseModel):
    """Parameters for external web retrieval."""

    query: str = Field(min_length=2, max_length=150, description="Search query string.")
    destination: Optional[str] = Field(default=None, description="Optional target destination context.")
    recency: Optional[str] = Field(default=None, description="Freshness window: today, 24h, 7d, 30d, all.")
    language: str = Field(default="en", description="Target ISO language code.")
    max_results: int = Field(default=5, ge=1, le=10)
    allowed_domains: Optional[List[str]] = Field(default=None, description="Optional domain filtering allowlist.")


class WebSearchOutput(BaseModel):
    """Web search snippets."""

    query: str
    destination: Optional[str] = None
    recency: Optional[str] = None
    results: List[SearchResultItem] = Field(default_factory=list)
    provider: str = "Mock Search Service"
    data_mode: str = "DEMO"
    untrusted: bool = True
    demo_data: bool = True


class FetchPageInput(BaseModel):
    """Parameters for fetching single page content under strict URL sandboxing."""

    url: str = Field(description="Target web address. Must conform to HTTP/HTTPS protocol.")
    max_length: int = Field(default=3000, ge=200, le=10000, description="Maximum characters extracted from page.")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if not (v_clean.startswith("http://") or v_clean.startswith("https://")):
            raise ValueError("Only HTTP and HTTPS URLs are permitted.")
        for blocked in ("localhost", "127.0.0.1", "0.0.0.0", "169.254.", "10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.31."):
            if blocked in v_clean:
                raise ValueError("Requests to private/local network addresses are strictly prohibited.")
        return v.strip()


class FetchPageOutput(BaseModel):
    """Extracted text from single web page."""

    url: str
    title: str
    headings: List[str] = Field(default_factory=list)
    content: str = Field(description="Sanitized web page text body.")
    source_domain: Optional[str] = None
    source_type: str = "UNKNOWN"
    published_at: Optional[str] = None
    retrieved_at: Optional[str] = None
    provider: str = "Mock Web Fetcher"
    data_mode: str = "DEMO"
    untrusted: bool = True
    demo_data: bool = True


class SearchNewsInput(BaseModel):
    """Parameters for news and seasonal events discovery."""

    query: str = Field(min_length=2, max_length=100)
    destination: Optional[str] = Field(default=None, description="Optional target destination.")
    recency: Optional[str] = Field(default="7d", description="Freshness window: today, 24h, 7d, 30d.")
    limit: int = Field(default=3, ge=1, le=10)


class SearchNewsOutput(BaseModel):
    """Recent news headlines and events."""

    query: str
    destination: Optional[str] = None
    recency: Optional[str] = "7d"
    articles: List[Dict[str, Any]] = Field(default_factory=list)
    provider: str = "Mock News Service"
    data_mode: str = "DEMO"
    untrusted: bool = True
    demo_data: bool = True
    untrusted: bool = True
    demo_data: bool = True


# ==============================================================================
# 6. Currency MCP Schemas
# ==============================================================================

class GetExchangeRateInput(BaseModel):
    """Parameters for foreign exchange conversion calculation."""

    base_currency: str = Field(default="USD", min_length=3, max_length=3, description="Source ISO currency code.")
    target_currency: str = Field(default="USD", min_length=3, max_length=3, description="Target ISO currency code.")

    @field_validator("base_currency", "target_currency")
    @classmethod
    def uppercase_currency(cls, v: str) -> str:
        return v.upper().strip()


class GetExchangeRateOutput(BaseModel):
    """Normalized currency conversion quote."""

    base_currency: str
    target_currency: str
    exchange_rate: float = Field(ge=0.0)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provider: str = "Mock Currency Catalog"
    data_mode: str = "DEMO"
    demo_data: bool = True
