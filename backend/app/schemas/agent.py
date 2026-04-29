import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.agent.tools import WIDGET_TYPES


class ChatRequest(BaseModel):
    message: str
    conversation_id: uuid.UUID | None = None


class ConversationRead(BaseModel):
    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationRead):
    messages: list[dict]


class PinWidgetRequest(BaseModel):
    widget_type: str
    title: str
    data: dict
    position: int | None = None

    @field_validator("widget_type")
    @classmethod
    def _check_widget_type(cls, v: str) -> str:
        if v not in WIDGET_TYPES:
            raise ValueError(f"widget_type must be one of {sorted(WIDGET_TYPES)}")
        return v


class ReorderRequest(BaseModel):
    widget_ids: list[uuid.UUID]


class WorkspaceWidgetRead(BaseModel):
    id: uuid.UUID
    widget_type: str
    title: str
    data: dict
    position: int
    created_at: datetime

    model_config = {"from_attributes": True}
