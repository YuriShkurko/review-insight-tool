"""Unit tests for agent tool functions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from app.agent.system_prompt import build_system_prompt
from app.agent.tools import (
    WIDGET_TYPES,
    _coerce_pin_widget_arguments,
    _get_rating_distribution,
    _get_top_issues,
    _pin_widget,
    execute_tool,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_review(
    rating: int,
    text: str | None = None,
    days_ago: int = 5,
    business_id: uuid.UUID | None = None,
) -> MagicMock:
    r = MagicMock()
    r.id = uuid.uuid4()
    r.rating = rating
    r.text = text
    r.business_id = business_id or uuid.uuid4()
    r.published_at = datetime.now(UTC) - timedelta(days=days_ago)
    return r


def _make_db(reviews: list, analysis_complaints: list | None = None) -> MagicMock:
    """Build a mock db Session that returns the given reviews and optional analysis."""
    from app.models.analysis import Analysis

    db = MagicMock()

    def _query(model):
        q = MagicMock()
        if model.__name__ == "Review":
            q.filter.return_value = q
            q.all.return_value = reviews
        elif model.__name__ == "Analysis":
            q.filter.return_value = q
            if analysis_complaints is not None:
                analysis = MagicMock(spec=Analysis)
                analysis.top_complaints = [
                    {"label": label, "count": 1} for label in analysis_complaints
                ]
                q.first.return_value = analysis
            else:
                q.first.return_value = None
        elif model.__name__ == "WorkspaceWidget":
            q.filter.return_value = q
            q.count.return_value = 0
        else:
            q.filter.return_value = q
            q.first.return_value = None
            q.all.return_value = []
        return q

    db.query.side_effect = _query
    return db


# ---------------------------------------------------------------------------
# _get_top_issues tests
# ---------------------------------------------------------------------------


class TestGetTopIssues:
    def test_empty_reviews_returns_empty_list(self):
        db = _make_db([])
        result = _get_top_issues(db, uuid.uuid4(), limit=5, days=30)
        assert result["issues"] == []
        assert result["total_reviews_analyzed"] == 0

    def test_returns_severity_labels(self):
        biz_id = uuid.uuid4()
        reviews = [
            _make_review(1, "Terrible wait times", days_ago=3, business_id=biz_id),
            _make_review(1, "Very slow wait times", days_ago=5, business_id=biz_id),
            _make_review(4, "Great atmosphere", days_ago=2, business_id=biz_id),
        ]
        db = _make_db(reviews, analysis_complaints=["wait times"])
        result = _get_top_issues(db, biz_id, limit=5, days=30)
        severities = {issue["severity"] for issue in result["issues"]}
        assert severities <= {"critical", "notable", "minor"}
        # The wait-times group has avg 1.0, recent → should be critical
        wait_issue = next((i for i in result["issues"] if "wait" in i["theme"].lower()), None)
        assert wait_issue is not None
        assert wait_issue["severity"] == "critical"

    def test_recency_weight_ranks_recent_issues_higher(self):
        """Two identical single-review groups: the recent one should rank first."""
        biz_id = uuid.uuid4()
        old_review = _make_review(1, "bad parking", days_ago=60, business_id=biz_id)
        recent_review = _make_review(1, "bad service", days_ago=3, business_id=biz_id)
        db = _make_db(
            [old_review, recent_review],
            analysis_complaints=["parking", "service"],
        )
        result = _get_top_issues(db, biz_id, limit=5, days=90)
        issues = result["issues"]
        # Both are 1-star; recent "service" should outrank old "parking"
        assert len(issues) >= 2
        service_idx = next(
            (i for i, iss in enumerate(issues) if "service" in iss["theme"].lower()), None
        )
        parking_idx = next(
            (i for i, iss in enumerate(issues) if "parking" in iss["theme"].lower()), None
        )
        assert service_idx is not None and parking_idx is not None
        assert service_idx < parking_idx

    def test_limit_respected(self):
        biz_id = uuid.uuid4()
        reviews = [
            _make_review(2, f"issue {i}", days_ago=i, business_id=biz_id) for i in range(10)
        ]
        db = _make_db(reviews)
        result = _get_top_issues(db, biz_id, limit=3, days=30)
        assert len(result["issues"]) <= 3

    def test_fallback_to_star_buckets_without_analysis(self):
        biz_id = uuid.uuid4()
        reviews = [
            _make_review(1, "bad", days_ago=2, business_id=biz_id),
            _make_review(5, "great", days_ago=2, business_id=biz_id),
        ]
        db = _make_db(reviews, analysis_complaints=None)
        result = _get_top_issues(db, biz_id, limit=5, days=30)
        assert len(result["issues"]) > 0
        themes = {i["theme"] for i in result["issues"]}
        # Should have star-based bucket names
        assert any("star" in t.lower() for t in themes)

    def test_representative_quote_is_short(self):
        biz_id = uuid.uuid4()
        long_text = "x" * 200
        short_text = "bad service"
        reviews = [
            _make_review(1, long_text, days_ago=3, business_id=biz_id),
            _make_review(1, short_text, days_ago=3, business_id=biz_id),
        ]
        db = _make_db(reviews, analysis_complaints=None)
        result = _get_top_issues(db, biz_id, limit=5, days=30)
        for issue in result["issues"]:
            quote = issue.get("representative_quote")
            if quote:
                assert len(quote) <= 120


# ---------------------------------------------------------------------------
# pin_widget argument coercion + execute_tool
# ---------------------------------------------------------------------------


class TestCoercePinWidgetArguments:
    def test_strips_unknown_keys(self):
        raw = {
            "widget_type": "line_chart",
            "title": "Trend",
            "data": {"series": []},
            "reasoning": "user asked for chart",
        }
        coerced = _coerce_pin_widget_arguments(raw)
        assert coerced == {
            "widget_type": "line_chart",
            "title": "Trend",
            "data": {"series": []},
        }

    def test_non_dict_data_becomes_empty_dict(self):
        coerced = _coerce_pin_widget_arguments(
            {"widget_type": "metric_card", "title": "X", "data": [1, 2]}
        )
        assert coerced["data"] == {}


class TestGetRatingDistribution:
    def test_counts_by_star(self):
        biz_id = uuid.uuid4()
        reviews = [
            _make_review(5, business_id=biz_id),
            _make_review(5, business_id=biz_id),
            _make_review(1, business_id=biz_id),
        ]
        db = _make_db(reviews)
        result = _get_rating_distribution(db, biz_id, days=30)
        assert result["total"] == 3
        assert result["bars"][4]["label"] == "5★"
        assert result["bars"][4]["value"] == 2
        assert result["bars"][0]["value"] == 1


class TestExecuteToolPinWidgetIgnoresExtraKeys:
    def test_extra_arguments_do_not_break_pin(self):
        biz_id = uuid.uuid4()
        user_id = uuid.uuid4()
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.count.return_value = 0
        db.query.return_value = q
        db.refresh.side_effect = lambda w: None

        result = execute_tool(
            "pin_widget",
            {
                "widget_type": "line_chart",
                "title": "Hi",
                "data": {"series": []},
                "chain_of_thought": "omit me",
            },
            db,
            biz_id,
            user_id,
        )
        assert result.get("pinned") is True
        assert "widget_id" in result


# ---------------------------------------------------------------------------
# _pin_widget validation
# ---------------------------------------------------------------------------


class TestPinWidgetValidation:
    def test_valid_widget_type_is_accepted(self):
        biz_id = uuid.uuid4()
        user_id = uuid.uuid4()
        widget = MagicMock()
        widget.id = uuid.uuid4()

        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.count.return_value = 0
        db.query.return_value = q
        db.refresh.side_effect = lambda w: None

        # Should not raise
        result = _pin_widget(db, biz_id, user_id, widget_type="line_chart", title="Chart", data={})
        assert result["pinned"] is True
        assert "widget_id" in result

    def test_invalid_widget_type_returns_pinned_false(self):
        db = MagicMock()
        result = _pin_widget(
            db, uuid.uuid4(), uuid.uuid4(), widget_type="unknown_chart", title="Bad", data={}
        )
        assert result["pinned"] is False
        assert "error" in result
        # db should NOT have been touched
        db.add.assert_not_called()

    def test_all_defined_widget_types_are_accepted(self):
        for wt in WIDGET_TYPES:
            db = MagicMock()
            q = MagicMock()
            q.filter.return_value = q
            q.count.return_value = 0
            db.query.return_value = q
            db.refresh.side_effect = lambda w: None

            result = _pin_widget(
                db, uuid.uuid4(), uuid.uuid4(), widget_type=wt, title="T", data={}
            )
            assert result["pinned"] is True, f"widget_type={wt!r} should be accepted"


# ---------------------------------------------------------------------------
# system_prompt synthesis instructions
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    def test_prompt_includes_consultant_style_instruction(self):
        business = MagicMock()
        business.name = "Test Cafe"
        business.business_type = "cafe"
        business.address = "123 Main St"
        business.avg_rating = 4.2
        business.total_reviews = 50

        prompt = build_system_prompt(business)
        assert "consultant" in prompt.lower(), "Prompt should mention consultant-style language"

    def test_prompt_references_get_top_issues(self):
        business = MagicMock()
        business.name = "Test Bar"
        business.business_type = "bar"
        business.address = None
        business.avg_rating = None
        business.total_reviews = 0

        prompt = build_system_prompt(business)
        assert "get_top_issues" in prompt, "Prompt should instruct agent to use get_top_issues"

    def test_prompt_contains_three_step_pin_sequence(self):
        """Prompt must describe the required data→pin→report sequence."""
        business = MagicMock()
        business.name = "Test Gym"
        business.business_type = "gym"
        business.address = None
        business.avg_rating = 4.0
        business.total_reviews = 20

        prompt = build_system_prompt(business)
        assert "pin_widget" in prompt
        # Step 1: data tool first
        assert "data tool" in prompt.lower() or "appropriate data tool" in prompt.lower()
        # Step 2: pass data unchanged
        assert "unchanged" in prompt.lower()
        # Step 3: report what was added
        assert (
            "tell the user what was added" in prompt.lower() or "what was added" in prompt.lower()
        )

    def test_prompt_forbids_invented_widget_types(self):
        """Prompt must instruct agent to use only known widget_type values."""
        business = MagicMock()
        business.name = "Test Hotel"
        business.business_type = "hotel"
        business.address = None
        business.avg_rating = 3.8
        business.total_reviews = 10

        prompt = build_system_prompt(business)
        assert "do not invent" in prompt.lower() or "only use widget_type" in prompt.lower()

    def test_prompt_includes_tool_widget_type_mapping(self):
        """Every tool→widget_type mapping entry must appear in the system prompt."""
        from app.agent.tools import TOOL_WIDGET_TYPES

        business = MagicMock()
        business.name = "Test Clinic"
        business.business_type = "clinic"
        business.address = None
        business.avg_rating = 4.5
        business.total_reviews = 30

        prompt = build_system_prompt(business)
        # Only check widget types that data tools actually map to (pin_widget maps to None)
        mapped_types = {wt for wt in TOOL_WIDGET_TYPES.values() if wt is not None}
        for wt in mapped_types:
            assert wt in prompt, f"widget_type '{wt}' missing from system prompt mapping"
