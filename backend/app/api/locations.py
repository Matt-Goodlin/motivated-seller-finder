"""Location search and active location management."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.location import LocationSearchResult, LocationSet
from app.services.auth import get_current_user
from app.services.geocoder import search_location

router = APIRouter(prefix="/locations", tags=["locations"])

# In-memory active location store (persisted in Redis in production via Celery)
_active_location: dict = {}


@router.get("/search", response_model=list[LocationSearchResult])
async def location_search(
    q: str = Query(..., min_length=2, description="City, county, zip, or address"),
    _user: User = Depends(get_current_user),
):
    results = await search_location(q)
    return [
        LocationSearchResult(
            display_name=r.display_name,
            city=r.city,
            county=r.county,
            state=r.state,
            state_code=r.state_code,
            zip_code=r.zip_code,
            latitude=r.latitude,
            longitude=r.longitude,
            bbox=r.bbox,
        )
        for r in results
    ]


@router.post("/set", response_model=LocationSet)
async def set_location(
    body: LocationSet,
    _user: User = Depends(get_current_user),
):
    global _active_location
    _active_location = body.model_dump()
    return body


@router.get("/current", response_model=LocationSet | None)
async def get_current_location(_user: User = Depends(get_current_user)):
    if not _active_location:
        return None
    return LocationSet(**_active_location)
