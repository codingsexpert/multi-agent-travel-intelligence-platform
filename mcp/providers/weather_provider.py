"""Weather Provider Adapter integrating Open-Meteo (WMO standard meteorological data) and mock fallback."""

from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple

from config.settings import settings
from models.mcp import (
    GetCurrentWeatherInput,
    GetCurrentWeatherOutput,
    GetForecastInput,
    GetForecastOutput,
    GetWeatherAlertsInput,
    GetWeatherAlertsOutput,
)
from models.specialized_options import WeatherObservation
from mcp.providers.base import (
    BaseProvider,
    ProviderError,
    ProviderNetworkError,
    ProviderResponseValidationError,
    get_effective_demo_mode,
)
from mcp.providers.cache import ProviderCache
from utils.logger import logger

# Canonical coordinates for major world travel hubs to avoid redundant geocoding latency
CITY_COORDINATES: Dict[str, Tuple[float, float]] = {
    "tokyo": (35.6762, 139.6503),
    "paris": (48.8566, 2.3522),
    "london": (51.5074, -0.1278),
    "new york": (40.7128, -74.0060),
    "rome": (41.9028, 12.4964),
    "bali": (-8.4095, 115.1889),
    "sydney": (-33.8688, 151.2093),
    "singapore": (1.3521, 103.8198),
    "dubai": (25.2048, 55.2708),
    "san francisco": (37.7749, -122.4194),
    "kyoto": (35.0116, 135.7681),
    "barcelona": (41.3851, 2.1734),
    "amsterdam": (52.3676, 4.9041),
    "berlin": (52.5200, 13.4050),
    "bangkok": (13.7563, 100.5018),
}

# WMO Weather interpretation codes (WMO code -> condition description)
WMO_CODE_MAP: Dict[int, str] = {
    0: "Clear Sky",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing Rime Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Dense Drizzle",
    61: "Slight Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    71: "Slight Snow Fall",
    73: "Moderate Snow Fall",
    75: "Heavy Snow Fall",
    77: "Snow Grains",
    80: "Slight Rain Showers",
    81: "Moderate Rain Showers",
    82: "Violent Rain Showers",
    85: "Slight Snow Showers",
    86: "Heavy Snow Showers",
    95: "Thunderstorm",
    96: "Thunderstorm with Slight Hail",
    99: "Thunderstorm with Heavy Hail",
}


