"""Unit tests for agent tool functions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from app.agent.system_prompt import build_system_prompt
from app.agent.tools import (
    DATA_TOOL_NAMES,
    TOOL_COMPATIBLE_WIDGETS,
    TOOL_DEFINITIONS,
    TOOL_WIDGET_TYPES,
    WIDGET_TYPES,
    _clear_dashboard,
    _coerce_pin_widget_arguments,
    _create_custom_chart_data,
    _duplicate_widget,
    _get_action_plan,
    _get_business_health,
    _get_financial_flow,
    _get_local_presence_summary,
    _get_operations_summary,
    _get_opportunities,
    _get_rating_distribution,
    _get_review_change_summary,
    _get_review_insights,
    _get_sales_summary,
    _get_signal_timeline,
    _get_social_signal_summary,
    _get_top_issues,
    _pin_widget,
    _remove_widget,
    execute_tool,
    format_compatibility_for_prompt,
    pin_rejects_money_flow_bar_masquerade,
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


def _make_chain_db(reviews: list) -> MagicMock:
    """Build a mock Session whose Review queries support filter/order_by/all chains."""
    db = MagicMock()
    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.all.return_value = reviews

    def _query(model):
        if model.__name__ == "Review":
            return query
        fallback = MagicMock()
        fallback.filter.return_value = fallback
        fallback.first.return_value = None
        fallback.all.return_value = []
        return fallback

    db.query.side_effect = _query
    return db


def _make_sequence_db(review_sets: list[list]) -> MagicMock:
    db = MagicMock()
    queries = []
    for reviews in review_sets:
        query = MagicMock()
        query.filter.return_value = query
        query.order_by.return_value = query
        query.all.return_value = reviews
        queries.append(query)
    iterator = iter(queries)

    def _query(model):
        if model.__name__ == "Review":
            return next(iterator)
        fallback = MagicMock()
        fallback.filter.return_value = fallback
        fallback.first.return_value = None
        fallback.all.return_value = []
        return fallback

    db.query.side_effect = _query
    return db


def _make_health_db(reviews: list, analysis: MagicMock | None = None) -> MagicMock:
    db = MagicMock()
    review_query = MagicMock()
    review_query.filter.return_value = review_query
    review_query.order_by.return_value = review_query
    review_query.all.return_value = reviews

    analysis_query = MagicMock()
    analysis_query.filter.return_value = analysis_query
    analysis_query.first.return_value = analysis

    def _query(model):
        if model.__name__ == "Review":
            return review_query
        if model.__name__ == "Analysis":
            return analysis_query
        fallback = MagicMock()
        fallback.filter.return_value = fallback
        fallback.first.return_value = None
        fallback.all.return_value = []
        return fallback

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

    def test_missing_data_key_becomes_empty_dict(self):
        coerced = _coerce_pin_widget_arguments({"widget_type": "bar_chart", "title": "T"})
        assert coerced["data"] == {}

    def test_null_data_becomes_empty_dict(self):
        coerced = _coerce_pin_widget_arguments(
            {"widget_type": "bar_chart", "title": "T", "data": None}
        )
        assert coerced["data"] == {}

    def test_source_tool_is_stripped_before_reaching_pin_widget(self):
        # source_tool is an executor-only field; _coerce_pin_widget_arguments must
        # not surface it to _pin_widget (which would error on an unexpected key).
        coerced = _coerce_pin_widget_arguments(
            {
                "widget_type": "bar_chart",
                "title": "Rating Dist",
                "source_tool": "get_rating_distribution",
                "data": {"bars": [{"label": "5★", "value": 3}]},
            }
        )
        assert "source_tool" not in coerced
        assert coerced["data"] == {"bars": [{"label": "5★", "value": 3}]}


class TestDataToolNames:
    def test_all_data_tool_names_are_present(self):
        # Every key in TOOL_WIDGET_TYPES that is not pin_widget should appear in
        # DATA_TOOL_NAMES so the source_tool enum stays in sync.
        from app.agent.tools import TOOL_WIDGET_TYPES

        missing = [
            name
            for name, widget_type in TOOL_WIDGET_TYPES.items()
            if widget_type is not None and name not in DATA_TOOL_NAMES
        ]
        assert missing == [], f"Tools missing from DATA_TOOL_NAMES: {missing}"

    def test_pin_widget_not_in_data_tool_names(self):
        assert "pin_widget" not in DATA_TOOL_NAMES
        assert "remove_widget" not in DATA_TOOL_NAMES
        assert "duplicate_widget" not in DATA_TOOL_NAMES

    def test_create_custom_chart_data_is_a_data_tool_name(self):
        # create_custom_chart_data builds chart-ready payloads itself, so the
        # model must be allowed to use it as source_tool when pinning.
        assert "create_custom_chart_data" in DATA_TOOL_NAMES


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
        assert result["slices"][4]["value"] == 2
        assert result["slices"][4]["percent"] == 66.7


class TestReviewInsightSynthesis:
    def test_worst_reviews_this_month_uses_mixed_ratings_severity_and_examples(self):
        biz_id = uuid.uuid4()
        reviews = [
            _make_review(
                1, "Rude staff ignored us for twenty minutes", days_ago=2, business_id=biz_id
            ),
            _make_review(
                3, "The wait was slow but the beer was good", days_ago=4, business_id=biz_id
            ),
            _make_review(4, "Loud music made it hard to talk", days_ago=5, business_id=biz_id),
        ]
        result = _get_review_insights(
            _make_chain_db(reviews),
            biz_id,
            focus="negative",
            period="this_month",
        )

        assert result["review_count"] == 3
        assert result["issues"]
        assert any(issue["avg_rating"] > 1 for issue in result["issues"])
        assert any(issue["representative_quote"] for issue in result["issues"])
        assert "recommended_focus" in result

    def test_good_parts_this_week_identifies_positive_themes(self):
        biz_id = uuid.uuid4()
        reviews = [
            _make_review(
                5, "Friendly staff and excellent beer selection", days_ago=1, business_id=biz_id
            ),
            _make_review(4, "Cozy atmosphere with great music", days_ago=2, business_id=biz_id),
            _make_review(3, "Good beer but service was slow", days_ago=3, business_id=biz_id),
        ]
        result = _get_review_insights(
            _make_chain_db(reviews),
            biz_id,
            focus="positive",
            period="this_week",
        )

        assert result["summary"]
        assert result["top_praise"]
        labels = {item["label"] for item in result["top_praise"]}
        assert {"friendly service", "food or drink quality"} & labels
        assert result["examples"]

    def test_changed_compared_to_last_month_compares_two_windows(self):
        biz_id = uuid.uuid4()
        current = [
            _make_review(5, "Friendly staff and fresh beer", days_ago=2, business_id=biz_id),
            _make_review(4, "Great atmosphere", days_ago=3, business_id=biz_id),
            _make_review(5, "Fast service this month", days_ago=4, business_id=biz_id),
        ]
        previous = [
            _make_review(2, "Slow service last month", days_ago=35, business_id=biz_id),
            _make_review(3, "Overpriced drinks last month", days_ago=40, business_id=biz_id),
            _make_review(3, "Crowded bar last month", days_ago=45, business_id=biz_id),
        ]
        result = _get_review_change_summary(
            _make_sequence_db([current, previous]),
            biz_id,
            current_period="this_month",
            previous_period="last_month",
        )

        assert result["current"]["count"] == 3
        assert result["previous"]["count"] == 3
        assert result["rating_delta"] > 0
        assert "current_themes" in result
        assert "previous_themes" in result
        assert result["recommended_focus"]

    def test_sparse_data_case_returns_clear_limitation(self):
        biz_id = uuid.uuid4()
        reviews = [_make_review(4, "Nice place", days_ago=1, business_id=biz_id)]
        result = _get_review_insights(
            _make_chain_db(reviews),
            biz_id,
            focus="balanced",
            period="this_week",
        )

        assert result["limitation"]
        assert "Only 1 review" in result["limitation"]


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

        result = _pin_widget(db, biz_id, user_id, widget_type="line_chart", title="Chart", data={})
        assert result["pinned"] is True
        assert "widget_id" in result
        assert "widget" in result
        assert result["widget"]["widget_type"] == "line_chart"
        assert result["widget"]["title"] == "Chart"
        assert result["widget"]["data"] == {}
        assert "id" in result["widget"]
        assert "position" in result["widget"]

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


class TestRemoveWidget:
    def test_removes_existing_widget(self):
        biz_id = uuid.uuid4()
        user_id = uuid.uuid4()
        widget_id = uuid.uuid4()
        widget = MagicMock()

        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = widget
        db.query.return_value = q

        result = _remove_widget(db, biz_id, user_id, widget_id=str(widget_id))

        assert result == {"removed": True, "widget_id": str(widget_id)}
        db.delete.assert_called_once_with(widget)
        db.commit.assert_called_once()

    def test_missing_widget_returns_error(self):
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = None
        db.query.return_value = q
        widget_id = uuid.uuid4()

        result = _remove_widget(db, uuid.uuid4(), uuid.uuid4(), widget_id=str(widget_id))

        assert result["removed"] is False
        assert result["widget_id"] == str(widget_id)
        assert "not found" in result["error"].lower()
        db.delete.assert_not_called()
        db.commit.assert_not_called()

    def test_invalid_uuid_returns_error_without_query(self):
        db = MagicMock()

        result = _remove_widget(db, uuid.uuid4(), uuid.uuid4(), widget_id="not-a-uuid")

        assert result["removed"] is False
        assert "invalid" in result["error"].lower()
        db.query.assert_not_called()


class TestClearDashboard:
    def test_clears_all_widgets_for_business_and_user(self):
        widget_1 = MagicMock()
        widget_1.id = uuid.uuid4()
        widget_2 = MagicMock()
        widget_2.id = uuid.uuid4()

        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.all.return_value = [widget_1, widget_2]
        db.query.return_value = q

        result = _clear_dashboard(db, uuid.uuid4(), uuid.uuid4())

        assert result == {
            "cleared": True,
            "removed_count": 2,
            "widget_ids": [str(widget_1.id), str(widget_2.id)],
        }
        db.delete.assert_any_call(widget_1)
        db.delete.assert_any_call(widget_2)
        assert db.delete.call_count == 2
        db.commit.assert_called_once()

    def test_execute_tool_routes_clear_dashboard(self):
        widget = MagicMock()
        widget.id = uuid.uuid4()
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.all.return_value = [widget]
        db.query.return_value = q

        result = execute_tool("clear_dashboard", {}, db, uuid.uuid4(), uuid.uuid4())

        assert result["cleared"] is True
        assert result["removed_count"] == 1
        db.delete.assert_called_once_with(widget)


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

    def test_prompt_directs_clear_then_improvement_dashboard_fill(self):
        business = MagicMock()
        business.name = "Test Bar"
        business.business_type = "bar"
        business.address = None
        business.avg_rating = None
        business.total_reviews = 10

        prompt = build_system_prompt(business)

        assert "clear_dashboard once" in prompt
        assert "IMPROVEMENT DASHBOARD FILL" in prompt
        assert "with at least 6 widgets" in prompt

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
        # Step 2: set source_tool to the data tool name
        assert "source_tool" in prompt
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

    def test_prompt_routes_open_questions_to_synthesis_tools(self):
        business = MagicMock()
        business.name = "Test Bar"
        business.business_type = "bar"
        business.address = None
        business.avg_rating = 4.1
        business.total_reviews = 25

        prompt = build_system_prompt(business)
        assert "get_review_insights" in prompt
        assert "get_review_change_summary" in prompt
        assert "query_reviews only when the user explicitly asks for raw reviews" in prompt

    def test_prompt_routes_rating_distribution_to_pie_or_donut(self):
        business = MagicMock()
        business.name = "Test Bar"
        business.business_type = "bar"
        business.address = None
        business.avg_rating = 4.1
        business.total_reviews = 25

        prompt = build_system_prompt(business)
        assert "pie_chart or donut_chart" in prompt
        assert "Rating distribution/share" in prompt

    def test_tool_widget_type_defaults_choose_new_chart_types(self):
        from app.agent.tools import TOOL_WIDGET_TYPES

        assert TOOL_WIDGET_TYPES["get_rating_distribution"] == "donut_chart"
        assert TOOL_WIDGET_TYPES["get_top_issues"] == "horizontal_bar_chart"
        assert TOOL_WIDGET_TYPES["get_review_series"] == "line_chart"
        assert TOOL_WIDGET_TYPES["get_review_change_summary"] == "comparison_chart"


# ---------------------------------------------------------------------------
# Compatibility table is the single source of truth and is auto-rendered into
# the system prompt + per-tool descriptions.
# ---------------------------------------------------------------------------


class TestCompatibilityExposure:
    def test_format_compatibility_for_prompt_lists_every_source_tool(self):
        rendered = format_compatibility_for_prompt()
        for source_tool in TOOL_COMPATIBLE_WIDGETS:
            assert source_tool in rendered

    def test_compatibility_table_is_in_system_prompt(self):
        business = MagicMock()
        business.name = "Cafe"
        business.business_type = "cafe"
        business.address = None
        business.avg_rating = 4.0
        business.total_reviews = 10

        prompt = build_system_prompt(business)
        assert "COMPATIBILITY TABLE" in prompt
        # Every source_tool->widget_type pair should be discoverable in the
        # rendered table; spot-check a couple known-tricky ones.
        assert "get_top_issues" in prompt
        assert "horizontal_bar_chart" in prompt
        assert "create_custom_chart_data" in prompt

    def test_data_tool_descriptions_include_allowed_widget_types(self):
        # The post-processing block enriches each data-tool description with
        # its compatible widget_types so the model sees the rule at tool-pick
        # time, not just in the system prompt.
        for tool_def in TOOL_DEFINITIONS:
            fn = tool_def.get("function") or {}
            name = fn.get("name")
            if name in TOOL_COMPATIBLE_WIDGETS:
                description = fn.get("description") or ""
                assert "Compatible widget_types" in description, (
                    f"Tool {name!r} description missing compatibility hint"
                )


# ---------------------------------------------------------------------------
# money_flow / get_financial_flow routing
# ---------------------------------------------------------------------------


class TestMoneyFlowRouting:
    def _business(self):
        b = MagicMock()
        b.name = "Test Cafe"
        b.business_type = "cafe"
        b.address = None
        b.avg_rating = 4.2
        b.total_reviews = 20
        return b

    def test_money_flow_widget_type_registered(self):
        assert "money_flow" in WIDGET_TYPES

    def test_get_financial_flow_in_data_tool_names(self):
        assert "get_financial_flow" in DATA_TOOL_NAMES

    def test_get_financial_flow_compatible_with_money_flow(self):
        assert "money_flow" in TOOL_COMPATIBLE_WIDGETS["get_financial_flow"]

    def test_get_financial_flow_not_in_demo_signal_gate(self):
        from app.agent.tools import _DEMO_SIGNAL_TOOL_NAMES

        assert "get_financial_flow" not in _DEMO_SIGNAL_TOOL_NAMES, (
            "get_financial_flow must not be gated by demo signals — it is BI-always-on"
        )

    def test_get_financial_flow_in_bi_tool_names(self):
        from app.agent.tools import _BUSINESS_INSIGHT_TOOL_NAMES

        assert "get_financial_flow" in _BUSINESS_INSIGHT_TOOL_NAMES

    def test_system_prompt_has_money_flow_override(self):
        prompt = build_system_prompt(self._business())
        assert "get_financial_flow" in prompt
        assert "money_flow" in prompt
        assert "MONEY FLOW" in prompt

    def test_system_prompt_forbids_bar_chart_for_money_flow(self):
        prompt = build_system_prompt(self._business())
        assert "NOT bar_chart" in prompt or "not bar_chart" in prompt.lower()

    def test_system_prompt_comprehensive_fill_includes_money_flow_and_action_plan(self):
        prompt = build_system_prompt(self._business())
        assert "5. Money flow" in prompt and "get_financial_flow" in prompt
        assert "6. Action plan" in prompt and "get_action_plan" in prompt
        assert "7. Trend" in prompt

    def test_get_financial_flow_returns_required_fields(self):
        result = _get_financial_flow(uuid.uuid4())
        assert "revenue" in result
        assert "cogs" in result
        assert "gross_profit" in result
        assert "operating_expenses" in result
        assert "net_profit" in result
        assert result["revenue"] > 0
        assert result["gross_profit"] == result["revenue"] - result["cogs"]
        assert result["net_profit"] == result["gross_profit"] - result["operating_expenses"]

    def test_get_financial_flow_active_when_bi_enabled(self):
        from app.agent.tools import get_active_tool_definitions

        active_names = {t["function"]["name"] for t in get_active_tool_definitions()}
        assert "get_financial_flow" in active_names, (
            "get_financial_flow must be active when BUSINESS_INSIGHT_ENABLED=True"
        )


# ---------------------------------------------------------------------------
# _get_business_health
# ---------------------------------------------------------------------------


class TestBusinessHealth:
    def test_health_score_uses_reviews_analysis_and_provenance(self):
        reviews = [
            _make_review(5, "Great beer", days_ago=2),
            _make_review(4, "Good service", days_ago=5),
            _make_review(2, "Slow wait", days_ago=8),
            _make_review(5, "Nice staff", days_ago=35),
        ]
        analysis = MagicMock()
        analysis.top_complaints = [{"label": "slow wait", "count": 2}]
        analysis.risk_areas = ["Queue pressure"]
        analysis.top_praise = [{"label": "beer", "count": 3}]
        analysis.action_items = ["Add one more server during rush."]
        analysis.recommended_focus = "Fix rush-hour wait time."
        db = _make_health_db(reviews, analysis)

        result = _get_business_health(db, uuid.uuid4())

        assert result["label"] == "Business Health"
        assert 0 <= result["score"] <= 100
        assert result["source"] == "reviews_and_analysis"
        assert result["is_demo"] is False
        assert result["confidence"] == "low"  # fewer than 10 reviews
        assert {s["id"] for s in result["sub_scores"]} == {
            "reputation",
            "customer_experience",
            "operations_risk",
            "momentum",
            "competitive_position",
            "local_presence",
        }
        assert result["drivers"]
        assert result["risks"]
        assert result["opportunities"] == ["Fix rush-hour wait time."]
        assert "connected signals" in result["limitations"][-1]

    def test_health_score_handles_empty_data_honestly(self):
        result = _get_business_health(_make_health_db([]), uuid.uuid4())

        assert result["score"] < 50
        assert result["confidence"] == "low"
        assert result["freshness"] is None
        assert any("No reviews are loaded" in item for item in result["limitations"])
        assert any("Run analysis" in item for item in result["limitations"])

    def test_health_tool_registry_is_pinnable(self):
        assert "get_business_health" in DATA_TOOL_NAMES
        assert TOOL_WIDGET_TYPES["get_business_health"] == "health_score"
        assert "health_score" in TOOL_COMPATIBLE_WIDGETS["get_business_health"]
        rendered = format_compatibility_for_prompt()
        assert "get_business_health" in rendered
        assert "health_score" in rendered


# ---------------------------------------------------------------------------
# _get_signal_timeline
# ---------------------------------------------------------------------------


class TestSignalTimeline:
    def test_signal_timeline_detects_rating_and_theme_shift(self):
        current = [
            _make_review(2, "Slow wait and cold beer", days_ago=2),
            _make_review(2, "Very slow service", days_ago=4),
            _make_review(4, "Friendly staff", days_ago=6),
            _make_review(3, "Crowded but okay", days_ago=8),
        ]
        previous = [
            _make_review(5, "Great beer", days_ago=35),
            _make_review(5, "Excellent atmosphere", days_ago=38),
            _make_review(4, "Good value", days_ago=40),
        ]

        result = _get_signal_timeline(
            _make_sequence_db([current, previous]), uuid.uuid4(), days=30
        )

        assert result["period"] == "past 30 days"
        assert result["source"] == "reviews"
        assert result["is_demo"] is False
        assert result["events"]
        event_ids = {event["id"] for event in result["events"]}
        assert "rating-change" in event_ids
        assert "top-issue-shift" in event_ids
        assert "low-rating-evidence" in event_ids
        assert result["confidence"] in {"low", "medium"}

    def test_signal_timeline_handles_empty_data(self):
        result = _get_signal_timeline(_make_sequence_db([[], []]), uuid.uuid4(), days=30)

        assert result["events"][0]["id"] == "stable-window"
        assert result["confidence"] == "low"
        assert any("No dated reviews" in item for item in result["limitations"])

    def test_signal_timeline_tool_registry_is_pinnable(self):
        assert "get_signal_timeline" in DATA_TOOL_NAMES
        assert TOOL_WIDGET_TYPES["get_signal_timeline"] == "signal_timeline"
        assert "signal_timeline" in TOOL_COMPATIBLE_WIDGETS["get_signal_timeline"]
        rendered = format_compatibility_for_prompt()
        assert "get_signal_timeline" in rendered
        assert "signal_timeline" in rendered


# ---------------------------------------------------------------------------
# Demo multi-signal summaries
# ---------------------------------------------------------------------------


class TestDemoSignalSummaries:
    def test_demo_signal_summaries_are_deterministic_and_marked_demo(self):
        business_id = uuid.UUID("00000000-0000-0000-0000-00000000002a")

        sales_1 = _get_sales_summary(business_id)
        sales_2 = _get_sales_summary(business_id)
        operations = _get_operations_summary(business_id)
        local = _get_local_presence_summary(business_id)
        social = _get_social_signal_summary(business_id)

        assert sales_1["metrics"] == sales_2["metrics"]
        for result in (sales_1, operations, local, social):
            assert result["is_demo"] is True
            assert result["source"].startswith("demo_")
            assert result["confidence"] == "demo"
            assert result["metrics"]
            assert result["items"]
            assert result["recommendation"]
            assert "Demo/offline signal" in result["limitations"][0]

    def test_demo_signal_disabled_payload_is_honest(self, monkeypatch):
        import app.config as config_mod

        monkeypatch.setattr(config_mod.settings, "DEMO_SIGNALS_ENABLED", False)

        result = _get_sales_summary(uuid.uuid4())

        assert result["is_demo"] is False
        assert result["source"] == "none"
        assert result["confidence"] == "none"
        assert result["metrics"] == []
        assert "DEMO_SIGNALS_ENABLED=true" in result["limitations"][0]

    def test_demo_signal_tools_are_pinnable(self):
        expected = {
            "get_sales_summary": "sales_summary",
            "get_operations_summary": "operations_risk",
            "get_local_presence_summary": "local_presence_card",
            "get_social_signal_summary": "social_signal",
        }
        for tool_name, widget_type in expected.items():
            assert tool_name in DATA_TOOL_NAMES
            assert TOOL_WIDGET_TYPES[tool_name] == widget_type
            assert widget_type in TOOL_COMPATIBLE_WIDGETS[tool_name]


# ---------------------------------------------------------------------------
# Opportunity and action-plan synthesis
# ---------------------------------------------------------------------------


class TestOpportunityActionPlan:
    def test_opportunities_mix_review_analysis_and_demo_signals(self):
        reviews = [
            _make_review(2, "Slow wait and crowded bar", days_ago=2),
            _make_review(5, "Great beer list", days_ago=4),
        ]
        analysis = MagicMock()
        analysis.top_complaints = [{"label": "slow wait", "count": 2}]
        analysis.risk_areas = ["Peak shift pressure"]
        analysis.top_praise = [{"label": "beer list", "count": 3}]
        analysis.action_items = ["Add one more server during rush."]
        analysis.recommended_focus = "Fix rush-hour wait time."

        result = _get_opportunities(_make_health_db(reviews, analysis), uuid.uuid4())

        assert result["opportunities"]
        assert result["source"] == "reviews_analysis_demo_signals"
        assert result["is_demo"] is True
        assert result["confidence"] == "low"
        titles = {item["title"] for item in result["opportunities"]}
        assert "Fix slow wait" in titles
        assert "Promote beer list" in titles
        assert any(item["source"].startswith("demo_") for item in result["opportunities"])
        assert any("demo" in item.lower() for item in result["limitations"])

    def test_action_plan_converts_opportunities_to_owner_metric_actions(self):
        reviews = [_make_review(2, "Slow wait", days_ago=1)]
        analysis = MagicMock()
        analysis.top_complaints = [{"label": "slow wait", "count": 1}]
        analysis.risk_areas = ["Peak shift pressure"]
        analysis.top_praise = []
        analysis.action_items = ["Add one more server during rush."]
        analysis.recommended_focus = "Fix rush-hour wait time."

        result = _get_action_plan(_make_health_db(reviews, analysis), uuid.uuid4())

        assert result["actions"]
        first = result["actions"][0]
        assert first["rank"] == 1
        assert first["issue_or_opportunity"] == "Fix slow wait"
        assert first["suggested_owner"] == "General manager"
        assert first["metric_to_watch"]
        assert result["weekly_priorities"]

    def test_opportunity_and_action_tools_are_pinnable(self):
        expected = {
            "get_opportunities": "opportunity_list",
            "get_action_plan": "action_plan",
        }
        for tool_name, widget_type in expected.items():
            assert tool_name in DATA_TOOL_NAMES
            assert TOOL_WIDGET_TYPES[tool_name] == widget_type
            assert widget_type in TOOL_COMPATIBLE_WIDGETS[tool_name]
        rendered = format_compatibility_for_prompt()
        assert "get_action_plan" in rendered
        assert "action_plan" in rendered


# ---------------------------------------------------------------------------
# _create_custom_chart_data validation
# ---------------------------------------------------------------------------


class TestCreateCustomChartData:
    def test_valid_pie_distribution_returns_chart_ready_payload(self):
        result = _create_custom_chart_data(
            {
                "widget_type": "pie_chart",
                "labels": ["likely female", "likely male", "unknown"],
                "values": [3.0, 2.0, 5.0],
                "source_summary": ("Derived from query_reviews + name-based gender inference."),
                "uncertainty_note": (
                    "Names were used to infer likely gender; this may be inaccurate."
                ),
            }
        )
        assert "error" not in result
        assert result["widget_type"] == "pie_chart"
        assert result["labels"] == ["likely female", "likely male", "unknown"]
        assert result["values"] == [3.0, 2.0, 5.0]
        assert len(result["bars"]) == 3
        assert len(result["slices"]) == 3
        # percent should sum (within rounding) to ~100 when total > 0
        assert sum(s["percent"] for s in result["slices"]) > 99
        assert result["uncertainty_note"]

    def test_inferred_segmentation_without_uncertainty_is_rejected(self):
        # The model promised "inferred name-gender" segmentation; missing
        # uncertainty_note must be rejected so the chart cannot be read as fact.
        result = _create_custom_chart_data(
            {
                "widget_type": "pie_chart",
                "labels": ["likely female", "likely male"],
                "values": [3.0, 2.0],
                "source_summary": "Inferred name-gender from review author names.",
            }
        )
        assert "error" in result
        assert "uncertainty_note" in result["error"]

    def test_label_value_length_mismatch_is_rejected(self):
        result = _create_custom_chart_data(
            {
                "widget_type": "bar_chart",
                "labels": ["a", "b", "c"],
                "values": [1, 2],
                "source_summary": "Manual roll-up.",
            }
        )
        assert "error" in result
        assert "same length" in result["error"]

    def test_empty_labels_or_values_are_rejected(self):
        result = _create_custom_chart_data(
            {
                "widget_type": "bar_chart",
                "labels": [],
                "values": [],
                "source_summary": "Manual roll-up.",
            }
        )
        assert "error" in result

    def test_negative_or_non_finite_values_are_rejected(self):
        nan_result = _create_custom_chart_data(
            {
                "widget_type": "bar_chart",
                "labels": ["a"],
                "values": [float("nan")],
                "source_summary": "Manual roll-up.",
            }
        )
        assert "error" in nan_result
        neg_result = _create_custom_chart_data(
            {
                "widget_type": "bar_chart",
                "labels": ["a"],
                "values": [-1],
                "source_summary": "Manual roll-up.",
            }
        )
        assert "error" in neg_result

    def test_pie_chart_needs_at_least_two_positive_slices(self):
        result = _create_custom_chart_data(
            {
                "widget_type": "donut_chart",
                "labels": ["only", "empty"],
                "values": [3, 0],
                "source_summary": "Manual roll-up.",
            }
        )
        assert "error" in result
        assert "at least 2" in result["error"]

    def test_insight_list_requires_items_with_themes(self):
        good = _create_custom_chart_data(
            {
                "widget_type": "insight_list",
                "items": [
                    {"theme": "slow service", "count": 4},
                    {"label": "noise", "count": 2},
                ],
                "source_summary": "Composed from get_top_issues + query_reviews keyword filter.",
            }
        )
        assert "error" not in good
        assert good["items"][0]["theme"] == "slow service"
        assert good["items"][1]["theme"] == "noise"

        bad = _create_custom_chart_data(
            {
                "widget_type": "insight_list",
                "items": [{"count": 5}],  # no theme/label
                "source_summary": "Composed.",
            }
        )
        assert "error" in bad

    def test_unsupported_widget_type_is_rejected(self):
        result = _create_custom_chart_data(
            {
                "widget_type": "line_chart",  # not allowed by this tool
                "labels": ["a", "b"],
                "values": [1, 2],
                "source_summary": "Manual roll-up.",
            }
        )
        assert "error" in result


class TestMoneyFlowIntercept:
    def test_profit_bridge_labels_return_redirect_error(self):
        result = _create_custom_chart_data(
            {
                "widget_type": "horizontal_bar_chart",
                "labels": ["Revenue", "COGS", "Gross Profit", "Operating Expenses", "Net Profit"],
                "values": [100.0, 40.0, 60.0, 25.0, 35.0],
                "source_summary": "Composed from hypothetical P&L segments.",
            }
        )
        assert result.get("error") == "money_flow_redirect"
        assert result.get("redirect_tool") == "get_financial_flow"
        assert result.get("redirect_widget_type") == "money_flow"

    def test_only_two_money_keywords_does_not_redirect(self):
        result = _create_custom_chart_data(
            {
                "widget_type": "horizontal_bar_chart",
                "labels": ["Revenue", "COGS", "Other"],
                "values": [10.0, 4.0, 1.0],
                "source_summary": "Manual roll-up.",
            }
        )
        assert "error" not in result
        assert result["widget_type"] == "horizontal_bar_chart"

    def test_pin_rejects_masquerade_from_cached_payload(self):
        payload = {
            "widget_type": "horizontal_bar_chart",
            "labels": ["revenue", "cogs", "gross profit", "net profit"],
            "values": [1, 1, 1, 1],
            "bars": [{"label": "revenue", "value": 1}, {"label": "cogs", "value": 1}],
            "source_summary": "x",
        }
        block = pin_rejects_money_flow_bar_masquerade(
            "create_custom_chart_data", "horizontal_bar_chart", payload
        )
        assert block is not None
        assert block["pinned"] is False
        assert "money_flow" in block["error"].lower() or "profit" in block["error"].lower()

    def test_pin_rejects_skips_non_custom_source(self):
        payload = {
            "labels": ["Revenue", "COGS", "Gross Profit", "Operating Expenses", "Net Profit"],
            "values": [1, 1, 1, 1, 1],
        }
        assert (
            pin_rejects_money_flow_bar_masquerade(
                "get_top_issues", "horizontal_bar_chart", payload
            )
            is None
        )


# ---------------------------------------------------------------------------
# _duplicate_widget
# ---------------------------------------------------------------------------


class TestDuplicateWidget:
    def test_duplicates_existing_widget_with_deep_copied_data(self):
        from app.models.workspace_widget import WorkspaceWidget

        biz_id = uuid.uuid4()
        user_id = uuid.uuid4()
        widget_id = uuid.uuid4()
        source_widget = MagicMock(spec=WorkspaceWidget)
        source_widget.id = widget_id
        source_widget.widget_type = "bar_chart"
        source_widget.title = "Top issues"
        source_widget.data = {"bars": [{"label": "slow service", "value": 4}]}
        source_widget.position = 2

        db = MagicMock()
        # Two separate query() calls: one for the source row, one for count.
        first_query = MagicMock()
        first_query.filter.return_value = first_query
        first_query.first.return_value = source_widget
        count_query = MagicMock()
        count_query.filter.return_value = count_query
        count_query.count.return_value = 3

        db.query.side_effect = [first_query, count_query]
        db.refresh.side_effect = lambda w: None

        result = _duplicate_widget(db, biz_id, user_id, widget_id=str(widget_id))
        assert result["duplicated"] is True
        assert result["source_widget_id"] == str(widget_id)
        assert result["widget_id"] != str(widget_id)
        assert result["widget"]["widget_type"] == "bar_chart"
        assert result["widget"]["title"] == "Top issues (copy)"
        # Data is deep-copied — mutating the original after the fact must not
        # affect the duplicate's payload.
        source_widget.data["bars"][0]["value"] = 999
        assert result["widget"]["data"]["bars"][0]["value"] == 4
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_missing_source_widget_returns_error(self):
        biz_id = uuid.uuid4()
        user_id = uuid.uuid4()
        widget_id = uuid.uuid4()

        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = None
        db.query.return_value = q

        result = _duplicate_widget(db, biz_id, user_id, widget_id=str(widget_id))
        assert result["duplicated"] is False
        assert "not found" in result["error"].lower()
        db.add.assert_not_called()
        db.commit.assert_not_called()

    def test_invalid_uuid_returns_error_without_query(self):
        db = MagicMock()
        result = _duplicate_widget(db, uuid.uuid4(), uuid.uuid4(), widget_id="not-a-uuid")
        assert result["duplicated"] is False
        assert "invalid" in result["error"].lower()
        db.query.assert_not_called()

    def test_duplicate_of_already_copied_title_does_not_double_suffix(self):
        from app.models.workspace_widget import WorkspaceWidget

        biz_id = uuid.uuid4()
        user_id = uuid.uuid4()
        widget_id = uuid.uuid4()
        source_widget = MagicMock(spec=WorkspaceWidget)
        source_widget.id = widget_id
        source_widget.widget_type = "bar_chart"
        source_widget.title = "Top issues (copy)"
        source_widget.data = {"bars": []}
        source_widget.position = 0

        db = MagicMock()
        first_query = MagicMock()
        first_query.filter.return_value = first_query
        first_query.first.return_value = source_widget
        count_query = MagicMock()
        count_query.filter.return_value = count_query
        count_query.count.return_value = 1
        db.query.side_effect = [first_query, count_query]
        db.refresh.side_effect = lambda w: None

        result = _duplicate_widget(db, biz_id, user_id, widget_id=str(widget_id))
        assert result["duplicated"] is True
        assert result["widget"]["title"] == "Top issues (copy)"
