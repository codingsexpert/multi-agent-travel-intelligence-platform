"""Currency Provider Adapter integrating Frankfurter (ECB open exchange rates) and mock fallbacks."""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from config.settings import settings
from models.mcp import GetExchangeRateInput, GetExchangeRateOutput
from mcp.providers.base import (
    BaseProvider,
    ProviderError,
    ProviderResponseValidationError,
    ProviderNetworkError,
    get_effective_demo_mode,
)
from mcp.providers.cache import ProviderCache
from utils.logger import logger

# Deterministic benchmark exchange rates relative to USD (1.0 USD = X Currency) for DEMO mode
USD_BASE_RATES: Dict[str, float] = {
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


class CurrencyProvider(BaseProvider):
    """Adapter for foreign exchange rate queries supporting live Frankfurter (ECB) data and caching."""

    def __init__(self, base_url: str = "https://api.frankfurter.dev/v1"):
        super().__init__(provider_name="Frankfurter (ECB)", base_url=base_url)
        self.cache = ProviderCache(default_ttl_seconds=3600)  # 1 hour cache

    def get_exchange_rate(
        self,
        base_currency: str,
        target_currency: str,
        demo_mode: Optional[bool] = None,
    ) -> GetExchangeRateOutput:
        """Retrieve foreign exchange conversion rate between base and target currency.

        Args:
            base_currency: 3-letter ISO base currency code (e.g., 'USD').
            target_currency: 3-letter ISO target currency code (e.g., 'EUR').
            demo_mode: Override settings.demo_mode if specified.

        Returns:
            GetExchangeRateOutput containing rate, timestamps, and provider attribution.
        """
        is_demo = get_effective_demo_mode(demo_mode)
        base = base_currency.upper().strip()
        target = target_currency.upper().strip()

        # Identity exchange
        if base == target:
            return GetExchangeRateOutput(
                base_currency=base,
                target_currency=target,
                exchange_rate=1.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                provider=self.provider_name if not is_demo else "Mock Currency Catalog",
                data_mode="DEMO" if is_demo else "LIVE",
                demo_data=is_demo,
            )

        # DEMO Mode execution
        if is_demo:
            base_to_usd = 1.0 / USD_BASE_RATES.get(base, 1.0)
            target_from_usd = USD_BASE_RATES.get(target, 1.0)
            rate = round(base_to_usd * target_from_usd, 4)

            return GetExchangeRateOutput(
                base_currency=base,
                target_currency=target,
                exchange_rate=rate,
                timestamp=datetime.now(timezone.utc).isoformat(),
                provider="Mock Currency Catalog",
                data_mode="DEMO",
                demo_data=True,
            )

        # LIVE Mode execution with caching
        cache_key = f"fx_{base}_{target}"
        cached_rate = self.cache.get(cache_key)
        if cached_rate is not None:
            logger.info(f"[{self.provider_name}] Cache hit for {base}->{target}: {cached_rate}")
            return GetExchangeRateOutput(
                base_currency=base,
                target_currency=target,
                exchange_rate=cached_rate,
                timestamp=datetime.now(timezone.utc).isoformat(),
                provider=self.provider_name,
                data_mode="LIVE",
                demo_data=False,
            )

        # External HTTP Query to Frankfurter ECB API
        url = f"{self.base_url}/latest"
        params = {"base": base, "symbols": target}

        try:
            resp = self.execute_http_request(method="GET", url=url, params=params, timeout=5.0)
            data = resp.json()
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderNetworkError(f"Failed to query currency exchange rates: {str(e)}", provider=self.provider_name)

        rates = data.get("rates", {})
        if target not in rates:
            raise ProviderResponseValidationError(
                f"Target currency '{target}' not present in provider rates response.",
                provider=self.provider_name,
            )

        try:
            rate_val = float(rates[target])
        except (ValueError, TypeError) as ve:
            raise ProviderResponseValidationError(
                f"Invalid rate value for {target}: {str(ve)}",
                provider=self.provider_name,
            )

        self.cache.set(cache_key, rate_val, ttl_seconds=3600)

        return GetExchangeRateOutput(
            base_currency=base,
            target_currency=target,
            exchange_rate=rate_val,
            timestamp=datetime.now(timezone.utc).isoformat(),
            provider=self.provider_name,
            data_mode="LIVE",
            demo_data=False,
        )


# Global singleton provider instance
currency_provider = CurrencyProvider()