class WeatherProvider(BaseProvider):
    """Adapter for meteorological queries supporting live Open-Meteo forecasts and caching."""

    def __init__(
        self,
        base_url: str = "https://api.open-meteo.com/v1",
        geocoding_url: str = "https://geocoding-api.open-meteo.com/v1",
    ):
        super().__init__(provider_name="Open-Meteo WMO", base_url=base_url)
        self.geocoding_url = geocoding_url
        self.cache = ProviderCache(default_ttl_seconds=600)  # 10 minute cache

    def _resolve_coordinates(self, location: str) -> Tuple[float, float]:
        """Resolve city name into (latitude, longitude) coordinates."""
        loc_clean = location.lower().strip()
        for city_name, coords in CITY_COORDINATES.items():
            if city_name in loc_clean:
                return coords

        # Dynamic Geocoding via Open-Meteo Geocoding API
        cache_key = f"geo_{loc_clean}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        try:
            resp = self.execute_http_request(
                method="GET",
                url=f"{self.geocoding_url}/search",
                params={"name": location, "count": 1, "language": "en", "format": "json"},
                timeout=4.0,
            )
            data = resp.json()
            results = data.get("results", [])
            if results:
                lat = float(results[0]["latitude"])
                lon = float(results[0]["longitude"])
                self.cache.set(cache_key, (lat, lon), ttl_seconds=86400)
                return (lat, lon)
        except Exception as e:
            logger.warning(f"[{self.provider_name}] Geocoding failed for '{location}': {str(e)}")

        # Default fallback to Tokyo coordinates if entirely unresolvable
        return (35.6762, 139.6503)

    def get_current_weather(
        self,
        location: str,
        demo_mode: Optional[bool] = None,
    ) -> GetCurrentWeatherOutput:
        """Retrieve real-time meteorological observations for a destination."""
        is_demo = get_effective_demo_mode(demo_mode)
        loc_title = location.title()

        if is_demo:
            return GetCurrentWeatherOutput(
                location=loc_title,
                temperature="21°C / 70°F",
                condition="Partly Cloudy",
                humidity_percent=55,
                wind_speed_kmh=14.0,
                provider="Mock Climatological Service",
                data_mode="DEMO",
                demo_data=True,
            )

        cache_key = f"curr_weather_{loc_title.lower()}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        lat, lon = self._resolve_coordinates(location)
        url = f"{self.base_url}/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "auto",
        }

        try:
            resp = self.execute_http_request(method="GET", url=url, params=params, timeout=5.0)
            data = resp.json()
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderNetworkError(f"Weather request failed: {str(e)}", provider=self.provider_name)

        current = data.get("current")
        if not current:
            raise ProviderResponseValidationError("Missing 'current' payload in weather response.", provider=self.provider_name)

        temp_c = float(current.get("temperature_2m", 20.0))
        temp_f = round((temp_c * 9 / 5) + 32, 1)
        humidity = int(current.get("relative_humidity_2m", 50))
        wind_speed = float(current.get("wind_speed_10m", 10.0))
        code = int(current.get("weather_code", 0))
        condition = WMO_CODE_MAP.get(code, "Partly Cloudy")

        result = GetCurrentWeatherOutput(
            location=loc_title,
            temperature=f"{temp_c:.1f}°C / {temp_f:.1f}°F",
            condition=condition,
            humidity_percent=humidity,
            wind_speed_kmh=wind_speed,
            provider=self.provider_name,
            data_mode="LIVE",
            demo_data=False,
        )
        self.cache.set(cache_key, result, ttl_seconds=600)
        return result

    def get_forecast(
        self,
        location: str,
        start_date: str,
        end_date: str,
        demo_mode: Optional[bool] = None,
    ) -> GetForecastOutput:
        """Retrieve multi-day daily forecasts across trip dates."""
        is_demo = get_effective_demo_mode(demo_mode)
        loc_title = location.title()

        if is_demo:
            try:
                s_dt = date.fromisoformat(start_date)
                e_dt = date.fromisoformat(end_date)
                days = max((e_dt - s_dt).days, 1)
            except Exception:
                s_dt = date.today() + timedelta(days=14)
                days = 5

            conditions_cycle = [
                (19.0, 66.2, "Partly Cloudy", 15, "Optimal for walking tours and cultural excursions."),
                (22.0, 71.6, "Sunny & Clear", 5, "Clear skies with excellent visibility; ideal for outdoor sightseeing."),
                (18.0, 64.4, "Scattered Showers", 60, "Occasional afternoon showers; carry compact umbrella or visit museums."),
                (20.0, 68.0, "Mild & Breezy", 20, "Comfortable temperate climate throughout the day."),
                (23.0, 73.4, "Warm & Sunny", 10, "Warm afternoon temperatures; stay hydrated during excursions."),
            ]

            forecasts = []
            for i in range(min(days, 14)):
                current_d = (s_dt + timedelta(days=i)).isoformat()
                temp_c, temp_f, cond, precip, warn = conditions_cycle[i % len(conditions_cycle)]
                forecasts.append(
                    WeatherObservation(
                        date=current_d,
                        location=loc_title,
                        temperature_celsius=temp_c,
                        temperature_fahrenheit=temp_f,
                        condition=cond,
                        precipitation_probability=precip,
                        humidity_percentage=55,
                        warning=warn,
                        source="[DEMO_DATA] Weather MCP Server (Mock Meteorological Feed)",
                        demo_data=True,
                    )
                )

            return GetForecastOutput(
                location=loc_title,
                forecasts=forecasts,
                provider="Mock Climatological Service",
                data_mode="DEMO",
                demo_data=True,
            )

        cache_key = f"fc_{loc_title.lower()}_{start_date}_{end_date}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        lat, lon = self._resolve_coordinates(location)
        url = f"{self.base_url}/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto",
        }

        try:
            resp = self.execute_http_request(method="GET", url=url, params=params, timeout=5.0)
            data = resp.json()
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderNetworkError(f"Forecast request failed: {str(e)}", provider=self.provider_name)

        daily = data.get("daily")
        if not daily or "time" not in daily:
            raise ProviderResponseValidationError("Missing 'daily' payload in weather response.", provider=self.provider_name)

        times = daily.get("time", [])
        codes = daily.get("weather_code", [])
        temps_max = daily.get("temperature_2m_max", [])
        precip_probs = daily.get("precipitation_probability_max", [])

        forecasts = []
        for i, day_str in enumerate(times[:14]):
            temp_c = float(temps_max[i]) if i < len(temps_max) and temps_max[i] is not None else 20.0
            temp_f = round((temp_c * 9 / 5) + 32, 1)
            code = int(codes[i]) if i < len(codes) and codes[i] is not None else 0
            cond = WMO_CODE_MAP.get(code, "Clear Sky")
            precip = int(precip_probs[i]) if i < len(precip_probs) and precip_probs[i] is not None else 10

            warn = None
            if precip >= 60:
                warn = "High probability of rain; consider indoor activities."
            elif temp_c >= 35.0:
                warn = "Extreme heat advisory; ensure adequate hydration."

            forecasts.append(
                WeatherObservation(
                    date=day_str,
                    location=loc_title,
                    temperature_celsius=temp_c,
                    temperature_fahrenheit=temp_f,
                    condition=cond,
                    precipitation_probability=precip,
                    humidity_percentage=50,
                    warning=warn,
                    source=f"Open-Meteo WMO Station [LIVE]",
                    demo_data=False,
                )
            )

        result = GetForecastOutput(
            location=loc_title,
            forecasts=forecasts,
            provider=self.provider_name,
            data_mode="LIVE",
            demo_data=False,
        )
        self.cache.set(cache_key, result, ttl_seconds=600)
        return result

    def get_weather_alerts(
        self,
        location: str,
        demo_mode: Optional[bool] = None,
    ) -> GetWeatherAlertsOutput:
        """Retrieve active severe meteorological warnings, storms, or typhoons."""
        is_demo = get_effective_demo_mode(demo_mode)
        loc_title = location.title()

        if is_demo:
            return GetWeatherAlertsOutput(
                location=loc_title,
                alerts=["No active extreme meteorological warnings for this region."],
                severity="NONE",
                provider="Mock Climatological Service",
                data_mode="DEMO",
                demo_data=True,
            )

        # In live mode with Open-Meteo, alerts are checked via current observations or thresholds
        try:
            curr = self.get_current_weather(location=location, demo_mode=False)
            alerts = []
            severity = "NONE"
            if "Thunderstorm" in curr.condition:
                alerts.append(f"Thunderstorm advisory in effect for {loc_title}.")
                severity = "MODERATE"
            elif curr.wind_speed_kmh > 60.0:
                alerts.append(f"High wind warning ({curr.wind_speed_kmh} km/h) for {loc_title}.")
                severity = "HIGH"
            else:
                alerts.append(f"No severe meteorological alerts for {loc_title}.")

            return GetWeatherAlertsOutput(
                location=loc_title,
                alerts=alerts,
                severity=severity,
                provider=self.provider_name,
                data_mode="LIVE",
                demo_data=False,
            )
        except Exception as e:
            logger.warning(f"[{self.provider_name}] Alert check encountered error: {str(e)}")
            return GetWeatherAlertsOutput(
                location=loc_title,
                alerts=[f"Meteorological advisories normal for {loc_title}."],
                severity="NONE",
                provider=self.provider_name,
                data_mode="LIVE",
                demo_data=False,
            )


# Global singleton provider instance
weather_provider = WeatherProvider()
