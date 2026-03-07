from pydantic import BaseModel

from app.schemas.analysis import InsightItem


class DashboardResponse(BaseModel):
    business_name: str
    address: str | None
    avg_rating: float | None
    total_reviews: int
    top_complaints: list[InsightItem]
    top_praise: list[InsightItem]
    ai_summary: str | None
