"""Currency MCP tools delegating to the Currency Provider adapter."""

from models.mcp import GetExchangeRateInput, GetExchangeRateOutput
from mcp.providers.currency_provider import currency_provider


def mcp_get_exchange_rate(params: GetExchangeRateInput) -> GetExchangeRateOutput:
    """Retrieve normalized foreign exchange conversion rate between base and target currency."""
    return currency_provider.get_exchange_rate(
        base_currency=params.base_currency,
        target_currency=params.target_currency,
    )
