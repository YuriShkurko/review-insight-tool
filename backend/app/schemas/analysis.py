import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InsightItem(BaseModel):
    label: str
    count: int


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    summary: str
    top_complaints: list[InsightItem]
    top_praise: list[InsightItem]
    created_at: datetime
