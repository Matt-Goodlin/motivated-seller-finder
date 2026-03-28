"""Property listing, detail, and export endpoints."""
import csv
import io
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.property import Property, MarketStatus
from app.models.score import PropertyScore
from app.models.indicator import PropertyIndicator, IndicatorType
from app.schemas.property import PropertySummary, PropertyDetail
from app.schemas.indicator import IndicatorOut
from app.services.auth import get_current_user
from app.services.scoring_engine import INDICATOR_WEIGHTS, score_band
from app.data_sources.street_view import StreetViewSource
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/properties", tags=["properties"])


def _build_summary(prop: Property) -> PropertySummary:
    score = prop.score
    total_score = score.total_score if score else 0.0
    return PropertySummary(
        id=prop.id,
        address=prop.address,
        city=prop.city,
        state=prop.state,
        zip_code=prop.zip_code,
        county=prop.county,
        latitude=prop.latitude,
        longitude=prop.longitude,
        owner_name=prop.owner_name,
        owner_is_absentee=prop.owner_is_absentee,
        assessed_value=prop.assessed_value,
        market_value_estimate=prop.market_value_estimate,
        list_price=prop.list_price,
        market_status=prop.market_status,
        days_on_market=prop.days_on_market,
        price_reductions=prop.price_reductions,
        total_score=total_score,
        score_band=score_band(total_score),
        indicator_count=score.indicator_count if score else 0,
        zillow_url=prop.zillow_url,
        updated_at=prop.updated_at,
    )


