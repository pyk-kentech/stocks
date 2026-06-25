from stock_risk_mcp.macro_regime_event_calendar import build_macro_regime_event_window_report
from stock_risk_mcp.macro_regime_provider_models import CanonicalMacroEvent


def test_event_calendar_manual_import_builds_event_windows():
    event = CanonicalMacroEvent.model_validate(
        {
            "event_id": "macro-cpi-1",
            "event_type": "CPI",
            "provider": "INVESTING_CALENDAR_MANUAL",
            "country": "US",
            "title": "US CPI",
            "event_time": "2026-06-26T13:30:00+00:00",
            "timezone": "UTC",
            "importance": "HIGH",
            "affected_assets": ["NQ_CONTINUOUS", "ES_CONTINUOUS", "USDKRW"],
            "pre_event_block_window_minutes": 30,
            "pre_event_reduce_window_minutes": 60,
            "post_event_cooldown_minutes": 45,
            "event_active_window_minutes": 15,
            "source_ref": "fixtures/macro/events.json",
            "available_at": "2026-06-20T00:00:00+00:00",
        }
    )
    report = build_macro_regime_event_window_report(
        "macro-regime-test",
        event.event_time,
        [event],
    )
    assert report.active_window_count == 1
    assert report.upcoming_window_count == 0
    assert report.windows[0].phase == "ACTIVE"
    assert report.report_only is True
