import pytest

from stock_risk_mcp.domestic_replay_fixture import load_domestic_replay_fixture
from stock_risk_mcp.domestic_replay_models import ReplayPromotionReadinessStatus
from tests.test_domestic_candidate_evaluation_fixture import (
    domestic_candidate_evaluation_fixture_payload,
)
from tests.test_domestic_realtime_fixture import write


def replay_clock_policy_payload():
    return {
        "primary_ordering_field": "PROVIDER_TIMESTAMP",
        "secondary_ordering_field": "RECEIVED_TIMESTAMP",
        "deterministic_tie_breaker": "SOURCE_EVENT_ID",
        "out_of_order_handling_policy": "SORT_BY_POLICY",
        "impossible_timestamp_handling_policy": "FAIL_CLOSED",
        "gap_handling_policy": "TRACE_ONLY",
        "replay_clock_advancement_mode": "EVENT_TIMESTAMP_STEP",
    }


def replay_config_payload(*, strategy_track: str = "DOMESTIC_KR", report_only_mode: bool = False):
    return {
        "config_id": "domestic-replay-config-1",
        "strategy_track": strategy_track,
        "report_only_mode": report_only_mode,
        "replay_ordering_mode": "PROVIDER_TIMESTAMP_THEN_RECEIVED",
        "replay_tie_breaker_mode": "SOURCE_EVENT_ID",
        "duplicate_event_policy": "KEEP_ALL",
        "missing_timestamp_policy": "FAIL_CLOSED",
        "stale_event_policy": "REPORT_ONLY" if report_only_mode else "FAIL_CLOSED",
        "report_only_event_policy": "ALLOW_EXPLICIT_REPORT_ONLY" if report_only_mode else "FAIL_CLOSED",
        "replay_window_size": 2,
        "replay_metrics_policy": "EVENT_TRACE_DERIVED",
        "promotion_readiness_policy": "OFFLINE_ONLY",
        "replay_clock_policy": replay_clock_policy_payload(),
    }


def replay_sequence_payload(candidate_fixture: dict):
    events = candidate_fixture["domestic_scanner_fixture"]["domestic_realtime_fixture"]["events"]
    provider_times = [event["provider_timestamp"] for event in events]
    received_times = [event["received_timestamp"] for event in events]
    return {
        "sequence_id": "domestic-replay-sequence-1",
        "ordered_event_ids": [event["source_fixture_id"] for event in events],
        "sequence_start_timestamp": min(provider_times),
        "sequence_end_timestamp": max(received_times),
        "symbol_universe_snapshot": sorted({event["symbol"] for event in events}),
        "source_fixture_markers": [candidate_fixture["run_id"]],
    }


def domestic_replay_fixture_payload(*, replay_config: dict | None = None, candidate_fixture: dict | None = None):
    candidate = candidate_fixture or domestic_candidate_evaluation_fixture_payload()
    return {
        "schema_version": "4.5-domestic-replay-fixture",
        "run_id": "domestic-replay-run-1",
        "created_at": "2026-06-17T09:04:00+09:00",
        "replay_config": replay_config or replay_config_payload(),
        "domestic_candidate_evaluation_fixture": candidate,
        "replay_event_sequence": replay_sequence_payload(candidate),
    }


def test_domestic_replay_fixture_loads_valid_domestic_input(tmp_path):
    fixture = load_domestic_replay_fixture(
        write(tmp_path, "domestic_replay_fixture.json", domestic_replay_fixture_payload())
    )
    assert fixture.replay_config.strategy_track.value == "DOMESTIC_KR"
    assert fixture.replay_event_sequence.sequence_id == "domestic-replay-sequence-1"


def test_domestic_replay_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_domestic_replay_fixture(
            write(tmp_path, "domestic_replay_fixture.txt", domestic_replay_fixture_payload())
        )


def test_domestic_replay_fixture_rejects_missing_strategy_track(tmp_path):
    payload = domestic_replay_fixture_payload()
    del payload["replay_config"]["strategy_track"]
    with pytest.raises(ValueError, match="strategy_track"):
        load_domestic_replay_fixture(
            write(tmp_path, "domestic_replay_fixture.json", payload)
        )


def test_domestic_replay_fixture_rejects_missing_market_profile(tmp_path):
    payload = domestic_replay_fixture_payload()
    del payload["domestic_candidate_evaluation_fixture"]["domestic_scanner_fixture"]["domestic_realtime_fixture"]["strategy_request"]["market_profile"]
    with pytest.raises(ValueError, match="market_profile"):
        load_domestic_replay_fixture(write(tmp_path, "domestic_replay_fixture.json", payload))


def test_domestic_replay_fixture_rejects_overseas_track(tmp_path):
    payload = domestic_replay_fixture_payload(
        replay_config=replay_config_payload(strategy_track="OVERSEAS_US")
    )
    with pytest.raises(ValueError, match="DOMESTIC_KR"):
        load_domestic_replay_fixture(write(tmp_path, "domestic_replay_fixture.json", payload))


def test_domestic_replay_fixture_exposes_promotion_status_enum():
    assert ReplayPromotionReadinessStatus.REPLAY_PASS.value == "REPLAY_PASS"
