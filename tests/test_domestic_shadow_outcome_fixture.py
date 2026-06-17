import pytest

from stock_risk_mcp.domestic_paper_shadow_engine import build_paper_shadow_journal
from stock_risk_mcp.domestic_paper_shadow_fixture import load_domestic_paper_shadow_fixture
from stock_risk_mcp.domestic_shadow_outcome_fixture import load_domestic_shadow_outcome_fixture
from stock_risk_mcp.domestic_shadow_outcome_models import PaperShadowOutcomeLabelType
from tests.test_domestic_candidate_evaluation_fixture import domestic_candidate_evaluation_fixture_payload
from tests.test_domestic_paper_shadow_fixture import paper_shadow_fixture_payload
from tests.test_domestic_realtime_fixture import event_payload, write


def _paper_shadow_journal_payload(tmp_path, paper_shadow_payload: dict | None = None):
    fixture = load_domestic_paper_shadow_fixture(
        write(
            tmp_path,
            "domestic_paper_shadow_fixture.json",
            paper_shadow_payload or paper_shadow_fixture_payload(tmp_path),
        )
    )
    return build_paper_shadow_journal(fixture).model_dump(mode="json")


def outcome_config_payload(*, strategy_track: str = "DOMESTIC_KR"):
    return {
        "config_id": "domestic-shadow-outcome-config-1",
        "strategy_track": strategy_track,
        "market_profile_id": "KRX",
        "explicit_shadow_outcome_opt_in": True,
        "report_only_preservation_mode": "PRESERVE",
        "blocked_context_preservation_mode": "PRESERVE",
        "inconclusive_labeling_mode": "FAIL_CLOSED_OR_LABEL",
        "aggregation_mode": "DERIVED_FROM_CANDIDATE_LABELS",
    }


def outcome_policy_payload(*, allow_report_only_observation_label: bool = False):
    return {
        "policy_id": "domestic-shadow-outcome-policy-1",
        "favorable_threshold_pct": 0.03,
        "adverse_threshold_pct": 0.02,
        "neutral_band_pct": 0.01,
        "minimum_point_count": 2,
        "allow_report_only_observation_label": allow_report_only_observation_label,
        "stale_data_policy": "FAIL_CLOSED",
        "threshold_precedence_rule": "HYBRID_TOUCH_AND_FINAL_STATE",
        "insufficient_data_rule": "LABEL_INSUFFICIENT_DATA",
        "safety_rejection_rule": "FAIL_OR_REJECT",
    }


def observation_window_payload():
    return {
        "window_id": "window-1",
        "start_timestamp": "2026-06-17T11:01:00+09:00",
        "end_timestamp": "2026-06-17T11:20:00+09:00",
        "horizon_label": "15M",
        "minimum_point_count": 2,
        "expected_cadence": "1M",
        "stale_tolerance_seconds": 120,
    }


def future_point(timestamp: str, price: float | None, volume: float = 1000.0):
    return {
        "timestamp": timestamp,
        "price": price,
        "volume": volume,
    }


