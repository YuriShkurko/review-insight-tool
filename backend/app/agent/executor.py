"""Agent executor: drives the LLM → tool → LLM loop and yields SSE-formatted lines."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy.orm import Session

from app.agent.context import truncate_messages
from app.agent.system_prompt import build_system_prompt
from app.agent.tools import TOOL_DEFINITIONS, TOOL_WIDGET_TYPES, execute_tool
from app.llm import get_llm_provider
from app.models.business import Business
from app.models.conversation import Conversation

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 8  # guard against runaway tool loops


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def run_agent(
    *,
    business_id: uuid.UUID,
    user_id: uuid.UUID,
    message: str,
    conversation_id: uuid.UUID | None,
    db: Session,
) -> AsyncGenerator[str, None]:
    provider = get_llm_provider()
    if not provider:
        yield _sse("text_delta", {"text": "LLM provider is not configured."})
        yield _sse("done", {})
        return

    # Load business (needed for system prompt + ownership check)
    business = (
        db.query(Business).filter(Business.id == business_id, Business.user_id == user_id).first()
    )
    if not business:
        yield _sse("error", {"message": "Business not found."})
        yield _sse("done", {})
        return

    # Load or create conversation
    conv = None
    if conversation_id:
        conv = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.business_id == business_id,
                Conversation.user_id == user_id,
            )
            .first()
        )
    if not conv:
        conv = Conversation(
            id=uuid.uuid4(),
            business_id=business_id,
            user_id=user_id,
            messages=[],
        )
        db.add(conv)
        db.flush()

    # Append user message
    history: list[dict] = list(conv.messages or [])
    history.append({"role": "user", "content": message})
    if not conv.title:
        conv.title = message[:80]

    system_prompt = build_system_prompt(business)
    new_messages: list[dict] = []  # messages added this turn (to persist later)
    new_messages.append({"role": "user", "content": message})

    # Build the full message list for the LLM (system + truncated history)
    def _build_llm_messages() -> list[dict]:
        base = [{"role": "system", "content": system_prompt}]
        return base + truncate_messages(history)

    for _ in range(MAX_ITERATIONS):
        llm_messages = _build_llm_messages()
        try:
            text, tool_calls = await asyncio.to_thread(
                provider.complete_with_tools,
                llm_messages,
                TOOL_DEFINITIONS,
            )
        except Exception as exc:
            logger.error("op=agent_llm error=%s", exc)
            yield _sse("text_delta", {"text": "Sorry, the AI call failed. Please try again."})
            break

        if text:
            yield _sse("text_delta", {"text": text})

        # Build assistant message for history
        assistant_msg: dict = {"role": "assistant", "content": text or None}
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                }
                for tc in tool_calls
            ]
        history.append(assistant_msg)
        new_messages.append(assistant_msg)

        if not tool_calls:
            break

        # Execute tools
        for tc in tool_calls:
            yield _sse("tool_call", {"name": tc.name, "args": tc.arguments})
            try:
                result = await asyncio.to_thread(
                    execute_tool, tc.name, tc.arguments, db, business_id, user_id
                )
            except Exception as exc:
                logger.error("op=agent_tool tool=%s error=%s", tc.name, exc)
                result = {"error": str(exc)}

            widget_type = TOOL_WIDGET_TYPES.get(tc.name)
            yield _sse(
                "tool_result",
                {"name": tc.name, "widget_type": widget_type, "result": result},
            )

            tool_msg = {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            }
            history.append(tool_msg)
            new_messages.append(tool_msg)

    # Persist updated conversation
    conv.messages = history
    db.commit()

    yield _sse("done", {"conversation_id": str(conv.id)})
