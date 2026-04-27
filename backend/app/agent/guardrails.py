"""Lightweight intent classification and prompt-injection detection.

Pure functions only — no DB, no async, no app imports. Designed to be fast
(regex-only, no ML) and fully unit-testable in isolation.
"""

from __future__ import annotations

import re
from enum import Enum


class Intent(str, Enum):
    ANALYTICS = "analytics_question"
    CREATE_WIDGET = "create_dashboard_widget"
    MODIFY_DASHBOARD = "modify_dashboard"
    COMPETITOR = "competitor_analysis"
    IRRELEVANT = "irrelevant_or_unsupported"
    UNSAFE = "prompt_injection_or_unsafe"


# ---------------------------------------------------------------------------
# Injection detection
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?(previous|above|prior|all)\s+(instructions?|prompts?|rules?)", re.I),
    re.compile(r"reveal\s+(your|the)\s+(system\s+)?prompt", re.I),
    re.compile(r"(forget|disregard)\s+(everything|all|your)", re.I),
    re.compile(r"print\s+(your|the)\s+(instructions?|training|prompt|system)", re.I),
    re.compile(r"\bjailbreak\b", re.I),
    re.compile(r"\bDAN\b"),
    # persona-hijacking: "act as if you are", "pretend you are", "behave as a"
    re.compile(r"(act|pretend|behave)\s+as\s+(if\s+you\s+(are|were)\b|a\s+\w)", re.I),
]


def is_injection(text: str) -> bool:
    """Return True if *text* contains high-confidence prompt-injection patterns."""
    return any(p.search(text) for p in _INJECTION_PATTERNS)


# ---------------------------------------------------------------------------
# Out-of-scope topics
# ---------------------------------------------------------------------------

_IRRELEVANT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"\b(weather|forecast|temperature|humidity)\b",
        re.I,
    ),
    re.compile(
        r"\b(stock\s+price|bitcoin|crypto|cryptocurrency|lottery|gambling)\b",
        re.I,
    ),
    re.compile(
        r"\b(recipe|cook(ing)?|bake|baking|ingredient)\b",
        re.I,
    ),
    re.compile(
        r"\b(homework|essay|poem|song|lyrics|translate|translation)\b",
        re.I,
    ),
    re.compile(
        r"\b(politics|election|president|prime\s+minister|congress|parliament|religion|god|prayer)\b",
        re.I,
    ),
    re.compile(
        r"\b(write\s+(me\s+)?(a\s+)?(code|script|program)|debug\s+my\s+code)\b",
        re.I,
    ),
    re.compile(
        r"\b(generate\s+a\s+password|what\s+is\s+the\s+capital\s+of)\b",
        re.I,
    ),
]

# ---------------------------------------------------------------------------
# In-scope routing patterns
# ---------------------------------------------------------------------------

_COMPETITOR_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bcompetitors?\b", re.I),
    re.compile(r"\b(rival|rivalry|competition)\b", re.I),
    re.compile(r"\bvs\.?\s", re.I),
    re.compile(r"\bversus\b", re.I),
    re.compile(r"\bcompare\s+(us|me|my\s+business|to\b)", re.I),
    re.compile(r"\bnearby\s+(cafe|restaurant|bar|shop|store)\b", re.I),
]

_CREATE_WIDGET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bpin\s+(this|it)\b", re.I),
    re.compile(r"\b(add|put)\b.{0,30}\bdashboard\b", re.I),
    re.compile(r"\bcreate\s+(a\s+)?widget\b", re.I),
    re.compile(r"\bshow\s+(on\s+)?dashboard\b", re.I),
]

_MODIFY_DASHBOARD_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(remove\s+(the\s+)?\w+\s+widget|delete\s+(the\s+)?\w+\s+widget|reorder|rearrange\s+(the\s+)?dashboard|clear\s+(the\s+)?dashboard)\b", re.I),
]


def classify_intent(text: str) -> Intent:
    """Classify *text* into one of the Intent categories.

    Default-to-allow: ambiguous messages return ANALYTICS and reach the LLM.
    Only high-confidence out-of-scope or injection patterns are blocked here.
    """
    if not text or not text.strip():
        return Intent.ANALYTICS

    if is_injection(text):
        return Intent.UNSAFE

    if any(p.search(text) for p in _IRRELEVANT_PATTERNS):
        return Intent.IRRELEVANT

    if any(p.search(text) for p in _COMPETITOR_PATTERNS):
        return Intent.COMPETITOR

    if any(p.search(text) for p in _CREATE_WIDGET_PATTERNS):
        return Intent.CREATE_WIDGET

    if any(p.search(text) for p in _MODIFY_DASHBOARD_PATTERNS):
        return Intent.MODIFY_DASHBOARD

    return Intent.ANALYTICS
