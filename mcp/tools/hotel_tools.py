"""Hotel MCP tools delegating to the Hotel Provider adapter."""

from models.mcp import (
    SearchHotelsInput,
    SearchHotelsOutput,
    GetHotelDetailsInput,
    GetHotelDetailsOutput,
)
from mcp.providers.hotel_provider import hotel_provider


def mcp_search_hotels(params: SearchHotelsInput) -> SearchHotelsOutput:
    """Discover lodging alternatives matching geographic and budgetary criteria."""
    return hotel_provider.search_hotels(params)


def mcp_get_hotel_details(params: GetHotelDetailsInput) -> GetHotelDetailsOutput:
    """Retrieve detailed property specifications and check-in logistics."""
    return hotel_provider.get_hotel_details(params)
