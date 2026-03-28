import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.indicator import IndicatorType, IndicatorCategory


class IndicatorOut(BaseModel):
    id: uuid.UUID
    indicator_type: IndicatorType
    category: IndicatorCategory
    confidence: float
    source_name: str
    detected_at: datetime
    notes: Optional[str]
    weight: int

    model_config = {"from_attributes": True}
