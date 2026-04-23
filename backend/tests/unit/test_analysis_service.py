"""Unit tests for analysis_service — OpenAI call, response parsing, overwrite flow."""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.errors import ExternalProviderError, NoReviewsError
from app.services.analysis_service import (
    _call_openai,
    _format_reviews_for_prompt,
    _mock_analysis,
    analyze_reviews,
)


class TestFormatReviewsForPrompt:
    def test_formats_rating_and_text(self):
        r1 = MagicMock(rating=5, text="Great!")
        r2 = MagicMock(rating=1, text="Terrible.")
        result = _format_reviews_for_prompt([r1, r2])
        assert "- [5/5] Great!" in result
        assert "- [1/5] Terrible." in result

    def test_none_text_becomes_no_text(self):
        r = MagicMock(rating=3, text=None)
        result = _format_reviews_for_prompt([r])
        assert "(no text)" in result

    def test_empty_list(self):
        assert _format_reviews_for_prompt([]) == ""


class TestCallOpenai:
    def test_no_api_key_returns_mock(self):
        with patch("app.services.analysis_service.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            result = _call_openai("system", "reviews")
        assert result == _mock_analysis()

    def test_valid_json_response(self):
        expected = {"summary": "Good place", "top_complaints": [], "top_praise": []}
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=json.dumps(expected)))]

        with (
            patch("app.services.analysis_service.settings") as mock_settings,
            patch("app.services.analysis_service.OpenAI") as mock_openai_cls,
        ):
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_openai_cls.return_value.chat.completions.create.return_value = mock_response
            result = _call_openai("system", "reviews")

        assert result["summary"] == "Good place"

    def test_invalid_json_falls_back(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="not valid json {{{"))]

        with (
            patch("app.services.analysis_service.settings") as mock_settings,
            patch("app.services.analysis_service.OpenAI") as mock_openai_cls,
        ):
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_openai_cls.return_value.chat.completions.create.return_value = mock_response
            result = _call_openai("system", "reviews")

        assert result["summary"] == "not valid json {{{"
        assert result["top_complaints"] == []

    def test_openai_exception_raises_external_provider_error(self):
        with (
            patch("app.services.analysis_service.settings") as mock_settings,
            patch("app.services.analysis_service.OpenAI") as mock_openai_cls,
        ):
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_openai_cls.return_value.chat.completions.create.side_effect = Exception(
                "API down"
            )
            with pytest.raises(ExternalProviderError):
                _call_openai("system", "reviews")

    def test_none_content_returns_empty_dict(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=None))]

        with (
            patch("app.services.analysis_service.settings") as mock_settings,
            patch("app.services.analysis_service.OpenAI") as mock_openai_cls,
        ):
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_openai_cls.return_value.chat.completions.create.return_value = mock_response
            result = _call_openai("system", "reviews")

        assert result == {}


class TestAnalyzeReviews:
    def _make_review(self, rating=4, text="Good"):
        r = MagicMock()
        r.rating = rating
        r.text = text
        return r

    def _make_business(self, business_type="restaurant"):
        b = MagicMock()
        b.business_type = business_type
        return b

    def test_no_reviews_raises(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = self._make_business()
        db.query.return_value.filter.return_value.all.return_value = []
        with pytest.raises(NoReviewsError):
            analyze_reviews(db, uuid.uuid4())

    def test_truncates_over_max_reviews(self):
        db = MagicMock()
        business = self._make_business()
        db.query.return_value.filter.return_value.first.return_value = business
        reviews = [self._make_review() for _ in range(250)]
        db.query.return_value.filter.return_value.all.return_value = reviews

        with patch("app.services.analysis_service._call_openai") as mock_call:
            mock_call.return_value = _mock_analysis()
            # No existing analysis
            db.query.return_value.filter.return_value.first.side_effect = [
                business,  # business query
                None,  # existing analysis query
            ]
            db.query.return_value.filter.return_value.all.return_value = reviews

            analyze_reviews(db, uuid.uuid4())

            # Verify the prompt was built with truncated reviews
            call_args = mock_call.call_args[0]
            review_text = call_args[1]
            assert review_text.count("\n") <= 200  # MAX_REVIEWS_FOR_ANALYSIS

    def test_creates_new_analysis(self):
        db = MagicMock()
        business = self._make_business()
        reviews = [self._make_review()]
        biz_id = uuid.uuid4()

        # First filter().first() → business, second → None (no existing analysis)
        db.query.return_value.filter.return_value.first.side_effect = [business, None]
        db.query.return_value.filter.return_value.all.return_value = reviews

        with patch("app.services.analysis_service._call_openai") as mock_call:
            mock_call.return_value = _mock_analysis()
            result = analyze_reviews(db, biz_id)

        db.add.assert_called_once()
        db.commit.assert_called_once()
        assert result is not None

    def test_overwrites_existing_and_archives(self):
        db = MagicMock()
        business = self._make_business()
        reviews = [self._make_review()]
        biz_id = uuid.uuid4()

        existing_analysis = MagicMock()
        existing_analysis.summary = "old summary"
        existing_analysis.top_complaints = []
        existing_analysis.top_praise = []
        existing_analysis.action_items = []
        existing_analysis.risk_areas = []
        existing_analysis.recommended_focus = ""
        existing_analysis.created_at = datetime(2025, 1, 1, tzinfo=UTC)

        db.query.return_value.filter.return_value.first.side_effect = [
            business,
            existing_analysis,
        ]
        db.query.return_value.filter.return_value.all.return_value = reviews

        with (
            patch("app.services.analysis_service._call_openai") as mock_call,
            patch("app.mongo.archive_analysis") as mock_archive,
        ):
            mock_call.return_value = _mock_analysis()
            analyze_reviews(db, biz_id)

        mock_archive.assert_called_once()
        assert mock_archive.call_args.kwargs["business_id"] == str(biz_id)
        assert existing_analysis.summary == _mock_analysis()["summary"]
        db.commit.assert_called_once()


class TestMockAnalysis:
    def test_has_all_required_keys(self):
        result = _mock_analysis()
        assert "summary" in result
        assert "top_complaints" in result
        assert "top_praise" in result
        assert "action_items" in result
        assert "risk_areas" in result
        assert "recommended_focus" in result

    def test_complaints_and_praise_are_dicts(self):
        result = _mock_analysis()
        for item in result["top_complaints"]:
            assert "label" in item
            assert "count" in item
