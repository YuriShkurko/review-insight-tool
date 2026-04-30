import uuid
from datetime import datetime
from typing import Any

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
    # `data` is a JSON column. Accept any JSON-compatible payload and coerce
    # to a dict — older rows or future tools may produce list-shaped or
    # null payloads, and one weird row should not crash the dashboard.
    data: dict[str, Any] = {}
    position: int
    # `created_at` has a server_default, but a NULL row from a manually-seeded
    # widget would otherwise crash response serialization. Allow None.
    created_at: datetime | None = None

    model_config = {"from_attributes": True}

    @field_validator("data", mode="before")
    @classmethod
    def _coerce_data(cls, v: Any) -> dict[str, Any]:
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        # A list (e.g., from a misrouted tool result) gets wrapped so render
        # code that reads .items / .series can still mount without a crash.
        return {"items": v} if isinstance(v, list) else {}
