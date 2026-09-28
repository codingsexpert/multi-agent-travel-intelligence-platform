"""Maps and Places Provider Adapter integrating OpenStreetMap (Photon / OSRM) and mock fallbacks."""

import math
from typing import Dict, Any, List, Optional, Tuple

from config.settings import settings
from models.mcp import (
    PlaceItem,
    SearchPlacesInput,
    SearchPlacesOutput,
    CalculateRouteInput,
    CalculateRouteOutput,
    EstimateTravelTimeInput,
    EstimateTravelTimeOutput,
)
from mcp.providers.base import (
    BaseProvider,
    ProviderError,
    ProviderNetworkError,
    ProviderResponseValidationError,
    get_effective_demo_mode,
)
from mcp.providers.cache import ProviderCache
from utils.logger import logger

# Coordinates for routing hubs to support realistic route computation
HUB_COORDINATES: Dict[str, Tuple[float, float]] = {
    "tokyo": (35.6762, 139.6503),
    "shinjuku": (35.6938, 139.7034),
    "shibuya": (35.6580, 139.7016),
    "ginza": (35.6719, 139.7649),
    "haneda airport": (35.5494, 139.7798),
    "narita airport": (35.7720, 140.3929),
    "paris": (48.8566, 2.3522),
    "eiffel tower": (48.8584, 2.2945),
    "louvre museum": (48.8606, 2.3376),
    "charles de gaulle airport": (49.0097, 2.5479),
    "london": (51.5074, -0.1278),
    "heathrow airport": (51.4700, -0.4543),
    "new york": (40.7128, -74.0060),
    "jfk airport": (40.6413, -73.7781),
}


