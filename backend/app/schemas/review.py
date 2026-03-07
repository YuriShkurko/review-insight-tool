import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    external_id: str
    source: str
    author: str | None
    rating: int
    text: str | None
    published_at: datetime | None
    created_at: datetime
