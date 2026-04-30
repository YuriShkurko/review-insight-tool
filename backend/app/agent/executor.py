"""Agent executor: drives the LLM → tool → LLM loop and yields SSE-formatted lines."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy.orm import Session

from app.agent.context import truncate_messages
from app.agent.guardrails import Intent, classify_intent
from app.agent.system_prompt import build_system_prompt
from app.agent.tools import (
    TOOL_COMPATIBLE_WIDGETS,
    TOOL_DEFINITIONS,
    TOOL_WIDGET_TYPES,
    execute_tool,
)
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
    # Pre-flight guardrails: run before any DB or LLM work so blocked messages
    # are cheap and don't persist history.
    intent = classify_intent(message)
    if intent == Intent.UNSAFE:
        yield _sse("text_delta", {"text": "I can't help with that request."})
        yield _sse("done", {})
        return
    if intent == Intent.IRRELEVANT:
        yield _sse(
            "text_delta",
            {
                "text": (
                    "I'm focused on your business reviews, competitors, and dashboard. "
                    "Try asking about your ratings, top issues, or review trends."
                )
            },
        )
        yield _sse("done", {})
        return

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

    # Yield immediately so the connection stays alive and the UI shows activity
    # before the first (potentially slow) LLM call completes.
    yield _sse("status", {"status": "thinking"})

    # Build the full message list for the LLM (system + truncated history)
    def _build_llm_messages() -> list[dict]:
        base = [{"role": "system", "content": system_prompt}]
        return base + truncate_messages(history)

    # Registry of successful data-tool results keyed by tool name.
    # pin_widget resolves source_tool against this dict so each widget is wired
    # to the exact tool that produced its data, not just whatever ran last.
    tool_results: dict[str, dict] = {}

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
                if tc.name == "pin_widget":
                    args = dict(tc.arguments)
                    # Refuse incompatible widget_type ↔ source_tool combos
                    # before resolving data, so the dashboard never gets a
                    # widget that the renderer can't draw (e.g. pie_chart
                    # of get_review_series time series).
                    requested_widget = str(args.get("widget_type") or "")
                    requested_source = args.get("source_tool")
                    compatible = (
                        TOOL_COMPATIBLE_WIDGETS.get(requested_source)
                        if isinstance(requested_source, str)
                        else None
                    )
                    if (
                        compatible is not None
                        and requested_widget
                        and requested_widget not in compatible
                    ):
                        result = {
                            "pinned": False,
                            "error": (
                                f"widget_type '{requested_widget}' is not compatible with "
                                f"source_tool '{requested_source}'. "
                                f"Use one of: {sorted(compatible)}."
                            ),
                        }
                        widget_type_hint = TOOL_WIDGET_TYPES.get(tc.name)
                        yield _sse(
                            "tool_result",
                            {"name": tc.name, "widget_type": widget_type_hint, "result": result},
                        )
                        tool_msg = {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result),
                        }
                        history.append(tool_msg)
                        new_messages.append(tool_msg)
                        continue
                    incoming_data = args.get("data")
                    data_is_empty = (
                        not incoming_data
                        or not isinstance(incoming_data, dict)
                        or len(incoming_data) == 0
                    )
                    if data_is_empty:
                        # Resolve source_tool first; fall back to most recent result.
                        source_tool = args.get("source_tool")
                        resolved: dict | None = None
                        if source_tool and source_tool in tool_results:
                            resolved = tool_results[source_tool]
                        elif tool_results:
                            resolved = next(reversed(tool_results.values()))
                        if not resolved or not isinstance(resolved, dict) or len(resolved) == 0:
                            # Refuse to persist an empty widget. The model gets a
                            # tool result it can react to in the next turn instead
                            # of leaving an empty card on the dashboard.
                            result = {
                                "pinned": False,
                                "error": (
                                    "No data available to pin. Call a data tool "
                                    "(e.g. get_dashboard, get_rating_distribution) "
                                    "first, then call pin_widget with that tool's "
                                    "name as source_tool."
                                ),
                            }
                        else:
                            args["data"] = resolved
                            result = execute_tool(tc.name, args, db, business_id, user_id)
                    else:
                        result = execute_tool(tc.name, args, db, business_id, user_id)
                else:
                    result = execute_tool(tc.name, tc.arguments, db, business_id, user_id)
                    if isinstance(result, dict) and "error" not in result:
                        tool_results[tc.name] = result
            except Exception as exc:
                logger.error("op=agent_tool tool=%s error=%s", tc.name, exc)
                result = {"error": str(exc)}

            widget_type = TOOL_WIDGET_TYPES.get(tc.name)
            yield _sse(
                "tool_result",
                {"name": tc.name, "widget_type": widget_type, "result": result},
            )

            if tc.name == "pin_widget" and result.get("pinned") and result.get("widget"):
                yield _sse(
                    "workspace_event",
                    {"action": "widget_added", "widget": result["widget"]},
                )
            if tc.name == "remove_widget" and result.get("removed") and result.get("widget_id"):
                yield _sse(
                    "workspace_event",
                    {"action": "widget_removed", "widget_id": result["widget_id"]},
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