@router.get("", response_model=dict)
async def list_properties(
    score_min: float = Query(0.0, ge=0, le=100),
    score_max: float = Query(100.0, ge=0, le=100),
    market_status: Optional[MarketStatus] = None,
    county: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
    indicator_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: str = Query("score", regex="^(score|address|city|days_on_market|assessed_value)$"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    # Build query with joins
    query = (
        select(Property)
        .join(PropertyScore, isouter=True)
        .options(selectinload(Property.score))
        .options(selectinload(Property.indicators))
    )

    filters = []
    if score_min > 0 or score_max < 100:
        filters.append(PropertyScore.total_score.between(score_min, score_max))
    if market_status:
        filters.append(Property.market_status == market_status)
    if county:
        filters.append(Property.county.ilike(f"%{county}%"))
    if state:
        filters.append(Property.state == state.upper())
    if zip_code:
        filters.append(Property.zip_code == zip_code)
    if indicator_type:
        subq = select(PropertyIndicator.property_id).where(
            PropertyIndicator.indicator_type == indicator_type
        )
        filters.append(Property.id.in_(subq))

    if filters:
        query = query.where(and_(*filters))

    # Sort
    if sort_by == "score":
        query = query.order_by(PropertyScore.total_score.desc().nulls_last())
    elif sort_by == "days_on_market":
        query = query.order_by(Property.days_on_market.desc().nulls_last())
    elif sort_by == "assessed_value":
        query = query.order_by(Property.assessed_value.desc().nulls_last())
    else:
        query = query.order_by(getattr(Property, sort_by))

    # Count total
    count_result = await db.execute(select(Property.id).join(PropertyScore, isouter=True).where(and_(*filters) if filters else True))
    total = len(count_result.all())

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    properties = result.scalars().unique().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "items": [_build_summary(p) for p in properties],
    }


@router.get("/map-pins", response_model=list[dict])
async def map_pins(
    score_min: float = Query(0.0),
    score_max: float = Query(100.0),
    county: Optional[str] = None,
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Lightweight endpoint returning only lat/lng/score for map rendering."""
    query = (
        select(Property.id, Property.latitude, Property.longitude,
               Property.address, Property.market_status, PropertyScore.total_score)
        .join(PropertyScore, isouter=True)
        .where(Property.latitude.isnot(None))
        .where(PropertyScore.total_score.between(score_min, score_max))
    )
    if county:
        query = query.where(Property.county.ilike(f"%{county}%"))
    if state:
        query = query.where(Property.state == state.upper())

    result = await db.execute(query)
    rows = result.all()
    return [
        {
            "id": str(r.id),
            "lat": r.latitude,
            "lng": r.longitude,
            "address": r.address,
            "market_status": r.market_status.value if r.market_status else "UNKNOWN",
            "score": r.total_score or 0.0,
            "score_band": score_band(r.total_score or 0.0),
        }
        for r in rows
    ]


@router.get("/{property_id}", response_model=PropertyDetail)
async def get_property(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Property)
        .options(selectinload(Property.score))
        .options(selectinload(Property.indicators))
        .where(Property.id == property_id)
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    score = prop.score
    total_score = score.total_score if score else 0.0

    indicators_out = [
        IndicatorOut(
            id=ind.id,
            indicator_type=ind.indicator_type,
            category=ind.category,
            confidence=ind.confidence,
            source_name=ind.source_name,
            detected_at=ind.detected_at,
            notes=ind.notes,
            weight=INDICATOR_WEIGHTS.get(ind.indicator_type, 0),
        )
        for ind in prop.indicators
    ]

    # Fetch street view on-demand
    street_view = None
    if prop.latitude and prop.longitude:
        sv = StreetViewSource()
        if sv.is_configured():
            street_view = await sv.get_street_view_url(prop.latitude, prop.longitude)

    return PropertyDetail(
        id=prop.id,
        address=prop.address,
        city=prop.city,
        state=prop.state,
        zip_code=prop.zip_code,
        county=prop.county,
        latitude=prop.latitude,
        longitude=prop.longitude,
        owner_name=prop.owner_name,
        owner_mailing_address=prop.owner_mailing_address,
        owner_phone=prop.owner_phone,
        owner_email=prop.owner_email,
        owner_is_absentee=prop.owner_is_absentee,
        assessed_value=prop.assessed_value,
        market_value_estimate=prop.market_value_estimate,
        list_price=prop.list_price,
        last_sale_price=prop.last_sale_price,
        last_sale_date=prop.last_sale_date,
        years_owned=prop.years_owned,
        mortgage_balance=prop.mortgage_balance,
        equity_estimate=prop.equity_estimate,
        market_status=prop.market_status,
        days_on_market=prop.days_on_market,
        price_reductions=prop.price_reductions,
        property_type=prop.property_type,
        year_built=prop.year_built,
        sq_ft=prop.sq_ft,
        lot_size_sqft=prop.lot_size_sqft,
        bedrooms=prop.bedrooms,
        bathrooms=prop.bathrooms,
        mls_id=prop.mls_id,
        list_date=prop.list_date,
        parcel_id=prop.parcel_id,
        zillow_url=prop.zillow_url,
        data_sources=prop.data_sources,
        total_score=total_score,
        score_band=score_band(total_score),
        indicator_count=score.indicator_count if score else 0,
        score=score,
        indicators=indicators_out,
        street_view=street_view,
        updated_at=prop.updated_at,
    )


@router.get("/export/csv")
async def export_csv(
    score_min: float = Query(0.0),
    county: Optional[str] = None,
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Export filtered properties as a CSV download."""
    query = (
        select(Property)
        .join(PropertyScore, isouter=True)
        .options(selectinload(Property.score))
        .where(PropertyScore.total_score >= score_min)
        .order_by(PropertyScore.total_score.desc().nulls_last())
        .limit(5000)
    )
    if county:
        query = query.where(Property.county.ilike(f"%{county}%"))
    if state:
        query = query.where(Property.state == state.upper())

    result = await db.execute(query)
    properties = result.scalars().unique().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Address", "City", "State", "Zip", "County",
        "Owner", "Absentee", "Owner Phone", "Owner Email",
        "Market Status", "Motivation Score", "Score Band",
        "Indicator Count", "Assessed Value", "List Price",
        "Days on Market", "Price Reductions",
        "Year Built", "Sq Ft", "Beds", "Baths",
        "Zillow URL", "Last Updated",
    ])
    for p in properties:
        s = p.score
        writer.writerow([
            p.address, p.city, p.state, p.zip_code, p.county,
            p.owner_name, "Yes" if p.owner_is_absentee else "No",
            p.owner_phone or "", p.owner_email or "",
            p.market_status.value if p.market_status else "",
            round(s.total_score, 1) if s else 0,
            score_band(s.total_score if s else 0),
            s.indicator_count if s else 0,
            p.assessed_value, p.list_price,
            p.days_on_market, p.price_reductions,
            p.year_built, p.sq_ft, p.bedrooms, p.bathrooms,
            p.zillow_url or "", p.updated_at.date() if p.updated_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=motivated-sellers.csv"},
    )
