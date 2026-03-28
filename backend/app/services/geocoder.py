"""
Geocoding and location resolution using Nominatim (OpenStreetMap).
Resolves city/county/zip queries to FIPS codes and bounding boxes.
"""
import asyncio
from dataclasses import dataclass
from typing import Optional
import httpx
from app.config import get_settings

settings = get_settings()

NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
CENSUS_GEOCODE_BASE = "https://geocoding.geo.census.gov/geocoder"


@dataclass
class LocationResult:
    display_name: str
    city: Optional[str]
    county: Optional[str]
    state: Optional[str]
    state_code: Optional[str]
    zip_code: Optional[str]
    fips_code: Optional[str]
    latitude: float
    longitude: float
    # Bounding box [south, north, west, east]
    bbox: tuple[float, float, float, float]


async def search_location(query: str) -> list[LocationResult]:
    """Search for a location by city, county, state, or zip."""
    headers = {"User-Agent": settings.nominatim_user_agent}
    params = {
        "q": query,
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": 5,
        "countrycodes": "us",
        "featuretype": "settlement",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{NOMINATIM_BASE}/search",
            params=params,
            headers=headers,
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data:
        addr = item.get("address", {})
        bbox_raw = item.get("boundingbox", [])
        bbox = (
            float(bbox_raw[0]),
            float(bbox_raw[1]),
            float(bbox_raw[2]),
            float(bbox_raw[3]),
        ) if len(bbox_raw) == 4 else (0.0, 0.0, 0.0, 0.0)

        state_code = addr.get("ISO3166-2-lvl4", "").replace("US-", "")

        results.append(LocationResult(
            display_name=item.get("display_name", ""),
            city=addr.get("city") or addr.get("town") or addr.get("village"),
            county=addr.get("county"),
            state=addr.get("state"),
            state_code=state_code,
            zip_code=addr.get("postcode"),
            fips_code=None,  # resolved separately if needed
            latitude=float(item.get("lat", 0)),
            longitude=float(item.get("lon", 0)),
            bbox=bbox,
        ))

    return results


async def geocode_address(address: str) -> Optional[tuple[float, float]]:
    """Convert a street address to (lat, lng). Returns None if not found."""
    headers = {"User-Agent": settings.nominatim_user_agent}
    params = {
        "q": address,
        "format": "jsonv2",
        "limit": 1,
        "countrycodes": "us",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{NOMINATIM_BASE}/search",
            params=params,
            headers=headers,
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()

    if data:
        return float(data[0]["lat"]), float(data[0]["lon"])
    return None
