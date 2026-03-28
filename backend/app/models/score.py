import uuid
from datetime import datetime
from sqlalchemy import Float, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class PropertyScore(Base):
    __tablename__ = "property_scores"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    # 0–100 overall score
    total_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Category sub-scores (0–100 each)
    financial_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    legal_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    landlord_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    market_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    condition_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    indicator_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    property: Mapped["Property"] = relationship(back_populates="score")  # noqa: F821
