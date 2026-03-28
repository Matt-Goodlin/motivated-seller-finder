import uuid
from datetime import datetime, date
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Date, func, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class MarketStatus(str, enum.Enum):
    ON_MARKET = "ON_MARKET"
    OFF_MARKET = "OFF_MARKET"
    UNKNOWN = "UNKNOWN"


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Identity
    parcel_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    zip_code: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    county: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    fips_code: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)

    # Geo
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Owner
    owner_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    owner_mailing_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    owner_is_absentee: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Financials
    assessed_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_value_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_sale_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_sale_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    years_owned: Mapped[float | None] = mapped_column(Float, nullable=True)
    mortgage_balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    equity_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Property details
    property_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sq_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lot_size_sqft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[float | None] = mapped_column(Float, nullable=True)

    # MLS / on-market
    market_status: Mapped[MarketStatus] = mapped_column(
        SAEnum(MarketStatus), default=MarketStatus.UNKNOWN
    )
    list_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    list_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    days_on_market: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_reductions: Mapped[int] = mapped_column(Integer, default=0)
    mls_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    zillow_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    data_sources: Mapped[list[str]] = mapped_column(
        String(500), default="", nullable=False
    )  # comma-separated source names

    # Relationships
    indicators: Mapped[list["PropertyIndicator"]] = relationship(  # noqa: F821
        back_populates="property", cascade="all, delete-orphan"
    )
    score: Mapped["PropertyScore | None"] = relationship(  # noqa: F821
        back_populates="property", uselist=False, cascade="all, delete-orphan"
    )
