import json

import pytest

from stock_risk_mcp.event_risk_fixture import load_event_risk_fixture
from stock_risk_mcp.event_risk_guard import validate_event_risk_metadata_safety
from stock_risk_mcp.event_risk_models import (
    EventImportance,
    EventRiskDecision,
    EventRiskInput,
    EventType,
)


def event_risk_payload(**overrides):
    payload = {
        "event_risk_review_id": "event-risk-1",
        "candidate_symbol": "QQQ",
        "market": "NASDAQ",
        "country_scope": "US",
        "candidate_action_type": "NEW_ENTRY",
        "candidate_side": "LONG",
        "decision_timestamp": "2026-06-24T11:00:00+09:00",
        "available_at": "2026-06-24T10:00:00+09:00",
        "provider_readiness_ref": "fixtures/provider/provider_selection_report.json",
        "provider_readiness_level": "PAPER_READY",
        "calendar_source_ref": "fixtures/calendar/economic_calendar.json",
        "calendar_provider_ref": "fixtures/provider/economic_calendar_provider.json",
        "calendar_freshness_minutes": 30,
        "calendar_max_age_minutes": 240,
        "fail_closed_if_calendar_missing": True,
        "position_sizing_ref": "fixtures/position_sizing/position_sizing_review.json",
        "position_sizing_decision": "SIZE_READY",
        "position_sizing_quantity": 40,
        "position_sizing_notional": 20000.0,
        "position_sizing_size_multiplier": 1.0,
        "market_regime_ref": "fixtures/regime/market_regime_report.json",
        "market_regime_label": "RISK_ON",
        "existing_position": False,
        "is_single_name": False,
        "is_inverse_or_hedge": False,
        "net_exposure_reducing_action": False,
        "events": [
            {
                "event_id": "FOMC-20260624",
                "event_type": "FOMC_RATE_DECISION",
                "country_scope": "US",
                "market_scope": "GLOBAL",
                "affected_markets": ["NASDAQ", "NYSE", "CME"],
                "scheduled_at": "2026-06-24T23:00:00+09:00",
                "available_at": "2026-06-24T10:00:00+09:00",
                "source_provider_ref": "fixtures/provider/fed_calendar.json",
                "source_calendar_ref": "fixtures/calendar/fomc_calendar.json",
                "importance_level": "CRITICAL",
                "expected_impact": "HIGH_VOL",
                "actual_value": None,
                "forecast_value": "HOLD",
                "previous_value": "HOLD",
                "event_status": "SCHEDULED",
                "timezone": "America/New_York",
                "event_window_policy_ref": "docs/policies/fomc_window.md",
            }
        ],
        "event_windows": [
            {
                "window_id": "FOMC-WINDOW",
                "event_type": "FOMC_RATE_DECISION",
                "importance_level": "CRITICAL",
                "pre_event_block_window_minutes": 180,
                "pre_event_reduce_window_minutes": 360,
                "post_event_cooldown_minutes": 120,
                "event_active_window_minutes": 60,
                "new_entry_allowed": False,
                "position_increase_allowed": False,
                "reduce_only": False,
                "watch_only": False,
                "event_size_multiplier": 0.5,
                "forced_gap_if_calendar_missing": True,
                "policy_reason": "Block new entries before FOMC",
            }
        ],
        "safety_report": {
            "safety_report_id": "event-risk-safety-1",
            "blocked_capabilities": [
                "LIVE_TRADING_BLOCKED",
                "REAL_ORDER_BLOCKED",
                "ACCOUNT_MUTATION_BLOCKED",
                "BROKER_API_BLOCKED",
                "KIWOOM_API_BLOCKED",
                "WEBSOCKET_BLOCKED",
                "NETWORK_BLOCKED",
                "AUTONOMOUS_TRADING_BLOCKED",
            ],
            "findings": [],
        },
        "audit_records": [
            {
                "audit_record_id": "event-risk-audit-1",
                "created_at": "2026-06-24T18:00:00+09:00",
                "source_path": "fixtures/event_risk/event_risk_fixture.json",
                "operator_context": "offline event risk review",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_default_event_risk_is_local_offline_report_only():
    loaded = EventRiskInput.model_validate(event_risk_payload())
    assert loaded.report_only is True
    assert loaded.offline_only is True
    assert loaded.no_broker_api is True
    assert loaded.no_order is True


def test_guard_rejects_secret_token_account_and_provider_markers():
    with pytest.raises(ValueError):
        validate_event_risk_metadata_safety({"authorization": "Bearer abc"}, context="event risk")
    with pytest.raises(ValueError):
        validate_event_risk_metadata_safety({"account_id": "123-45"}, context="event risk")


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "event_risk_fixture.json"
    fixture_path.write_text(json.dumps(event_risk_payload()), encoding="utf-8")
    loaded = load_event_risk_fixture(fixture_path)
    assert isinstance(loaded, EventRiskInput)
    assert loaded.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_event_risk_fixture("https://example.com/event_risk.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_event_risk_fixture(tmp_path / "event_risk.parquet")


def test_enum_surface():
    assert EventType.FOMC_RATE_DECISION.value == "FOMC_RATE_DECISION"
    assert EventType.EARNINGS.value == "EARNINGS"
    assert EventImportance.CRITICAL.value == "CRITICAL"
    assert EventRiskDecision.BLOCK_NEW_ENTRY.value == "BLOCK_NEW_ENTRY"

