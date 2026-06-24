from stock_risk_mcp.event_risk_engine import build_event_risk_review
from stock_risk_mcp.event_risk_models import EventRiskDecision, EventRiskInput
from tests.test_event_risk_models import event_risk_payload


def _run(**overrides):
    payload = event_risk_payload()
    payload.update(overrides)
    return build_event_risk_review(EventRiskInput.model_validate(payload))


def test_no_relevant_event_produces_allow():
    result = _run(events=[], event_windows=[])
    assert result.summary_report.decision == EventRiskDecision.ALLOW


def test_fomc_three_hours_before_blocks_new_entries():
    result = _run(decision_timestamp="2026-06-24T20:30:00+09:00")
    assert result.summary_report.decision == EventRiskDecision.BLOCK_NEW_ENTRY


def test_cpi_pre_event_window_reduces_size():
    result = _run(
        events=[{
            "event_id": "CPI-20260624",
            "event_type": "CPI",
            "country_scope": "US",
            "market_scope": "GLOBAL",
            "affected_markets": ["NASDAQ"],
            "scheduled_at": "2026-06-24T21:30:00+09:00",
            "available_at": "2026-06-24T10:00:00+09:00",
            "source_provider_ref": "fixtures/provider/bls_calendar.json",
            "source_calendar_ref": "fixtures/calendar/cpi_calendar.json",
            "importance_level": "HIGH",
            "expected_impact": "VOLATILITY",
            "actual_value": None,
            "forecast_value": "2.8",
            "previous_value": "2.7",
            "event_status": "SCHEDULED",
            "timezone": "America/New_York",
            "event_window_policy_ref": "docs/policies/cpi_window.md",
        }],
        event_windows=[{
            "window_id": "CPI-WINDOW",
            "event_type": "CPI",
            "importance_level": "HIGH",
            "pre_event_block_window_minutes": 30,
            "pre_event_reduce_window_minutes": 60,
            "post_event_cooldown_minutes": 60,
            "event_active_window_minutes": 30,
            "new_entry_allowed": True,
            "position_increase_allowed": False,
            "reduce_only": False,
            "watch_only": False,
            "event_size_multiplier": 0.5,
            "forced_gap_if_calendar_missing": True,
            "policy_reason": "Reduce size before CPI",
        }],
        decision_timestamp="2026-06-24T20:45:00+09:00",
    )
    assert result.summary_report.decision == EventRiskDecision.REDUCE_SIZE


def test_nfp_pre_event_window_blocks_new_entries():
    result = _run(
        events=[{
            "event_id": "NFP-20260624",
            "event_type": "NFP",
            "country_scope": "US",
            "market_scope": "GLOBAL",
            "affected_markets": ["NASDAQ"],
            "scheduled_at": "2026-06-24T21:30:00+09:00",
            "available_at": "2026-06-24T10:00:00+09:00",
            "source_provider_ref": "fixtures/provider/bls_nfp.json",
            "source_calendar_ref": "fixtures/calendar/nfp_calendar.json",
            "importance_level": "CRITICAL",
            "expected_impact": "HIGH_VOL",
            "actual_value": None,
            "forecast_value": "200K",
            "previous_value": "175K",
            "event_status": "SCHEDULED",
            "timezone": "America/New_York",
            "event_window_policy_ref": "docs/policies/nfp_window.md",
        }],
        event_windows=[{
            "window_id": "NFP-WINDOW",
            "event_type": "NFP",
            "importance_level": "CRITICAL",
            "pre_event_block_window_minutes": 60,
            "pre_event_reduce_window_minutes": 180,
            "post_event_cooldown_minutes": 60,
            "event_active_window_minutes": 30,
            "new_entry_allowed": False,
            "position_increase_allowed": False,
            "reduce_only": False,
            "watch_only": False,
            "event_size_multiplier": 0.25,
            "forced_gap_if_calendar_missing": True,
            "policy_reason": "Block before NFP",
        }],
        decision_timestamp="2026-06-24T20:45:00+09:00",
    )
    assert result.summary_report.decision == EventRiskDecision.BLOCK_NEW_ENTRY


