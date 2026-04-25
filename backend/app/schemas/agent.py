import uuid
from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: uuid.UUID | None = None


class ConversationRead(BaseModel):
    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PinWidgetRequest(BaseModel):
    widget_type: str
    title: str
    data: dict
    position: int | None = None


class WorkspaceWidgetRead(BaseModel):
    id: uuid.UUID
    widget_type: str
    title: str
    data: dict
    position: int
    created_at: datetime

    model_config = {"from_attributes": True}
