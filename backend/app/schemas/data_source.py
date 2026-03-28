import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DataSourceOut(BaseModel):
    source_name: str
    display_name: str
    description: str
    is_paid: bool
    enabled: bool
    is_configured: bool
    last_run_at: Optional[datetime]

    model_config = {"from_attributes": True}


class DataSourceUpdate(BaseModel):
    enabled: Optional[bool] = None
    api_key: Optional[str] = None  # written encrypted, never returned
    config_json: Optional[dict] = None


class DataSourceRunOut(BaseModel):
    id: uuid.UUID
    source_name: str
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    records_fetched: int
    records_created: int
    records_updated: int
    error_message: Optional[str]
    location: Optional[str]

    model_config = {"from_attributes": True}