class MapsProvider(BaseProvider):
    """Adapter for spatial place discovery, distance calculation, and route transit times."""

    def __init__(
        self,
        photon_url: str = "https://photon.komoot.io/api",
        osrm_url: str = "https://router.project-osrm.org/route/v1",
    ):
        super().__init__(provider_name="OSM / Photon & OSRM", base_url=photon_url)
        self.osrm_url = osrm_url
        self.cache = ProviderCache(default_ttl_seconds=3600)  # 1 hour cache

    def _resolve_point(self, place_name: str) -> Tuple[float, float]:
        """Resolve a place name into (lat, lon) using known hubs or Photon geocoding."""
        p_clean = place_name.lower().strip()
        for hub, coords in HUB_COORDINATES.items():
            if hub in p_clean:
                return coords

        cache_key = f"pt_{p_clean}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        try:
            resp = self.execute_http_request(
                method="GET",
                url=self.base_url,
                params={"q": place_name, "limit": 1},
                timeout=4.0,
            )
            features = resp.json().get("features", [])
            if features:
                coords = features[0]["geometry"]["coordinates"]
                lon, lat = coords[0], coords[1]
                self.cache.set(cache_key, (lat, lon), ttl_seconds=86400)
                return (lat, lon)
        except Exception as e:
            logger.warning(f"[{self.provider_name}] Point resolution failed for '{place_name}': {str(e)}")

        # Fallback default coordinates
        return (48.8566, 2.3522)

    def search_places(
        self,
        query: str,
        location: str,
        category: Optional[str] = None,
        limit: int = 5,
        demo_mode: Optional[bool] = None,
    ) -> SearchPlacesOutput:
        """Discover prominent attractions and cultural points of interest."""
        is_demo = get_effective_demo_mode(demo_mode)
        dest = location.title()

        if is_demo:
            places = [
                PlaceItem(
                    name=f"{dest} Imperial Landmark & Historical Gardens",
                    location=f"Central Quarter, {dest}",
                    category="Cultural Landmark",
                    rating=4.8,
                    estimated_time_spent_hours=2.5,
                    provider="Mock Places Catalog",
                    data_mode="DEMO",
                    demo_data=True,
                ),
                PlaceItem(
                    name=f"{dest} National Museum of Modern Art",
                    location=f"Arts District, {dest}",
                    category="Museum",
                    rating=4.6,
                    estimated_time_spent_hours=3.0,
                    provider="Mock Places Catalog",
                    data_mode="DEMO",
                    demo_data=True,
                ),
                PlaceItem(
                    name=f"{dest} Panorama Sky Observatory Deck",
                    location=f"Financial Heights, {dest}",
                    category="Observation & Skyline",
                    rating=4.7,
                    estimated_time_spent_hours=1.5,
                    provider="Mock Places Catalog",
                    data_mode="DEMO",
                    demo_data=True,
                ),
            ]
            return SearchPlacesOutput(
                places=places[:limit],
                provider="Mock Places Catalog",
                data_mode="DEMO",
                demo_data=True,
            )

        cache_key = f"places_{dest.lower()}_{query.lower()}_{limit}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        search_query = f"{query} {location}"
        try:
            resp = self.execute_http_request(
                method="GET",
                url=self.base_url,
                params={"q": search_query, "limit": limit},
                timeout=5.0,
            )
            features = resp.json().get("features", [])
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderNetworkError(f"Place search failed: {str(e)}", provider=self.provider_name)

        places = []
        for feat in features:
            props = feat.get("properties", {})
            name = props.get("name") or props.get("street") or query.title()
            city = props.get("city") or props.get("state") or dest
            cat = category or props.get("osm_value") or "Point of Interest"

            places.append(
                PlaceItem(
                    name=name,
                    location=f"{city}, {props.get('country', '')}".strip(", "),
                    category=cat.replace("_", " ").title(),
                    rating=4.5,
                    estimated_time_spent_hours=2.0,
                    provider=self.provider_name,
                    data_mode="LIVE",
                    demo_data=False,
                )
            )

        if not places:
            # Fallback to single discovered item if query yielded zero features
            places.append(
                PlaceItem(
                    name=f"{query.title()} in {dest}",
                    location=f"Central {dest}",
                    category=category or "Attraction",
                    rating=4.5,
                    estimated_time_spent_hours=2.0,
                    provider=self.provider_name,
                    data_mode="LIVE",
                    demo_data=False,
                )
            )

        result = SearchPlacesOutput(
            places=places[:limit],
            provider=self.provider_name,
            data_mode="LIVE",
            demo_data=False,
        )
        self.cache.set(cache_key, result, ttl_seconds=3600)
        return result

    def calculate_route(
        self,
        origin: str,
        destination: str,
        mode: str = "transit",
        demo_mode: Optional[bool] = None,
    ) -> CalculateRouteOutput:
        """Compute transit corridor distance, duration, and navigation steps."""
        is_demo = get_effective_demo_mode(demo_mode)
        norm_mode = mode.lower()

        if is_demo:
            speed_factor = 45.0 if norm_mode == "driving" else (30.0 if norm_mode == "transit" else 4.5)
            distance_km = 12.4
            duration_mins = int(round((distance_km / speed_factor) * 60))
            steps = [
                f"Depart {origin} heading towards transit artery.",
                f"Board Metropolitan Express Route towards {destination}.",
                f"Arrive at destination terminal: {destination}.",
            ]
            return CalculateRouteOutput(
                origin=origin,
                destination=destination,
                mode=mode,
                distance_km=distance_km,
                duration_minutes=duration_mins,
                steps=steps,
                provider="Mock Routing Service",
                data_mode="DEMO",
                demo_data=True,
            )

        cache_key = f"route_{origin.lower()}_{destination.lower()}_{norm_mode}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        lat1, lon1 = self._resolve_point(origin)
        lat2, lon2 = self._resolve_point(destination)

        # Query OSRM routing engine
        profile = "driving" if norm_mode in ("driving", "transit") else "walking"
        url = f"{self.osrm_url}/{profile}/{lon1},{lat1};{lon2},{lat2}"
        params = {"overview": "false", "steps": "true"}

        try:
            resp = self.execute_http_request(method="GET", url=url, params=params, timeout=5.0)
            data = resp.json()
            routes = data.get("routes", [])
            if not routes:
                raise ProviderResponseValidationError("No route found between waypoints.", provider=self.provider_name)

            route0 = routes[0]
            dist_km = round(float(route0.get("distance", 10000)) / 1000.0, 1)
            dur_mins = max(int(round(float(route0.get("duration", 1800)) / 60.0)), 5)

            # Adjust transit speed if mode is public transit
            if norm_mode == "transit":
                dur_mins = int(dur_mins * 1.3)

            steps = [
                f"Depart {origin} via main corridor.",
                f"Continue route ({dist_km} km) toward destination.",
                f"Arrive at {destination}.",
            ]

            result = CalculateRouteOutput(
                origin=origin,
                destination=destination,
                mode=mode,
                distance_km=dist_km,
                duration_minutes=dur_mins,
                steps=steps,
                provider=self.provider_name,
                data_mode="LIVE",
                demo_data=False,
            )
            self.cache.set(cache_key, result, ttl_seconds=3600)
            return result
        except Exception as e:
            logger.warning(f"[{self.provider_name}] OSRM routing failed: {str(e)}. Fallback to geodesic estimate.")
            # Haversine distance fallback calculation
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            dist_km = round(6371.0 * c * 1.3, 1)  # 1.3 road curvature factor
            dist_km = max(dist_km, 3.0)
            dur_mins = max(int(round(dist_km * 2.5)), 10)

            return CalculateRouteOutput(
                origin=origin,
                destination=destination,
                mode=mode,
                distance_km=dist_km,
                duration_minutes=dur_mins,
                steps=[f"Travel {dist_km} km from {origin} to {destination}."],
                provider=self.provider_name,
                data_mode="LIVE",
                demo_data=False,
            )

    def estimate_travel_time(
        self,
        origin: str,
        destination: str,
        mode: str = "transit",
        demo_mode: Optional[bool] = None,
    ) -> EstimateTravelTimeOutput:
        """Estimate transit duration between waypoints with safety buffer recommendation."""
        is_demo = get_effective_demo_mode(demo_mode)
        is_airport = "airport" in origin.lower() or "airport" in destination.lower()
        buffer = 40 if is_airport else 15

        if is_demo:
            duration = 45 if is_airport else 20
            return EstimateTravelTimeOutput(
                origin=origin,
                destination=destination,
                mode=mode,
                duration_minutes=duration,
                buffer_minutes=buffer,
                provider="Travel Time Estimator",
                data_mode="DEMO",
                demo_data=True,
            )

        route = self.calculate_route(origin=origin, destination=destination, mode=mode, demo_mode=False)
        return EstimateTravelTimeOutput(
            origin=origin,
            destination=destination,
            mode=mode,
            duration_minutes=route.duration_minutes,
            buffer_minutes=buffer,
            provider=self.provider_name,
            data_mode="LIVE",
            demo_data=False,
        )


# Global singleton provider instance
maps_provider = MapsProvider()
