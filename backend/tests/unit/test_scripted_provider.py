"""Unit tests for ScriptedProvider and the LLM factory's scripted branch."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.llm.base import ToolCall
from app.llm.scripted import (
    ScriptedProvider,
    ScriptExhausted,
    get_scripted_provider,
    reset_scripted_provider,
)


def test_returns_turns_in_order():
    p = ScriptedProvider(
        [
            {"text": "", "tool_calls": [{"name": "get_dashboard", "arguments": {}}]},
            {"text": "Done.", "tool_calls": []},
        ]
    )
    text, calls = p.complete_with_tools([], [])
    assert text == ""
    assert [(tc.name, tc.arguments) for tc in calls] == [("get_dashboard", {})]
    assert all(isinstance(tc, ToolCall) for tc in calls)

    text, calls = p.complete_with_tools([], [])
    assert text == "Done."
    assert calls == []


def test_complete_returns_text_only():
    p = ScriptedProvider(
        [
            {"text": "hello", "tool_calls": []},
        ]
    )
    assert p.complete([]) == "hello"


def test_exhaustion_raises_clearly():
    p = ScriptedProvider([{"text": "only one", "tool_calls": []}])
    p.complete_with_tools([], [])
    with pytest.raises(ScriptExhausted) as excinfo:
        p.complete_with_tools([], [])
    msg = str(excinfo.value)
    assert "exhausted" in msg.lower()
    assert "1 turn" in msg


def test_remaining_and_reset():
    p = ScriptedProvider(
        [
            {"text": "a", "tool_calls": []},
            {"text": "b", "tool_calls": []},
        ]
    )
    assert p.remaining == 2
    p.complete_with_tools([], [])
    assert p.remaining == 1
    p.reset()
    assert p.remaining == 2


def test_set_script_replaces_and_rewinds():
    p = ScriptedProvider([{"text": "old", "tool_calls": []}])
    p.set_script(
        [
            {"text": "new1", "tool_calls": []},
            {"text": "new2", "tool_calls": []},
        ]
    )
    assert p.remaining == 2
    assert p.complete([]) == "new1"


def test_load_from_path(tmp_path: Path):
    fp = tmp_path / "script.json"
    fp.write_text(
        json.dumps(
            [
                {"text": "loaded", "tool_calls": []},
            ]
        )
    )
    p = ScriptedProvider()
    p.load_from_path(fp)
    assert p.complete([]) == "loaded"


def test_load_from_missing_path_raises(tmp_path: Path):
    p = ScriptedProvider()
    with pytest.raises(FileNotFoundError):
        p.load_from_path(tmp_path / "nope.json")


@pytest.mark.parametrize(
    "bad_script,fragment",
    [
        ("not a list", "must be a JSON array"),
        ([1, 2, 3], "must be an object"),
        ([{"text": 5, "tool_calls": []}], "'text' must be a string"),
        ([{"tool_calls": "not a list"}], "'tool_calls' must be a list"),
        ([{"tool_calls": [{"arguments": {}}]}], "non-empty 'name'"),
        ([{"tool_calls": [{"name": "x", "arguments": "no"}]}], "'arguments' must be an object"),
    ],
)
def test_invalid_scripts_rejected(bad_script, fragment):
    with pytest.raises(ValueError) as excinfo:
        ScriptedProvider(bad_script)
    assert fragment in str(excinfo.value)


def test_tool_call_id_synthesized_when_missing():
    p = ScriptedProvider(
        [
            {
                "text": "",
                "tool_calls": [{"name": "get_dashboard", "arguments": {}}],
            }
        ]
    )
    _, calls = p.complete_with_tools([], [])
    assert calls[0].id  # non-empty
    assert calls[0].id != ""


def test_factory_returns_scripted_only_when_testing(monkeypatch):
    """LLM_PROVIDER=scripted is ignored unless TESTING=true (production safety)."""
    import app.config as config_mod
    from app.llm.factory import get_llm_provider

    reset_scripted_provider()

    monkeypatch.setattr(config_mod.settings, "LLM_PROVIDER", "scripted")
    monkeypatch.setattr(config_mod.settings, "TESTING", False)
    monkeypatch.setattr(config_mod.settings, "AGENT_SCRIPT_PATH", "")
    assert get_llm_provider() is None, (
        "scripted provider must NOT be selected when TESTING is false"
    )

    monkeypatch.setattr(config_mod.settings, "TESTING", True)
    provider = get_llm_provider()
    assert isinstance(provider, ScriptedProvider)
    # Singleton: subsequent calls return the same object so set_script() sticks
    assert provider is get_scripted_provider()


def test_factory_loads_path_when_configured(monkeypatch, tmp_path: Path):
    import app.config as config_mod
    from app.llm.factory import get_llm_provider

    reset_scripted_provider()
    fp = tmp_path / "s.json"
    fp.write_text(json.dumps([{"text": "from-path", "tool_calls": []}]))

    monkeypatch.setattr(config_mod.settings, "LLM_PROVIDER", "scripted")
    monkeypatch.setattr(config_mod.settings, "TESTING", True)
    monkeypatch.setattr(config_mod.settings, "AGENT_SCRIPT_PATH", str(fp))

    provider = get_llm_provider()
    assert isinstance(provider, ScriptedProvider)
    assert provider.complete([]) == "from-path"
