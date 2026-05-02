"""Unit tests for synthetic_monitor helpers.

Run with:  python -m pytest scripts/test_synthetic_monitor.py -v
"""

from __future__ import annotations

import sys
import os

# Allow importing from the scripts directory without installation.
sys.path.insert(0, os.path.dirname(__file__))

import io
import pytest
from synthetic_monitor import (
    _OFFLINE_PLACE_IDS,
    _pick_place_id,
    SyntheticMonitor,
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID,
)


class TestPickPlaceId:
    def test_returns_value_from_pool(self):
        result = _pick_place_id()
        assert result in _OFFLINE_PLACE_IDS

    def test_no_exclusion_returns_first(self):
        # Deterministic: always the first element when nothing is excluded.
        assert _pick_place_id() == _OFFLINE_PLACE_IDS[0]

    def test_excludes_given_id(self):
        excluded = _OFFLINE_PLACE_IDS[0]
        result = _pick_place_id(exclude={excluded})
        assert result != excluded
        assert result in _OFFLINE_PLACE_IDS

    def test_excludes_multiple_ids(self):
        excluded = set(_OFFLINE_PLACE_IDS[:3])
        result = _pick_place_id(exclude=excluded)
        assert result not in excluded
        assert result in _OFFLINE_PLACE_IDS

    def test_target_and_competitor_never_same(self):
        """Simulates the monitor's two-step selection — result must differ."""
        target = _pick_place_id()
        comp = _pick_place_id(exclude={target})
        assert target != comp

    def test_raises_when_all_excluded(self):
        with pytest.raises(RuntimeError, match="setup error"):
            _pick_place_id(exclude=set(_OFFLINE_PLACE_IDS))

    def test_raises_message_mentions_pool_size(self):
        try:
            _pick_place_id(exclude=set(_OFFLINE_PLACE_IDS))
        except RuntimeError as exc:
            assert str(len(_OFFLINE_PLACE_IDS)) in str(exc)

    def test_empty_exclude_is_equivalent_to_no_exclude(self):
        assert _pick_place_id(exclude=set()) == _pick_place_id()

    def test_pool_has_enough_entries_for_target_plus_competitor(self):
        """Pool must have at least 2 entries so a competitor can always be found."""
        assert len(_OFFLINE_PLACE_IDS) >= 2


class TestDependencyAwareSkipping:
    def _monitor(self) -> SyntheticMonitor:
        return SyntheticMonitor()

    def test_check_deps_passes_when_prereqs_passed(self):
        m = self._monitor()
        m._step_results["fetch_reviews"] = "passed"
        assert m._check_deps("analyze") is None

    def test_check_deps_returns_blocker_when_prereq_failed(self):
        m = self._monitor()
        m._step_results["fetch_reviews"] = "failed"
        assert m._check_deps("analyze") == "fetch_reviews"

    def test_check_deps_returns_blocker_when_prereq_skipped(self):
        m = self._monitor()
        m._step_results["fetch_competitor_reviews"] = "skipped"
        assert m._check_deps("analyze_competitor") == "fetch_competitor_reviews"

    def test_check_deps_returns_blocker_when_prereq_missing(self):
        m = self._monitor()
        # analyze_competitor not in step_results at all
        assert m._check_deps("comparison_cold") == "analyze_competitor"

    def test_analyze_competitor_timeout_blocks_both_comparisons(self):
        m = self._monitor()
        m._step_results["add_competitor"] = "passed"
        m._step_results["fetch_competitor_reviews"] = "passed"
        m._step_results["analyze_competitor"] = "failed"
        assert m._check_deps("comparison_cold") == "analyze_competitor"
        assert m._check_deps("comparison_cached") == "analyze_competitor"

    def test_skip_records_skipped_outcome(self):
        m = self._monitor()
        m._skip("comparison_cold", "blocked: analyze_competitor did not pass")
        assert m._step_results["comparison_cold"] == "skipped"
        result = m.results[0]
        assert result["name"] == "comparison_cold"
        assert result["success"] is False
        assert "skipped" in result["detail"]
        assert "analyze_competitor" in result["detail"]

    def test_skip_wording_mentions_blocking_prereq(self):
        m = self._monitor()
        m._skip("comparison_cached", "blocked: analyze_competitor did not pass")
        assert "analyze_competitor" in m.results[0]["detail"]

    def test_no_deps_step_always_passes_check(self):
        m = self._monitor()
        assert m._check_deps("fetch_reviews") is None
        assert m._check_deps("health_check") is None


class TestTelegramEnvSanitisation:
    def test_token_stripped_at_import(self):
        # TELEGRAM_TOKEN is the module-level constant resolved at import time.
        # It should not contain leading/trailing whitespace or newlines.
        assert TELEGRAM_TOKEN == TELEGRAM_TOKEN.strip()

    def test_chat_id_stripped_at_import(self):
        assert TELEGRAM_CHAT_ID == TELEGRAM_CHAT_ID.strip()

    def test_send_alert_with_control_char_url_prints_error(self, capsys):
        import synthetic_monitor as sm
        old_token = sm.TELEGRAM_TOKEN
        old_chat = sm.TELEGRAM_CHAT_ID
        # Inject a newline into the token so the URL becomes invalid;
        # set a valid-looking chat ID so the early "not configured" guard is bypassed.
        sm.TELEGRAM_TOKEN = "bad\ntoken"
        sm.TELEGRAM_CHAT_ID = "12345"
        try:
            m = SyntheticMonitor()
            m._send_alert("test alert")
            captured = capsys.readouterr()
            assert "ALERT SEND FAILED" in captured.err or "non-printable" in captured.err
        finally:
            sm.TELEGRAM_TOKEN = old_token
            sm.TELEGRAM_CHAT_ID = old_chat

    def test_send_alert_does_not_raise_on_bad_url(self, capsys):
        import synthetic_monitor as sm
        old_token = sm.TELEGRAM_TOKEN
        old_chat = sm.TELEGRAM_CHAT_ID
        sm.TELEGRAM_TOKEN = "bad\ntoken"
        sm.TELEGRAM_CHAT_ID = "12345"
        try:
            m = SyntheticMonitor()
            m._send_alert("should not raise")
            # Reaching here means no exception was raised
        finally:
            sm.TELEGRAM_TOKEN = old_token
            sm.TELEGRAM_CHAT_ID = old_chat
