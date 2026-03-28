"""
Street View / visual condition assessment.

Uses Google Street View API (paid) or Mapillary (free) to pull street-level
imagery of properties. In the future, this can be extended with a vision
model to detect: overgrown lawn, boarded windows, missing roof tiles, etc.

For now, this source returns metadata about image availability, and the
frontend displays the image. Manual scoring of condition is done by the user.

Configure GOOGLE_STREET_VIEW_API_KEY or MAPILLARY_CLIENT_TOKEN in .env.
"""
import httpx
from app.data_sources.base import DataSource, DataSourceResult, RawPropertyRecord, RawIndicator
from app.models.indicator import IndicatorType
from app.config import get_settings

settings = get_settings()

MAPILLARY_BASE = "https://graph.mapillary.com"
GOOGLE_SV_METADATA = "https://maps.googleapis.com/maps/api/streetview/metadata"


class StreetViewSource(DataSource):
    name = "street_view"
    display_name = "Street View Imagery"
    description = (
        "Provides street-level imagery links for visual property condition assessment. "
        "Uses Mapillary (free) or Google Street View (paid). "
        "Lets you visually spot overgrown lawns, boarded windows, deferred maintenance."
    )
    is_paid = False  # Mapillary is free
    default_enabled = False

    def is_configured(self) -> bool:
        return bool(settings.mapillary_client_token or settings.google_street_view_api_key)

    async def fetch(self, county: str, state: str) -> DataSourceResult:
        result = DataSourceResult(
            source_name=self.name,
            location=f"{county}, {state}",
        )
        result.errors.append(
            "Street view is property-level (not area-wide). "
            "Images are fetched on-demand when viewing a property detail."
        )
        return result

    async def get_street_view_url(self, lat: float, lng: float) -> dict:
        """
        Returns street view image metadata and URL for a specific property.
        Called on-demand from the property detail API endpoint.
        """
        result = {"available": False, "url": None, "source": None}

        # Try Mapillary first (free)
        if settings.mapillary_client_token:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"{MAPILLARY_BASE}/images",
                        params={
                            "access_token": settings.mapillary_client_token,
                            "fields": "id,thumb_1024_url,computed_compass_angle",
                            "closeto": f"{lng},{lat}",
                            "radius": 50,
                            "limit": 1,
                        },
                        timeout=10.0,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        images = data.get("data", [])
                        if images:
                            result["available"] = True
                            result["url"] = images[0].get("thumb_1024_url")
                            result["source"] = "mapillary"
                            return result
            except Exception:
                pass

        # Fall back to Google Street View
        if settings.google_street_view_api_key:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        GOOGLE_SV_METADATA,
                        params={
                            "location": f"{lat},{lng}",
                            "key": settings.google_street_view_api_key,
                        },
                        timeout=10.0,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("status") == "OK":
                            result["available"] = True
                            result["url"] = (
                                f"https://maps.googleapis.com/maps/api/streetview"
                                f"?size=800x400&location={lat},{lng}"
                                f"&key={settings.google_street_view_api_key}"
                            )
                            result["source"] = "google"
            except Exception:
                pass

        return result

    def map_to_indicators(self, record: RawPropertyRecord) -> list[RawIndicator]:
        return []