def test_bok_rate_decision_reduces_domestic_exposure():
    result = _run(
        market="KRX",
        country_scope="KR",
        events=[{
            "event_id": "BOK-20260624",
            "event_type": "BOK_RATE_DECISION",
            "country_scope": "KR",
            "market_scope": "KRX",
            "affected_markets": ["KRX"],
            "scheduled_at": "2026-06-24T10:30:00+09:00",
            "available_at": "2026-06-24T08:00:00+09:00",
            "source_provider_ref": "fixtures/provider/bok_calendar.json",
            "source_calendar_ref": "fixtures/calendar/bok_calendar.json",
            "importance_level": "HIGH",
            "expected_impact": "DOMESTIC_RATES",
            "actual_value": None,
            "forecast_value": "HOLD",
            "previous_value": "HOLD",
            "event_status": "SCHEDULED",
            "timezone": "Asia/Seoul",
            "event_window_policy_ref": "docs/policies/bok_window.md",
        }],
        event_windows=[{
            "window_id": "BOK-WINDOW",
            "event_type": "BOK_RATE_DECISION",
            "importance_level": "HIGH",
            "pre_event_block_window_minutes": 0,
            "pre_event_reduce_window_minutes": 120,
            "post_event_cooldown_minutes": 60,
            "event_active_window_minutes": 30,
            "new_entry_allowed": True,
            "position_increase_allowed": False,
            "reduce_only": False,
            "watch_only": True,
            "event_size_multiplier": 0.5,
            "forced_gap_if_calendar_missing": True,
            "policy_reason": "Reduce before BOK decision",
        }],
        decision_timestamp="2026-06-24T09:30:00+09:00",
    )
    assert result.summary_report.decision in {EventRiskDecision.REDUCE_SIZE, EventRiskDecision.WATCH_ONLY}


def test_earnings_window_blocks_single_name_entry():
    result = _run(
        candidate_symbol="AAPL",
        is_single_name=True,
        events=[{
            "event_id": "AAPL-EARNINGS",
            "event_type": "EARNINGS",
            "country_scope": "US",
            "market_scope": "NASDAQ",
            "affected_markets": ["NASDAQ"],
            "scheduled_at": "2026-06-24T17:00:00+09:00",
            "available_at": "2026-06-24T09:00:00+09:00",
            "source_provider_ref": "fixtures/provider/earnings_calendar.json",
            "source_calendar_ref": "fixtures/calendar/earnings_calendar.json",
            "importance_level": "HIGH",
            "expected_impact": "SINGLE_NAME_VOL",
            "actual_value": None,
            "forecast_value": "EPS",
            "previous_value": "EPS",
            "event_status": "SCHEDULED",
            "timezone": "America/New_York",
            "event_window_policy_ref": "docs/policies/earnings_window.md",
        }],
        event_windows=[{
            "window_id": "EARNINGS-WINDOW",
            "event_type": "EARNINGS",
            "importance_level": "HIGH",
            "pre_event_block_window_minutes": 240,
            "pre_event_reduce_window_minutes": 480,
            "post_event_cooldown_minutes": 120,
            "event_active_window_minutes": 60,
            "new_entry_allowed": False,
            "position_increase_allowed": False,
            "reduce_only": False,
            "watch_only": True,
            "event_size_multiplier": 0.0,
            "forced_gap_if_calendar_missing": True,
            "policy_reason": "Block single-name entries into earnings",
        }],
        decision_timestamp="2026-06-24T14:00:00+09:00",
    )
    assert result.summary_report.decision in {EventRiskDecision.BLOCK_NEW_ENTRY, EventRiskDecision.WATCH_ONLY}


def test_post_event_cooldown_works():
    result = _run(decision_timestamp="2026-06-25T00:15:00+09:00")
    assert result.summary_report.decision == EventRiskDecision.COOLDOWN


