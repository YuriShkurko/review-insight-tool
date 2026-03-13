from datetime import datetime

from pydantic import BaseModel

from app.schemas.analysis import InsightItem


class DashboardResponse(BaseModel):
    business_name: str
    business_type: str
    address: str | None
    avg_rating: float | None
    total_reviews: int
    top_complaints: list[InsightItem]
    top_praise: list[InsightItem]
    ai_summary: str | None
    action_items: list[str]
    risk_areas: list[str]
    recommended_focus: str | None
    analysis_created_at: datetime | None
    last_updated_at: datetime | None
