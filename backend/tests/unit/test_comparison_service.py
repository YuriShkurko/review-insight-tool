"""Unit tests for comparison_service — cache logic, OpenAI call, snapshot building."""

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.errors import BusinessNotFoundError, ComparisonNotReadyError, ExternalProviderError
from app.schemas.analysis import InsightItem
from app.schemas.comparison import BusinessSnapshot
from app.services.comparison_service import (
    _call_openai_comparison,
    _format_snapshots_for_prompt,
    _mock_comparison,
    _normalize_comparison_result,
    _snapshot_from_business_and_analysis,
    generate_comparison,
)


def _make_snapshot(**overrides) -> BusinessSnapshot:
    defaults = {
        "business_id": uuid.uuid4(),
        "name": "Test Biz",
        "business_type": "restaurant",
        "avg_rating": 4.2,
        "total_reviews": 50,
        "summary": "Good place.",
        "top_complaints": [InsightItem(label="Slow", count=3)],
        "top_praise": [InsightItem(label="Friendly", count=5)],
        "action_items": ["Hire more staff"],
        "risk_areas": ["Wait times"],
        "recommended_focus": "Speed up service.",
    }
    defaults.update(overrides)
    return BusinessSnapshot(**defaults)


class TestSnapshotFromBusinessAndAnalysis:
    def test_returns_none_when_no_analysis(self):
        business = MagicMock()
        assert _snapshot_from_business_and_analysis(business, None) is None

    def test_builds_snapshot_from_analysis(self):
        business = MagicMock()
        business.id = uuid.uuid4()
        business.name = "My Bar"
        business.business_type = "bar"
        business.avg_rating = 4.5
        business.total_reviews = 100

        analysis = MagicMock()
        analysis.summary = "Great bar."
        analysis.top_complaints = [{"label": "Noise", "count": 3}]
        analysis.top_praise = [{"label": "Drinks", "count": 7}]
        analysis.action_items = ["Add acoustic panels"]
        analysis.risk_areas = ["Noise complaints"]
        analysis.recommended_focus = "Reduce noise."

        result = _snapshot_from_business_and_analysis(business, analysis)
        assert result.name == "My Bar"
        assert result.summary == "Great bar."
        assert len(result.top_complaints) == 1
        assert result.top_complaints[0].label == "Noise"


class TestFormatSnapshotsForPrompt:
    def test_produces_valid_json(self):
        target = _make_snapshot(name="Target")
        comp = _make_snapshot(name="Competitor")
        result = _format_snapshots_for_prompt(target, [comp])
        parsed = json.loads(result)
        assert parsed["target"]["name"] == "Target"
        assert len(parsed["competitors"]) == 1
        assert parsed["competitors"][0]["name"] == "Competitor"

    def test_multiple_competitors(self):
        target = _make_snapshot()
        comps = [_make_snapshot(name=f"Comp{i}") for i in range(3)]
        result = _format_snapshots_for_prompt(target, comps)
        parsed = json.loads(result)
        assert len(parsed["competitors"]) == 3


class TestCallOpenaiComparison:
    def test_no_api_key_returns_mock(self):
        with patch("app.services.comparison_service.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            result = _call_openai_comparison("prompt text")
        assert result == _mock_comparison()

    def test_valid_json_response(self):
        expected = {
            "comparison_summary": "Target is better",
            "strengths": ["Fast service"],
            "weaknesses": ["Higher prices"],
            "opportunities": ["Expand menu"],
        }
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=json.dumps(expected)))]

        with (
            patch("app.services.comparison_service.settings") as mock_settings,
            patch("app.services.comparison_service.OpenAI") as mock_openai_cls,
        ):
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_openai_cls.return_value.chat.completions.create.return_value = mock_response
            result = _call_openai_comparison("prompt text")

        assert result["comparison_summary"] == "Target is better"

    def test_invalid_json_falls_back_to_mock(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="not json!!!"))]

        with (
            patch("app.services.comparison_service.settings") as mock_settings,
            patch("app.services.comparison_service.OpenAI") as mock_openai_cls,
        ):
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_openai_cls.return_value.chat.completions.create.return_value = mock_response
            result = _call_openai_comparison("prompt")

        assert result == _mock_comparison()

    def test_openai_exception_raises_external_provider_error(self):
        with (
            patch("app.services.comparison_service.settings") as mock_settings,
            patch("app.services.comparison_service.OpenAI") as mock_openai_cls,
        ):
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_openai_cls.return_value.chat.completions.create.side_effect = Exception("timeout")
            with pytest.raises(ExternalProviderError):
                _call_openai_comparison("prompt")


class TestNormalizeComparisonResult:
    def test_full_result(self):
        raw = {
            "comparison_summary": "They are equal.",
            "strengths": ["Fast", "Clean"],
            "weaknesses": ["Pricey"],
            "opportunities": ["Expand hours"],
        }
        result = _normalize_comparison_result(raw)
        assert result["comparison_summary"] == "They are equal."
        assert len(result["strengths"]) == 2

    def test_missing_fields_default_to_empty(self):
        result = _normalize_comparison_result({})
        assert result["comparison_summary"] == ""
        assert result["strengths"] == []
        assert result["weaknesses"] == []
        assert result["opportunities"] == []

    def test_none_values_handled(self):
        raw = {
            "comparison_summary": None,
            "strengths": None,
            "weaknesses": None,
            "opportunities": None,
        }
        result = _normalize_comparison_result(raw)
        assert result["comparison_summary"] == ""
        assert result["strengths"] == []

    def test_filters_falsy_items(self):
        raw = {"strengths": ["Good", "", None, "Fast"]}
        result = _normalize_comparison_result(raw)
        assert result["strengths"] == ["Good", "Fast"]