def shadow_outcome_fixture_payload(
    tmp_path,
    *,
    journal_payload: dict | None = None,
    config: dict | None = None,
    policy: dict | None = None,
    future_points: list[dict] | None = None,
    decision_index: int = 0,
):
    journal = journal_payload or _paper_shadow_journal_payload(tmp_path)
    decision = journal["entries"][decision_index]
    return {
        "schema_version": "4.8-domestic-shadow-outcome-fixture",
        "run_id": "domestic-shadow-outcome-run-1",
        "created_at": "2026-06-17T11:30:00+09:00",
        "shadow_outcome_config": config or outcome_config_payload(),
        "shadow_outcome_input_set": {
            "input_set_id": "domestic-shadow-outcome-input-set-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_summary": {"market_id": "KRX", "country": "KR", "base_currency": "KRW"},
            "paper_shadow_journal": journal,
            "promotion_gate_context_reference": decision["source_promotion_gate_id"],
            "replay_window_references": ["REPLAY_WINDOW_A"],
            "scenario_family_markers": ["BASELINE"],
            "advisory_context_markers": ["NON_EXECUTABLE_CONTEXT_ONLY"],
        },
        "outcome_label_policy": policy or outcome_policy_payload(),
        "outcome_fixtures": [
            {
                "fixture_id": "outcome-fixture-1",
                "strategy_track": "DOMESTIC_KR",
                "market_profile_id": "KRX",
                "source_paper_shadow_journal_id": journal["journal_id"],
                "source_paper_shadow_decision_id": decision["journal_entry_id"],
                "candidate_id": decision["candidate_id"],
                "symbol": "005930",
                "fixture_timestamp": "2026-06-17T11:01:00+09:00",
                "observation_window": observation_window_payload(),
                "reference_price": 100.0,
                "future_points": future_points or [
                    future_point("2026-06-17T11:05:00+09:00", 103.5),
                    future_point("2026-06-17T11:10:00+09:00", 102.0),
                ],
                "benchmark_points": [],
                "data_quality_flags": [],
                "scenario_family": "BASELINE",
                "replay_window_id": "REPLAY_WINDOW_A",
                "promotion_gate_status": "PROMOTION_READY_FOR_PAPER_SHADOW",
            }
        ],
    }


def test_domestic_shadow_outcome_fixture_loads_valid_input(tmp_path):
    fixture = load_domestic_shadow_outcome_fixture(
        write(tmp_path, "domestic_shadow_outcome_fixture.json", shadow_outcome_fixture_payload(tmp_path))
    )
    assert fixture.shadow_outcome_config.strategy_track.value == "DOMESTIC_KR"
    assert fixture.outcome_fixtures[0].candidate_id


def test_domestic_shadow_outcome_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_domestic_shadow_outcome_fixture(
            write(tmp_path, "domestic_shadow_outcome_fixture.txt", shadow_outcome_fixture_payload(tmp_path))
        )


def test_domestic_shadow_outcome_fixture_rejects_missing_strategy_track(tmp_path):
    payload = shadow_outcome_fixture_payload(tmp_path)
    del payload["shadow_outcome_config"]["strategy_track"]
    with pytest.raises(ValueError, match="strategy_track"):
        load_domestic_shadow_outcome_fixture(
            write(tmp_path, "domestic_shadow_outcome_fixture.json", payload)
        )


def test_domestic_shadow_outcome_fixture_rejects_missing_market_profile(tmp_path):
    payload = shadow_outcome_fixture_payload(tmp_path)
    del payload["shadow_outcome_input_set"]["market_profile_summary"]
    with pytest.raises(ValueError, match="market_profile"):
        load_domestic_shadow_outcome_fixture(
            write(tmp_path, "domestic_shadow_outcome_fixture.json", payload)
        )


def test_domestic_shadow_outcome_fixture_rejects_missing_paper_shadow_journal(tmp_path):
    payload = shadow_outcome_fixture_payload(tmp_path)
    del payload["shadow_outcome_input_set"]["paper_shadow_journal"]
    with pytest.raises(ValueError, match="paper_shadow_journal"):
        load_domestic_shadow_outcome_fixture(
            write(tmp_path, "domestic_shadow_outcome_fixture.json", payload)
        )


def test_domestic_shadow_outcome_fixture_rejects_missing_paper_shadow_decision(tmp_path):
    payload = shadow_outcome_fixture_payload(tmp_path)
    payload["outcome_fixtures"][0]["source_paper_shadow_decision_id"] = "missing-entry"
    with pytest.raises(ValueError, match="paper shadow decision"):
        load_domestic_shadow_outcome_fixture(
            write(tmp_path, "domestic_shadow_outcome_fixture.json", payload)
        )


def test_domestic_shadow_outcome_fixture_rejects_missing_outcome_fixture(tmp_path):
    payload = shadow_outcome_fixture_payload(tmp_path)
    payload["outcome_fixtures"] = []
    with pytest.raises(ValueError, match="outcome fixture"):
        load_domestic_shadow_outcome_fixture(
            write(tmp_path, "domestic_shadow_outcome_fixture.json", payload)
        )


