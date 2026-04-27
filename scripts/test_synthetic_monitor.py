"""Unit tests for synthetic_monitor helpers.

Run with:  python -m pytest scripts/test_synthetic_monitor.py -v
"""

from __future__ import annotations

import sys
import os

# Allow importing from the scripts directory without installation.
sys.path.insert(0, os.path.dirname(__file__))

import pytest
from synthetic_monitor import _OFFLINE_PLACE_IDS, _pick_place_id


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
