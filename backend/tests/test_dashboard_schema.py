"""Tests for dashboard and analysis schema validation."""

from app.schemas.analysis import AnalysisRead, InsightItem
from app.schemas.dashboard import DashboardResponse


class TestInsightItem:
    def test_valid_item(self):
        item = InsightItem(label="Friendly staff", count=5)
        assert item.label == "Friendly staff"
        assert item.count == 5


class TestDashboardResponse:
    def test_full_dashboard(self):
        data = DashboardResponse(
            business_name="Test Cafe",
            business_type="cafe",
            address="123 Main St",
            avg_rating=4.2,
            total_reviews=15,
            top_complaints=[InsightItem(label="Slow", count=3)],
            top_praise=[InsightItem(label="Great coffee", count=5)],
            ai_summary="Overall positive.",
            action_items=["Hire more baristas"],
            risk_areas=["Peak hour delays"],
            recommended_focus="Speed up service during morning rush.",
            analysis_created_at=None,
            last_updated_at=None,
        )
        assert data.business_name == "Test Cafe"
        assert data.business_type == "cafe"
        assert data.avg_rating == 4.2
        assert len(data.top_complaints) == 1
        assert len(data.action_items) == 1
        assert data.recommended_focus is not None

    def test_dashboard_with_no_analysis(self):
        data = DashboardResponse(
            business_name="New Place",
            business_type="other",
            address=None,
            avg_rating=None,
            total_reviews=0,
            top_complaints=[],
            top_praise=[],
            ai_summary=None,
            action_items=[],
            risk_areas=[],
            recommended_focus=None,
            analysis_created_at=None,
            last_updated_at=None,
        )
        assert data.ai_summary is None
        assert data.action_items == []
        assert data.recommended_focus is None

    def test_dashboard_serialization(self):
        data = DashboardResponse(
            business_name="Test",
            business_type="gym",
            address=None,
            avg_rating=3.5,
            total_reviews=10,
            top_complaints=[],
            top_praise=[],
            ai_summary="Good gym.",
            action_items=["Buy new equipment"],
            risk_areas=[],
            recommended_focus="Equipment upgrades.",
            analysis_created_at=None,
            last_updated_at=None,
        )
        d = data.model_dump()
        assert isinstance(d, dict)
        assert d["business_type"] == "gym"
        assert d["action_items"] == ["Buy new equipment"]


class TestAnalysisRead:
    def test_includes_new_v11_fields(self):
        """Ensure the schema accepts the V1.1 analysis fields."""
        import uuid
        from datetime import datetime, timezone

        data = AnalysisRead(
            id=uuid.uuid4(),
            business_id=uuid.uuid4(),
            summary="Test summary",
            top_complaints=[],
            top_praise=[],
            action_items=["Do this", "Do that"],
            risk_areas=["Watch out for this"],
            recommended_focus="Focus here.",
            created_at=datetime.now(timezone.utc),
        )
        assert len(data.action_items) == 2
        assert data.recommended_focus == "Focus here."
