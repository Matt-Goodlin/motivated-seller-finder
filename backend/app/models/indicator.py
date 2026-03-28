import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, func, Enum as SAEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class IndicatorCategory(str, enum.Enum):
    FINANCIAL = "FINANCIAL"
    LEGAL_LIFE_EVENT = "LEGAL_LIFE_EVENT"
    LANDLORD_PAIN = "LANDLORD_PAIN"
    MARKET_SIGNAL = "MARKET_SIGNAL"
    PROPERTY_CONDITION = "PROPERTY_CONDITION"


class IndicatorType(str, enum.Enum):
    # Financial
    PRE_FORECLOSURE = "pre_foreclosure"
    TAX_DELINQUENT = "tax_delinquent"
    ACTIVE_LIEN = "active_lien"
    BANKRUPTCY_FILING = "bankruptcy_filing"
    UTILITY_SHUTOFF = "utility_shutoff"
    LOW_EQUITY = "low_equity"

    # Legal / Life Events
    PROBATE_FILING = "probate_filing"
    DIVORCE_FILING = "divorce_filing"
    EVICTION_FILING = "eviction_filing"
    JOB_RELOCATION = "job_relocation"

    # Landlord Pain
    CODE_VIOLATION = "code_violation"
    FAILED_INSPECTION = "failed_inspection"
    PERMIT_INCOMPLETE = "permit_incomplete"
    LOW_RENT_VS_MARKET = "low_rent_vs_market"
    LANDLORD_MULTI_EVICTION = "landlord_multi_eviction"

    # Market Signals
    EXPIRED_LISTING = "expired_listing"
    LONG_DOM = "long_dom"
    PRICE_DROPS = "price_drops"
    USPS_VACANCY = "usps_vacancy"
    NO_MAIL_ACTIVITY = "no_mail_activity"

    # Property Condition
    STREET_VIEW_NEGLECT = "street_view_neglect"
    LONG_OWNERSHIP_NO_IMPROVEMENTS = "long_ownership_no_improvements"
    ABSENTEE_OWNER = "absentee_owner"


INDICATOR_CATEGORIES: dict[IndicatorType, IndicatorCategory] = {
    IndicatorType.PRE_FORECLOSURE: IndicatorCategory.FINANCIAL,
    IndicatorType.TAX_DELINQUENT: IndicatorCategory.FINANCIAL,
    IndicatorType.ACTIVE_LIEN: IndicatorCategory.FINANCIAL,
    IndicatorType.BANKRUPTCY_FILING: IndicatorCategory.FINANCIAL,
    IndicatorType.UTILITY_SHUTOFF: IndicatorCategory.FINANCIAL,
    IndicatorType.LOW_EQUITY: IndicatorCategory.FINANCIAL,

    IndicatorType.PROBATE_FILING: IndicatorCategory.LEGAL_LIFE_EVENT,
    IndicatorType.DIVORCE_FILING: IndicatorCategory.LEGAL_LIFE_EVENT,
    IndicatorType.EVICTION_FILING: IndicatorCategory.LEGAL_LIFE_EVENT,
    IndicatorType.JOB_RELOCATION: IndicatorCategory.LEGAL_LIFE_EVENT,

    IndicatorType.CODE_VIOLATION: IndicatorCategory.LANDLORD_PAIN,
    IndicatorType.FAILED_INSPECTION: IndicatorCategory.LANDLORD_PAIN,
    IndicatorType.PERMIT_INCOMPLETE: IndicatorCategory.LANDLORD_PAIN,
    IndicatorType.LOW_RENT_VS_MARKET: IndicatorCategory.LANDLORD_PAIN,
    IndicatorType.LANDLORD_MULTI_EVICTION: IndicatorCategory.LANDLORD_PAIN,

    IndicatorType.EXPIRED_LISTING: IndicatorCategory.MARKET_SIGNAL,
    IndicatorType.LONG_DOM: IndicatorCategory.MARKET_SIGNAL,
    IndicatorType.PRICE_DROPS: IndicatorCategory.MARKET_SIGNAL,
    IndicatorType.USPS_VACANCY: IndicatorCategory.MARKET_SIGNAL,
    IndicatorType.NO_MAIL_ACTIVITY: IndicatorCategory.MARKET_SIGNAL,

    IndicatorType.STREET_VIEW_NEGLECT: IndicatorCategory.PROPERTY_CONDITION,
    IndicatorType.LONG_OWNERSHIP_NO_IMPROVEMENTS: IndicatorCategory.PROPERTY_CONDITION,
    IndicatorType.ABSENTEE_OWNER: IndicatorCategory.PROPERTY_CONDITION,
}


class PropertyIndicator(Base):
    __tablename__ = "property_indicators"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    indicator_type: Mapped[IndicatorType] = mapped_column(
        SAEnum(IndicatorType), nullable=False, index=True
    )
    category: Mapped[IndicatorCategory] = mapped_column(
        SAEnum(IndicatorCategory), nullable=False, index=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    property: Mapped["Property"] = relationship(back_populates="indicators")  # noqa: F821
