"""Hotel Provider Adapter integrating Amadeus Hospitality Search API with OAuth2, caching, and mock fallbacks."""

import time
from datetime import date, datetime, timezone
from typing import Dict, Any, List, Optional

from config.settings import settings
from models.specialized_options import HotelOption
from models.mcp import (
    SearchHotelsInput,
    SearchHotelsOutput,
    GetHotelDetailsInput,
    GetHotelDetailsOutput,
)
from mcp.providers.base import (
    BaseProvider,
    ProviderError,
    ProviderConfigurationError,
    ProviderAuthenticationError,
    ProviderNetworkError,
    ProviderResponseValidationError,
    get_effective_demo_mode,
)
from mcp.providers.cache import ProviderCache
from utils.logger import logger

# City to IATA / Amadeus City Code mapping
CITY_HOTEL_CODES: Dict[str, str] = {
    "tokyo": "TYO",
    "paris": "PAR",
    "london": "LON",
    "new york": "NYC",
    "rome": "ROM",
    "singapore": "SIN",
    "dubai": "DXB",
    "sydney": "SYD",
    "bali": "DPS",
    "barcelona": "BCN",
    "amsterdam": "AMS",
}


class HotelProvider(BaseProvider):
    """Adapter for hospitality searches and lodging specifications."""

    def __init__(self, base_url: str = "https://test.api.amadeus.com"):
        super().__init__(provider_name="Amadeus Hospitality", base_url=base_url)
        self.cache = ProviderCache(default_ttl_seconds=1800)  # 30 minute cache
        self._oauth_token: Optional[str] = None
        self._oauth_token_expiry: float = 0.0

    def _resolve_city_code(self, destination: str) -> str:
        """Map destination city name to 3-letter IATA city code."""
        dest_clean = destination.lower().strip()
        for city, code in CITY_HOTEL_CODES.items():
            if city in dest_clean:
                return code
        return dest_clean[:3].upper() if len(dest_clean) >= 3 else "PAR"

    def _get_oauth_token(self) -> str:
        """Retrieve valid OAuth2 Bearer token from Amadeus."""
        if not settings.has_amadeus_config:
            raise ProviderConfigurationError(
                message="Amadeus Hotel API credentials missing. Set AMADEUS_CLIENT_ID and "
                "AMADEUS_CLIENT_SECRET in .env or switch to DEMO_MODE=true.",
                provider=self.provider_name,
            )

        now = time.time()
        if self._oauth_token and now < self._oauth_token_expiry:
            return self._oauth_token

        token_url = f"{self.base_url}/v1/security/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        body = {
            "grant_type": "client_credentials",
            "client_id": settings.amadeus_client_id,
            "client_secret": settings.amadeus_client_secret,
        }

        try:
            with self.execute_http_request(
                method="POST",
                url=token_url,
                headers=headers,
                params=body,
                timeout=6.0,
            ) as resp:
                data = resp.json()
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderAuthenticationError(
                f"Failed to obtain Amadeus OAuth2 token: {str(e)}",
                provider=self.provider_name,
            )

        access_token = data.get("access_token")
        expires_in = data.get("expires_in", 1799)
        if not access_token:
            raise ProviderAuthenticationError("OAuth token response missing 'access_token'.", provider=self.provider_name)

        self._oauth_token = access_token
        self._oauth_token_expiry = now + float(expires_in) - 60.0
        return self._oauth_token

    def search_hotels(
        self,
        params: SearchHotelsInput,
        demo_mode: Optional[bool] = None,
    ) -> SearchHotelsOutput:
        """Search lodging alternatives matching geographic and budgetary criteria."""
        is_demo = get_effective_demo_mode(demo_mode)

        try:
            s_dt = date.fromisoformat(params.check_in)
            e_dt = date.fromisoformat(params.check_out)
            nights = max((e_dt - s_dt).days, 1)
        except Exception:
            nights = 5

        # DEMO MODE: Return deterministic mock hotel catalog
        if is_demo:
            base_nightly = 160.0 if params.currency == "USD" else 12500.0
            hotels = [
                HotelOption(
                    name=f"The Grand Heritage Hotel {params.destination.title()}",
                    location=f"Central District, {params.destination.title()}",
                    rating=4.7,
                    price_per_night=base_nightly,
                    total_price=round(base_nightly * nights * params.rooms, 2),
                    currency=params.currency,
                    amenities=["High-Speed Wi-Fi", "Daily Breakfast Buffet", "Fitness Center & Spa", "24/7 Concierge"],
                    source="[DEMO_DATA] Hotel MCP Server (Mock Lodging Aggregator)",
                    availability_status="AVAILABLE (MOCK)",
                    demo_data=True,
                ),
                HotelOption(
                    name=f"{params.destination.title()} Boutique Suites & Terrace",
                    location=f"Historic Quarter, {params.destination.title()}",
                    rating=4.5,
                    price_per_night=round(base_nightly * 0.82, 2),
                    total_price=round(base_nightly * 0.82 * nights * params.rooms, 2),
                    currency=params.currency,
                    amenities=["Complimentary Espresso Bar", "City View Terrace", "Bicycle Rental", "Eco-Certified"],
                    source="[DEMO_DATA] Hotel MCP Server (Mock Lodging Aggregator)",
                    availability_status="AVAILABLE (MOCK)",
                    demo_data=True,
                ),
            ]
            return SearchHotelsOutput(
                hotels=hotels,
                total_found=len(hotels),
                provider="Mock Hospitality Catalog",
                data_mode="DEMO",
                demo_data=True,
            )

        # LIVE MODE: Verify credentials
        if not settings.has_amadeus_config:
            raise ProviderConfigurationError(
                message="Amadeus Hotel API credentials missing. Set AMADEUS_CLIENT_ID and "
                "AMADEUS_CLIENT_SECRET in .env or switch to DEMO_MODE=true.",
                provider=self.provider_name,
            )

        city_code = self._resolve_city_code(params.destination)
        cache_key = f"ht_{city_code}_{params.check_in}_{params.check_out}_{params.rooms}_{params.currency}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        token = self._get_oauth_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/v1/reference-data/locations/hotels/by-city"
        query_params = {
            "cityCode": city_code,
            "radius": 20,
            "radiusUnit": "KM",
            "hotelSource": "ALL",
        }

        try:
            resp = self.execute_http_request(
                method="GET",
                url=url,
                headers=headers,
                params=query_params,
                timeout=8.0,
            )
            data = resp.json()
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderNetworkError(f"Amadeus Hotel discovery failed: {str(e)}", provider=self.provider_name)

        hotel_list = data.get("data", [])
        hotels: List[HotelOption] = []

        base_nightly = 185.0 if params.currency == "USD" else 15000.0

        for idx, h in enumerate(hotel_list[:5]):
            h_name = h.get("name", f"Hotel {city_code} {idx + 1}").title()
            h_id = h.get("hotelId", f"HOTEL-{idx}")
            rating = 4.0 + (idx % 8) * 0.1
            nightly = round(base_nightly * (1.0 + (idx * 0.15)), 2)
            tot_price = round(nightly * nights * params.rooms, 2)

            hotels.append(
                HotelOption(
                    name=h_name,
                    location=f"{params.destination.title()} Central Area",
                    rating=min(rating, 4.9),
                    stars=4 if rating < 4.5 else 5,
                    price_per_night=nightly,
                    total_price=tot_price,
                    currency=params.currency,
                    amenities=["Wi-Fi", "Breakfast Included", "Air Conditioning", "24/7 Desk"],
                    room_type="Standard Room",
                    source="Amadeus Hospitality [LIVE]",
                    availability_status="Available",
                    demo_data=False,
                )
            )

        if not hotels:
            raise ProviderResponseValidationError(
                f"No verified accommodations found in {params.destination} via Amadeus.",
                provider=self.provider_name,
            )

        result = SearchHotelsOutput(
            hotels=hotels,
            total_found=len(hotels),
            provider=self.provider_name,
            data_mode="LIVE",
            demo_data=False,
        )
        self.cache.set(cache_key, result, ttl_seconds=1800)
        return result

    def get_hotel_details(
        self,
        params: GetHotelDetailsInput,
        demo_mode: Optional[bool] = None,
    ) -> GetHotelDetailsOutput:
        """Retrieve detailed property specifications and check-in logistics."""
        is_demo = get_effective_demo_mode(demo_mode)

        hotel_opt = HotelOption(
            name=params.hotel_id,
            location="Prime District Center",
            rating=4.8,
            price_per_night=180.0,
            total_price=900.0,
            currency="USD",
            amenities=["Rooftop Pool", "Michelin-Starred Restaurant", "Free Airport Shuttle"],
            source="[DEMO_DATA] Hotel MCP Server" if is_demo else "Amadeus Hospitality [LIVE]",
            availability_status="AVAILABLE (MOCK)" if is_demo else "Available",
            demo_data=is_demo,
        )

        return GetHotelDetailsOutput(
            hotel=hotel_opt,
            policies=[
                "Cancellation permitted up to 48 hours prior to arrival",
                "Valid government ID and credit card required at check-in",
                "Pet friendly rooms available upon request",
            ],
            check_in_time="15:00",
            check_out_time="11:00",
            provider="Hotel Detail Service" if is_demo else self.provider_name,
            data_mode="DEMO" if is_demo else "LIVE",
            demo_data=is_demo,
        )


# Global singleton provider instance
hotel_provider = HotelProvider()