def test_domestic_shadow_outcome_fixture_rejects_missing_observation_window(tmp_path):
    payload = shadow_outcome_fixture_payload(tmp_path)
    del payload["outcome_fixtures"][0]["observation_window"]
    with pytest.raises(ValueError, match="observation_window"):
        load_domestic_shadow_outcome_fixture(
            write(tmp_path, "domestic_shadow_outcome_fixture.json", payload)
        )


def test_domestic_shadow_outcome_fixture_rejects_impossible_timestamp_ordering(tmp_path):
    payload = shadow_outcome_fixture_payload(tmp_path)
    payload["outcome_fixtures"][0]["observation_window"]["end_timestamp"] = "2026-06-17T10:59:00+09:00"
    with pytest.raises(ValueError, match="timestamp ordering"):
        load_domestic_shadow_outcome_fixture(
            write(tmp_path, "domestic_shadow_outcome_fixture.json", payload)
        )


def test_domestic_shadow_outcome_fixture_rejects_overseas_track(tmp_path):
    payload = shadow_outcome_fixture_payload(
        tmp_path,
        config=outcome_config_payload(strategy_track="OVERSEAS_US"),
    )
    with pytest.raises(ValueError, match="DOMESTIC_KR"):
        load_domestic_shadow_outcome_fixture(
            write(tmp_path, "domestic_shadow_outcome_fixture.json", payload)
        )


def test_domestic_shadow_outcome_fixture_rejects_unsafe_trigger_attempt(tmp_path):
    payload = shadow_outcome_fixture_payload(tmp_path)
    payload["outcome_fixtures"][0]["data_quality_flags"] = ["ORDER_TRIGGER_ATTEMPT"]
    with pytest.raises(ValueError, match="unsafe trigger"):
        load_domestic_shadow_outcome_fixture(
            write(tmp_path, "domestic_shadow_outcome_fixture.json", payload)
        )


def test_domestic_shadow_outcome_fixture_exposes_label_enum():
    assert PaperShadowOutcomeLabelType.OUTCOME_FAVORABLE.value == "OUTCOME_FAVORABLE"


def report_only_journal_payload(tmp_path):
    payload = domestic_candidate_evaluation_fixture_payload()
    payload["domestic_scanner_fixture"]["scanner_config"]["report_only_mode"] = True
    payload["domestic_scanner_fixture"]["domestic_realtime_fixture"]["report_only_mode"] = True
    payload["domestic_scanner_fixture"]["domestic_realtime_fixture"]["staleness_policy"]["allow_report_only_downgrade"] = True
    payload["domestic_scanner_fixture"]["domestic_realtime_fixture"]["events"] = [
        event_payload(provider_timestamp="2026-06-17T08:58:00+09:00", received_timestamp="2026-06-17T09:00:10+09:00")
    ]
    paper_shadow_payload = paper_shadow_fixture_payload(tmp_path)
    from tests.test_domestic_paper_shadow_engine import _eval_payload

    paper_shadow_payload["paper_shadow_input_set"]["candidate_evaluation_reports"] = [_eval_payload(tmp_path, payload)]
    return _paper_shadow_journal_payload(tmp_path, paper_shadow_payload)


def blocked_profitability_journal_payload(tmp_path):
    payload = domestic_candidate_evaluation_fixture_payload()
    payload["profitability_context"] = {
        "profitability_context_status": "REPORT_ONLY",
        "track_aware_profitability_check": "REPORT_ONLY",
        "expected_net_profit": -10.0,
        "expected_net_return_percentage": -0.01,
        "break_even_move": 0.02,
        "cost_aware_minimum_target_move": 0.03,
    }
    paper_shadow_payload = paper_shadow_fixture_payload(tmp_path)
    from tests.test_domestic_paper_shadow_engine import _eval_payload

    paper_shadow_payload["paper_shadow_input_set"]["candidate_evaluation_reports"] = [_eval_payload(tmp_path, payload)]
    return _paper_shadow_journal_payload(tmp_path, paper_shadow_payload)