def test_reduce_only_allows_exposure_reducing_action_only():
    reducing = _run(candidate_action_type="TRIM", net_exposure_reducing_action=True, decision_timestamp="2026-06-24T23:10:00+09:00")
    assert reducing.summary_report.decision in {EventRiskDecision.REDUCE_ONLY, EventRiskDecision.ALLOW}
    blocked = _run(candidate_action_type="ADD", net_exposure_reducing_action=False, decision_timestamp="2026-06-24T23:10:00+09:00",
                   event_windows=[{
                       "window_id": "FOMC-REDUCE-ONLY",
                       "event_type": "FOMC_RATE_DECISION",
                       "importance_level": "CRITICAL",
                       "pre_event_block_window_minutes": 0,
                       "pre_event_reduce_window_minutes": 0,
                       "post_event_cooldown_minutes": 120,
                       "event_active_window_minutes": 30,
                       "new_entry_allowed": False,
                       "position_increase_allowed": False,
                       "reduce_only": True,
                       "watch_only": False,
                       "event_size_multiplier": 0.0,
                       "forced_gap_if_calendar_missing": True,
                       "policy_reason": "Reduce only after event",
                   }])
    assert blocked.summary_report.decision == EventRiskDecision.REDUCE_ONLY


def test_missing_calendar_provider_readiness_causes_data_gap():
    result = _run(provider_readiness_ref=None, provider_readiness_level="GAP")
    assert result.summary_report.decision == EventRiskDecision.DATA_GAP


def test_stale_calendar_causes_data_gap():
    result = _run(calendar_freshness_minutes=1000, calendar_max_age_minutes=120)
    assert result.summary_report.decision in {EventRiskDecision.DATA_GAP, EventRiskDecision.WATCH_ONLY}


def test_missing_available_at_causes_data_gap_or_blocked():
    result = _run(available_at=None)
    assert result.summary_report.decision in {EventRiskDecision.DATA_GAP, EventRiskDecision.BLOCKED}


def test_future_event_knowledge_leakage_blocks():
    result = _run(events=[{
        "event_id": "CPI-LEAK",
        "event_type": "CPI",
        "country_scope": "US",
        "market_scope": "GLOBAL",
        "affected_markets": ["NASDAQ"],
        "scheduled_at": "2026-06-24T21:30:00+09:00",
        "available_at": "2026-06-24T12:00:00+09:00",
        "source_provider_ref": "fixtures/provider/bls_calendar.json",
        "source_calendar_ref": "fixtures/calendar/cpi_calendar.json",
        "importance_level": "HIGH",
        "expected_impact": "VOLATILITY",
        "actual_value": None,
        "forecast_value": "2.8",
        "previous_value": "2.7",
        "event_status": "SCHEDULED",
        "timezone": "America/New_York",
        "event_window_policy_ref": "docs/policies/cpi_window.md",
    }])
    assert result.summary_report.decision == EventRiskDecision.BLOCKED


def test_future_actual_value_leakage_blocks():
    result = _run(events=[{
        "event_id": "CPI-ACTUAL-LEAK",
        "event_type": "CPI",
        "country_scope": "US",
        "market_scope": "GLOBAL",
        "affected_markets": ["NASDAQ"],
        "scheduled_at": "2026-06-24T21:30:00+09:00",
        "available_at": "2026-06-24T10:00:00+09:00",
        "source_provider_ref": "fixtures/provider/bls_calendar.json",
        "source_calendar_ref": "fixtures/calendar/cpi_calendar.json",
        "importance_level": "HIGH",
        "expected_impact": "VOLATILITY",
        "actual_value": "3.5",
        "forecast_value": "2.8",
        "previous_value": "2.7",
        "event_status": "SCHEDULED",
        "timezone": "America/New_York",
        "event_window_policy_ref": "docs/policies/cpi_window.md",
    }])
    assert result.summary_report.decision == EventRiskDecision.BLOCKED


def test_executable_order_object_presence_blocks():
    result = _run(source_refs=["fixtures/calendar/cpi_calendar.json", "real_order_payload.json"])
    assert result.summary_report.decision == EventRiskDecision.BLOCKED


def test_output_remains_non_executable_and_audit_redacted():
    result = _run()
    assert result.summary_report.report_only is True
    assert result.summary_report.non_executable is True
    assert result.audit_records[0].redaction_applied is True

