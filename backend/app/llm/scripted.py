"""Deterministic LLM provider for E2E and integration tests.

Loads a list of pre-recorded assistant turns from JSON and returns them
in order from `complete_with_tools`. No network. No live SDK. Selected
only when LLM_PROVIDER=scripted.

Script JSON shape:
    [
      {"text": "...", "tool_calls": [{"name": "get_dashboard", "arguments": {}}, ...]},
      {"text": "Pinned.", "tool_calls": []}
    ]

Each entry is one assistant turn — i.e. one return value of
`complete_with_tools`. `text` defaults to "" and `tool_calls` defaults
to []. `id` on each tool_call is optional; if omitted, a stable id is
synthesized from the (turn_index, call_index) so executor history stays
parseable.
"""

from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any

from app.llm.base import LLMProvider, ToolCall


class ScriptExhausted(RuntimeError):  # noqa: N818 — kept verb-form for readability at raise sites
    """Raised when the script has no more turns but the executor asked for one."""


class ScriptedProvider(LLMProvider):
    """LLM provider that replays a fixed list of assistant turns."""

    def __init__(self, script: list[dict] | None = None) -> None:
        self._lock = threading.Lock()
        self._cursor = 0
        self._turns: list[dict] = []
        if script is not None:
            self._set_turns(script)

    # ── public API ──────────────────────────────────────────────────────

    def load_from_path(self, path: str | Path) -> None:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"ScriptedProvider: AGENT_SCRIPT_PATH not found: {p}")
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"ScriptedProvider: invalid JSON in {p}: {exc}") from exc
        self._set_turns(data)

    def set_script(self, script: list[dict]) -> None:
        self._set_turns(script)

    def reset(self) -> None:
        with self._lock:
            self._cursor = 0

    @property
    def remaining(self) -> int:
        with self._lock:
            return max(0, len(self._turns) - self._cursor)

    # ── LLMProvider interface ───────────────────────────────────────────

    def complete(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> str:
        text, _ = self._next_turn()
        return text

    def complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        *,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> tuple[str, list[ToolCall]]:
        return self._next_turn()

    # ── internals ───────────────────────────────────────────────────────

    def _set_turns(self, script: Any) -> None:
        if not isinstance(script, list):
            raise ValueError("ScriptedProvider: script must be a JSON array of assistant turns.")
        normalized: list[dict] = []
        for i, entry in enumerate(script):
            if not isinstance(entry, dict):
                raise ValueError(
                    f"ScriptedProvider: turn {i} must be an object, got {type(entry).__name__}."
                )
            text = entry.get("text", "") or ""
            if not isinstance(text, str):
                raise ValueError(f"ScriptedProvider: turn {i} 'text' must be a string.")
            tool_calls_raw = entry.get("tool_calls", []) or []
            if not isinstance(tool_calls_raw, list):
                raise ValueError(f"ScriptedProvider: turn {i} 'tool_calls' must be a list.")
            tool_calls: list[dict] = []
            for j, tc in enumerate(tool_calls_raw):
                if not isinstance(tc, dict):
                    raise ValueError(
                        f"ScriptedProvider: turn {i} tool_call {j} must be an object."
                    )
                name = tc.get("name")
                if not isinstance(name, str) or not name:
                    raise ValueError(
                        f"ScriptedProvider: turn {i} tool_call {j} requires non-empty 'name'."
                    )
                args = tc.get("arguments", {}) or {}
                if not isinstance(args, dict):
                    raise ValueError(
                        f"ScriptedProvider: turn {i} tool_call {j} 'arguments' must be an object."
                    )
                tc_id = tc.get("id") or f"scripted-{i}-{j}-{uuid.uuid4().hex[:8]}"
                tool_calls.append({"id": str(tc_id), "name": name, "arguments": args})
            normalized.append({"text": text, "tool_calls": tool_calls})

        with self._lock:
            self._turns = normalized
            self._cursor = 0

    def _next_turn(self) -> tuple[str, list[ToolCall]]:
        with self._lock:
            if self._cursor >= len(self._turns):
                raise ScriptExhausted(
                    f"ScriptedProvider: script exhausted after {self._cursor} turn(s). "
                    "Add another entry to the script or stop the agent loop earlier."
                )
            entry = self._turns[self._cursor]
            self._cursor += 1
        tool_calls = [
            ToolCall(id=tc["id"], name=tc["name"], arguments=tc["arguments"])
            for tc in entry["tool_calls"]
        ]
        return entry["text"], tool_calls


# ── module-level singleton wired by the factory ────────────────────────

_singleton_lock = threading.Lock()
_singleton: ScriptedProvider | None = None


def get_scripted_provider() -> ScriptedProvider:
    """Return the process-wide ScriptedProvider, creating it on first use."""
    global _singleton
    with _singleton_lock:
        if _singleton is None:
            _singleton = ScriptedProvider()
        return _singleton


def reset_scripted_provider() -> None:
    """Drop the singleton (used by tests so script state never leaks across tests)."""
    global _singleton
    with _singleton_lock:
        _singleton = None