class TestGenerateComparison:
    def _setup_db(self, target_biz, target_analysis, links, competitors, comp_analyses):
        db = MagicMock()

        # We need to handle multiple db.query() calls with different models
        # Use side_effect to return different mocks for each call
        def query_side_effect(model):
            mock_query = MagicMock()
            if model.__name__ == "Business":
                # Returns target_biz first, then competitors in order
                biz_iter = iter([target_biz, *competitors])
                mock_query.filter.return_value.first.side_effect = lambda: next(biz_iter, None)
            elif model.__name__ == "Analysis":
                analysis_iter = iter([target_analysis, *comp_analyses])
                mock_query.filter.return_value.first.side_effect = lambda: next(
                    analysis_iter, None
                )
            elif model.__name__ == "CompetitorLink":
                mock_query.filter.return_value.all.return_value = links
            return mock_query

        db.query.side_effect = query_side_effect
        return db

    def test_business_not_found_raises(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(BusinessNotFoundError):
            generate_comparison(db, uuid.uuid4(), uuid.uuid4())

    def test_no_target_analysis_raises(self):
        db = MagicMock()
        biz = MagicMock()
        # First call: business found, second call: no analysis
        db.query.return_value.filter.return_value.first.side_effect = [biz, None]
        with pytest.raises(ComparisonNotReadyError, match="Run analysis"):
            generate_comparison(db, uuid.uuid4(), uuid.uuid4())

    def _make_biz_mock(
        self,
        user_id,
        biz_id=None,
        biz_name="Biz",
        biz_type="bar",
        avg_rating=4.0,
        total_reviews=10,
    ):
        biz = MagicMock()
        biz.id = biz_id or uuid.uuid4()
        biz.user_id = user_id
        biz.configure_mock(name=biz_name)
        biz.business_type = biz_type
        biz.avg_rating = avg_rating
        biz.total_reviews = total_reviews
        return biz

    def _make_analysis_mock(self, **overrides):
        defaults = {
            "summary": "s",
            "top_complaints": [],
            "top_praise": [],
            "action_items": [],
            "risk_areas": [],
            "recommended_focus": "",
        }
        defaults.update(overrides)
        return MagicMock(**defaults)

    def test_no_competitor_analyses_raises(self):
        user_id = uuid.uuid4()
        biz_id = uuid.uuid4()
        comp_id = uuid.uuid4()

        biz = self._make_biz_mock(user_id, biz_id=biz_id)
        analysis = self._make_analysis_mock()
        comp_biz = self._make_biz_mock(user_id, biz_id=comp_id, biz_name="Comp")
        link = MagicMock(competitor_business_id=comp_id)

        db = MagicMock()
        from app.models.analysis import Analysis
        from app.models.business import Business
        from app.models.competitor_link import CompetitorLink

        biz_iter = iter([biz, comp_biz])
        analysis_iter = iter([analysis, None])

        def query_side_effect(model):
            q = MagicMock()
            if model is Business:
                q.filter.return_value.first.side_effect = lambda: next(biz_iter)
            elif model is Analysis:
                q.filter.return_value.first.side_effect = lambda: next(analysis_iter)
            elif model is CompetitorLink:
                q.filter.return_value.all.return_value = [link]
            return q

        db.query.side_effect = query_side_effect

        with (
            patch("app.mongo.get_cached_comparison", return_value=None),
            pytest.raises(ComparisonNotReadyError, match="Add at least one"),
        ):
            generate_comparison(db, biz_id, user_id)

    def test_cache_hit_skips_llm(self):
        user_id = uuid.uuid4()
        biz_id = uuid.uuid4()
        comp_id = uuid.uuid4()

        biz = self._make_biz_mock(user_id, biz_id=biz_id)
        analysis = self._make_analysis_mock(
            summary="good",
            top_complaints=[{"label": "x", "count": 1}],
            top_praise=[{"label": "y", "count": 2}],
            action_items=["do x"],
            risk_areas=["risk"],
            recommended_focus="focus",
        )
        link = MagicMock(competitor_business_id=comp_id)
        comp_biz = self._make_biz_mock(
            user_id, biz_id=comp_id, biz_name="Comp", avg_rating=3.5, total_reviews=20
        )
        comp_analysis = self._make_analysis_mock(
            summary="ok",
            top_complaints=[{"label": "a", "count": 1}],
            top_praise=[{"label": "b", "count": 2}],
            action_items=["do a"],
            risk_areas=["r"],
            recommended_focus="f",
        )

        db = self._setup_db(biz, analysis, [link], [comp_biz], [comp_analysis])

        cached = {
            "comparison_summary": "cached summary",
            "strengths": ["s1"],
            "weaknesses": ["w1"],
            "opportunities": ["o1"],
        }

        with (
            patch("app.mongo.get_cached_comparison", return_value=cached),
            patch("app.services.comparison_service._call_openai_comparison") as mock_llm,
        ):
            result = generate_comparison(db, biz_id, user_id)

        mock_llm.assert_not_called()
        assert result.comparison_summary == "cached summary"


class TestMockComparison:
    def test_has_all_required_keys(self):
        result = _mock_comparison()
        assert "comparison_summary" in result
        assert "strengths" in result
        assert "weaknesses" in result
        assert "opportunities" in result
