"""Tests for analysis result normalization and prompt generation."""

from app.services.analysis_service import (
    _build_system_prompt,
    _normalize_insights,
    _normalize_result,
    _normalize_strings,
)


class TestNormalizeInsights:
    def test_dict_items(self):
        items = [{"label": "Slow service", "count": 3}]
        result = _normalize_insights(items)
        assert result == [{"label": "Slow service", "count": 3}]

    def test_string_items_get_zero_count(self):
        items = ["Slow service", "Bad food"]
        result = _normalize_insights(items)
        assert result == [
            {"label": "Slow service", "count": 0},
            {"label": "Bad food", "count": 0},
        ]

    def test_mixed_items(self):
        items = [{"label": "Good coffee", "count": 5}, "Nice ambiance"]
        result = _normalize_insights(items)
        assert len(result) == 2
        assert result[0] == {"label": "Good coffee", "count": 5}
        assert result[1] == {"label": "Nice ambiance", "count": 0}

    def test_empty_list(self):
        assert _normalize_insights([]) == []

    def test_missing_label_defaults_to_empty_string(self):
        items = [{"count": 3}]
        result = _normalize_insights(items)
        assert result[0]["label"] == ""

    def test_missing_count_defaults_to_zero(self):
        items = [{"label": "Something"}]
        result = _normalize_insights(items)
        assert result[0]["count"] == 0


class TestNormalizeStrings:
    def test_filters_empty_values(self):
        assert _normalize_strings(["a", "", "b", None]) == ["a", "b"]

    def test_converts_to_strings(self):
        assert _normalize_strings([1, 2.5, True]) == ["1", "2.5", "True"]

    def test_empty_list(self):
        assert _normalize_strings([]) == []


class TestNormalizeResult:
    def test_full_result(self):
        raw = {
            "summary": "Great place.",
            "top_complaints": [{"label": "Slow", "count": 2}],
            "top_praise": [{"label": "Friendly", "count": 4}],
            "action_items": ["Hire more staff"],
            "risk_areas": ["Wait times"],
            "recommended_focus": "Reduce wait times.",
        }
        result = _normalize_result(raw)
        assert result["summary"] == "Great place."
        assert len(result["top_complaints"]) == 1
        assert len(result["top_praise"]) == 1
        assert result["action_items"] == ["Hire more staff"]
        assert result["risk_areas"] == ["Wait times"]
        assert result["recommended_focus"] == "Reduce wait times."

    def test_missing_fields_get_defaults(self):
        result = _normalize_result({})
        assert result["summary"] == ""
        assert result["top_complaints"] == []
        assert result["top_praise"] == []
        assert result["action_items"] == []
        assert result["risk_areas"] == []
        assert result["recommended_focus"] == ""

    def test_none_summary_becomes_empty_string(self):
        result = _normalize_result({"summary": None})
        assert result["summary"] == ""


class TestBuildSystemPrompt:
    def test_known_type_includes_focus_areas(self):
        prompt = _build_system_prompt("restaurant")
        assert "restaurant" in prompt
        assert "food quality" in prompt
        assert "wait times" in prompt

    def test_unknown_type_uses_generic_instruction(self):
        prompt = _build_system_prompt("other")
        assert "customer experience dimensions" in prompt

    def test_all_known_types_produce_valid_prompts(self):
        known_types = ["restaurant", "bar", "cafe", "gym", "salon", "hotel", "clinic", "retail"]
        for btype in known_types:
            prompt = _build_system_prompt(btype)
            assert btype in prompt
            assert "JSON" in prompt
