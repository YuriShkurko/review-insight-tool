import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class BusinessType(StrEnum):
    restaurant = "restaurant"
    bar = "bar"
    cafe = "cafe"
    gym = "gym"
    salon = "salon"
    hotel = "hotel"
    clinic = "clinic"
    retail = "retail"
    other = "other"


class BusinessCreate(BaseModel):
    google_maps_url: str | None = None
    place_id: str | None = None
    business_type: BusinessType = BusinessType.other


class BusinessRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    place_id: str
    name: str
    business_type: str
    address: str | None
    google_maps_url: str | None
    avg_rating: float | None
    total_reviews: int
    created_at: datetime
    updated_at: datetime
