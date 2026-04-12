import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InsightItem(BaseModel):
    label: str
    count: int


class AnalysisHistoryItem(BaseModel):
    """A single versioned analysis snapshot from MongoDB."""

    business_id: str
    version: int
    summary: str
    top_complaints: list[InsightItem]
    top_praise: list[InsightItem]
    action_items: list[str]
    risk_areas: list[str]
    recommended_focus: str
    created_at: datetime
    archived_at: datetime


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    summary: str
    top_complaints: list[InsightItem]
    top_praise: list[InsightItem]
    action_items: list[str]
    risk_areas: list[str]
    recommended_focus: str
    created_at: datetime
