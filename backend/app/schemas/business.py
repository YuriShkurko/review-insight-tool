import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BusinessCreate(BaseModel):
    google_maps_url: str | None = None
    place_id: str | None = None


class BusinessRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    place_id: str
    name: str
    address: str | None
    google_maps_url: str | None
    avg_rating: float | None
    total_reviews: int
    created_at: datetime
    updated_at: datetime
