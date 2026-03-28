from typing import Optional
from pydantic import BaseModel


class LocationSearchResult(BaseModel):
    display_name: str
    city: Optional[str]
    county: Optional[str]
    state: Optional[str]
    state_code: Optional[str]
    zip_code: Optional[str]
    latitude: float
    longitude: float
    bbox: tuple[float, float, float, float]


class LocationSet(BaseModel):
    display_name: str
    city: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    state_code: Optional[str] = None
    latitude: float
    longitude: float
    bbox: tuple[float, float, float, float]
