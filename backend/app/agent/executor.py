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

MAX_ITERATIONS = 20  # guard against runaway tool loops; dashboard fills need many tool rounds.
MAX_FAILED_PIN_ATTEMPTS = 3
# Cap how many tool_results we restore from prior turns so the registry
# does not grow unbounded across long conversations. The model still has
# the full history; this only governs the cached-payload registry that
# pin_widget uses to wire data.
_REHYDRATE_TOOL_LIMIT = 12
_NON_DATA_TOOLS = {
    "pin_widget",
    "get_workspace",
    "remove_widget",
    "clear_dashboard",
    "duplicate_widget",
    "set_dashboard_order",
}


def _pin_abort_reason() -> str:
    return (
        "I couldn't add that widget after a few attempts because the requested "
        "widget/data pairing kept failing. Try a supported summary, insight list, "
        "or chart for the same review data."
    )


def _tool_execution_order(tool_calls: list) -> list:
    """Run data tools before pin_widget inside one assistant tool batch.

    Live LLMs may return a parallel-looking batch where pin_widget appears
    before the source data tool it references. The chat-completions protocol
    requires every tool_call_id to receive a tool response; executing data
    producers first lets source_tool resolution work even when the model's
    call order is not dependency-safe.
    """
    return sorted(enumerate(tool_calls), key=lambda item: (item[1].name == "pin_widget", item[0]))


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _rehydrate_tool_results(history: list[dict]) -> dict[str, dict]:
    """Reconstruct tool_results from prior conversation turns.

    pin_widget resolves source_tool against tool_results[name]. Without
    rehydration, that registry is empty at the start of every user turn,
    so a recovery flow ("yes, use the bar chart instead") can't reach the
    data the agent already fetched. We walk the history backwards, match
    each tool message to its preceding assistant tool_call, and seed the
    registry with the most recent successful payload per tool name.
    """
    pending: dict[str, dict] = {}
    # Map tool_call_id -> tool name from assistant messages so tool messages
    # can be resolved without an O(n^2) scan.
    call_id_to_name: dict[str, str] = {}
    for msg in history:
        if msg.get("role") == "assistant":
            for tc in msg.get("tool_calls") or []:
                call_id = tc.get("id")
                fn = (tc.get("function") or {}).get("name")
                if isinstance(call_id, str) and isinstance(fn, str):
                    call_id_to_name[call_id] = fn

    # Walk backwards so the most recent successful result wins.
    for msg in reversed(history):
        if msg.get("role") != "tool":
            continue
        if len(pending) >= _REHYDRATE_TOOL_LIMIT:
            break
        call_id = msg.get("tool_call_id")
        name = call_id_to_name.get(call_id) if isinstance(call_id, str) else None
        if not name or name in pending:
            continue
        # Skip non-data tools — pin_widget/remove_widget/duplicate_widget
        # do not produce reusable payloads.
        if name in _NON_DATA_TOOLS:
            continue
        raw = msg.get("content")
        if not isinstance(raw, str):
            continue
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict) or "error" in payload:
            continue
        pending[name] = payload
    return pending


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
    # Seeded from prior turns so the agent can recover ("yes, use the bar
    # chart instead") without re-fetching data it already has.
    tool_results: dict[str, dict] = _rehydrate_tool_results(history)
    failed_pin_attempts = 0

    for _ in range(MAX_ITERATIONS):
        abort_reason: str | None = None
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
        for _, tc in _tool_execution_order(tool_calls):
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
                        available_sources = sorted(tool_results.keys())
                        result = {
                            "pinned": False,
                            "error": (
                                f"widget_type '{requested_widget}' is not compatible with "
                                f"source_tool '{requested_source}'. "
                                f"Use one of: {sorted(compatible)}. "
                                "To recover: pick an allowed widget_type for this source_tool, "
                                "OR call create_custom_chart_data and re-pin with "
                                "source_tool='create_custom_chart_data'."
                            ),
                            "allowed_widget_types": sorted(compatible),
                            "available_source_tools": available_sources,
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
                        failed_pin_attempts += 1
                        if failed_pin_attempts >= MAX_FAILED_PIN_ATTEMPTS:
                            abort_reason = _pin_abort_reason()
                            break
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
                            available_sources = sorted(tool_results.keys())
                            hint = (
                                f"Cached results currently available as source_tool: "
                                f"{available_sources}. "
                                if available_sources
                                else ""
                            )
                            result = {
                                "pinned": False,
                                "error": (
                                    "No data available to pin. "
                                    f"{hint}"
                                    "Call a data tool (e.g. get_dashboard, "
                                    "get_rating_distribution) first, then call "
                                    "pin_widget with that tool's name as source_tool."
                                ),
                                "available_source_tools": available_sources,
                            }
                        else:
                            args["data"] = resolved
                            result = execute_tool(tc.name, args, db, business_id, user_id)
                    else:
                        result = execute_tool(tc.name, args, db, business_id, user_id)
                else:
                    result = execute_tool(tc.name, tc.arguments, db, business_id, user_id)
                    # Only cache data-producing tools as future source_tool
                    # candidates. remove_widget / duplicate_widget produce
                    # workspace ack payloads that should not be reused as
                    # widget data.
                    if (
                        isinstance(result, dict)
                        and "error" not in result
                        and tc.name not in _NON_DATA_TOOLS
                    ):
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
            if tc.name == "clear_dashboard" and result.get("cleared"):
                yield _sse(
                    "workspace_event",
                    {
                        "action": "dashboard_cleared",
                        "widget_ids": result.get("widget_ids", []),
                    },
                )
            if tc.name == "duplicate_widget" and result.get("duplicated") and result.get("widget"):
                yield _sse(
                    "workspace_event",
                    {"action": "widget_added", "widget": result["widget"]},
                )
            if tc.name == "set_dashboard_order" and result.get("reordered"):
                yield _sse(
                    "workspace_event",
                    {"action": "widgets_reordered", "widget_ids": result.get("widget_ids", [])},
                )

            tool_msg = {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            }
            history.append(tool_msg)
            new_messages.append(tool_msg)

            if tc.name == "pin_widget":
                if result.get("pinned") is True:
                    failed_pin_attempts = 0
                elif result.get("pinned") is False:
                    failed_pin_attempts += 1
                    if failed_pin_attempts >= MAX_FAILED_PIN_ATTEMPTS:
                        abort_reason = _pin_abort_reason()
                        break

        if abort_reason:
            yield _sse("text_delta", {"text": abort_reason})
            assistant_abort_msg = {"role": "assistant", "content": abort_reason}
            history.append(assistant_abort_msg)
            new_messages.append(assistant_abort_msg)
            break

    # Persist updated conversation
    conv.messages = history
    db.commit()

    yield _sse("done", {"conversation_id": str(conv.id)})
