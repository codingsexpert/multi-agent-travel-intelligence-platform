"""Currency MCP tools implementing foreign exchange rate calculation and conversions."""

from datetime import datetime, timezone
from models.mcp import GetExchangeRateInput, GetExchangeRateOutput

# Deterministic benchmark exchange rates relative to USD (1.0 USD = X Currency)
USD_BASE_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.78,
    "INR": 83.5,
    "JPY": 155.0,
    "AUD": 1.52,
    "CAD": 1.36,
    "CHF": 0.89,
    "SGD": 1.35,
}


def mcp_get_exchange_rate(params: GetExchangeRateInput) -> GetExchangeRateOutput:
    """Retrieve normalized foreign exchange conversion rate between base and target currency."""
    base = params.base_currency.upper()
    target = params.target_currency.upper()

    if base == target:
        rate = 1.0
    else:
        base_to_usd = 1.0 / USD_BASE_RATES.get(base, 1.0)
        target_from_usd = USD_BASE_RATES.get(target, 1.0)
        rate = round(base_to_usd * target_from_usd, 4)

    return GetExchangeRateOutput(
        base_currency=base,
        target_currency=target,
        exchange_rate=rate,
        timestamp=datetime.now(timezone.utc).isoformat(),
        demo_data=True,
    )
