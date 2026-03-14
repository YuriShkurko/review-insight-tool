import uuid

from pydantic import BaseModel

from app.schemas.analysis import InsightItem
from app.schemas.business import BusinessRead, BusinessType


class CompetitorAdd(BaseModel):
    """Payload to add a competitor (same shape as adding a business)."""
    google_maps_url: str | None = None
    place_id: str | None = None
    business_type: BusinessType = BusinessType.other


class CompetitorRead(BaseModel):
    """A linked competitor: the link id plus the competitor business and readiness status."""
    link_id: uuid.UUID
    business: BusinessRead
    has_reviews: bool
    has_analysis: bool


class BusinessSnapshot(BaseModel):
    """Subset of business + analysis data for comparison display."""
    business_id: uuid.UUID
    name: str
    business_type: str
    avg_rating: float | None
    total_reviews: int
    summary: str
    top_complaints: list[InsightItem]
    top_praise: list[InsightItem]
    action_items: list[str]
    risk_areas: list[str]
    recommended_focus: str


class ComparisonResponse(BaseModel):
    """Full comparison: target + competitors snapshots + AI-generated insights."""
    target: BusinessSnapshot
    competitors: list[BusinessSnapshot]
    comparison_summary: str
    strengths: list[str]
    weaknesses: list[str]
    opportunities: list[str]
