import uuid
from datetime import datetime
from pydantic import BaseModel


class ScoreOut(BaseModel):
    id: uuid.UUID
    total_score: float
    financial_score: float
    legal_score: float
    landlord_score: float
    market_score: float
    condition_score: float
    indicator_count: int
    last_calculated_at: datetime

    model_config = {"from_attributes": True}
