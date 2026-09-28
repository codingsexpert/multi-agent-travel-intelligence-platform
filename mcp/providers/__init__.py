"""Model Context Protocol (MCP) External Provider Adapters and Infrastructure."""

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
from mcp.providers.currency_provider import CurrencyProvider, currency_provider
from mcp.providers.weather_provider import WeatherProvider, weather_provider
from mcp.providers.maps_provider import MapsProvider, maps_provider
from mcp.providers.search_provider import SearchProvider, search_provider
from mcp.providers.flight_provider import FlightProvider, flight_provider
from mcp.providers.hotel_provider import HotelProvider, hotel_provider

__all__ = [
    "BaseProvider",
    "ProviderError",
    "ProviderConfigurationError",
    "ProviderAuthenticationError",
    "ProviderRateLimitError",
    "ProviderTimeoutError",
    "ProviderNetworkError",
    "ProviderResponseValidationError",
    "SourceAttribution",
    "ProviderCache",
    "CurrencyProvider",
    "currency_provider",
    "WeatherProvider",
    "weather_provider",
    "MapsProvider",
    "maps_provider",
    "SearchProvider",
    "search_provider",
    "FlightProvider",
    "flight_provider",
    "HotelProvider",
    "hotel_provider",
]
