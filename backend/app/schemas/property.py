import uuid
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel
from app.models.property import MarketStatus
from app.schemas.score import ScoreOut
from app.schemas.indicator import IndicatorOut


class PropertyFilter(BaseModel):
    score_min: float = 0.0
    score_max: float = 100.0
    market_status: Optional[MarketStatus] = None
    zip_codes: Optional[list[str]] = None
    indicator_types: Optional[list[str]] = None
    county: Optional[str] = None
    state: Optional[str] = None
    page: int = 1
    page_size: int = 50


class PropertySummary(BaseModel):
    id: uuid.UUID
    address: str
    city: str
    state: str
    zip_code: Optional[str]
    county: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    owner_name: Optional[str]
    owner_is_absentee: bool
    assessed_value: Optional[float]
    market_value_estimate: Optional[float]
    list_price: Optional[float]
    market_status: MarketStatus
    days_on_market: Optional[int]
    price_reductions: int
    total_score: float
    score_band: str
    indicator_count: int
    zillow_url: Optional[str]
    updated_at: datetime

    model_config = {"from_attributes": True}


class PropertyDetail(PropertySummary):
    parcel_id: Optional[str]
    owner_mailing_address: Optional[str]
    owner_phone: Optional[str]
    owner_email: Optional[str]
    last_sale_price: Optional[float]
    last_sale_date: Optional[date]
    years_owned: Optional[float]
    mortgage_balance: Optional[float]
    equity_estimate: Optional[float]
    property_type: Optional[str]
    year_built: Optional[int]
    sq_ft: Optional[int]
    lot_size_sqft: Optional[int]
    bedrooms: Optional[int]
    bathrooms: Optional[float]
    mls_id: Optional[str]
    list_date: Optional[date]
    data_sources: str
    score: Optional[ScoreOut]
    indicators: list[IndicatorOut] = []
    street_view: Optional[dict] = None

    model_config = {"from_attributes": True}
