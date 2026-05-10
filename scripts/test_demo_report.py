from datetime import UTC, datetime, timedelta

from demo_report import ARC_EPOCH, ARC_PERIOD, report_end_ts, resolve_cycle_start


def ts(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> float:
    return datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp()


def test_auto_cycle_reports_completed_cycle_during_boundary_grace() -> None:
    now_ts = ts(2026, 5, 8, 4, 55)

    assert resolve_cycle_start(now_ts, mode="auto", boundary_grace_hours=12) == ARC_EPOCH


def test_auto_cycle_reports_current_cycle_after_boundary_grace() -> None:
    now_ts = ts(2026, 5, 8, 13, 0)

    assert resolve_cycle_start(now_ts, mode="auto", boundary_grace_hours=12) == (
        ARC_EPOCH + ARC_PERIOD
    )


def test_completed_cycle_mode_uses_previous_cycle_after_boundary() -> None:
    now_ts = ts(2026, 5, 22, 2, 0)

    assert resolve_cycle_start(now_ts, mode="completed") == ARC_EPOCH + ARC_PERIOD


def test_report_end_caps_completed_cycle_at_boundary() -> None:
    cycle_start = ARC_EPOCH
    now_ts = cycle_start + ARC_PERIOD + timedelta(hours=5).total_seconds()

    assert report_end_ts(cycle_start, now_ts) == cycle_start + ARC_PERIOD
