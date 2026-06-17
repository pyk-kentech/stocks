import pytest

from stock_risk_mcp.domestic_calibration_fixture import load_domestic_calibration_fixture
from stock_risk_mcp.domestic_calibration_models import PromotionGateStatus
from stock_risk_mcp.domestic_replay_engine import build_domestic_replay_report
from stock_risk_mcp.domestic_replay_fixture import load_domestic_replay_fixture
from tests.test_domestic_realtime_fixture import write
from tests.test_domestic_replay_fixture import domestic_replay_fixture_payload


def _replay_report_payload(tmp_path, replay_payload: dict | None = None):
    fixture = load_domestic_replay_fixture(
        write(tmp_path, "domestic_replay_fixture.json", replay_payload or domestic_replay_fixture_payload())
    )
    return build_domestic_replay_report(fixture).model_dump(mode="json")


def scanner_threshold_payload(
    *,
    volume_spike_threshold: float = 2.0,
    momentum_threshold: float = 1.0,
    liquidity_threshold: float = 0.02,
    stale_data_strictness: str = "FAIL_CLOSED",
    report_only_handling: str = "ALLOW_EXPLICIT_REPORT_ONLY",
    watchlist_add_threshold: int = 70,
    watchlist_remove_threshold: int = 25,
):
    return {
        "volume_spike_threshold": volume_spike_threshold,
        "momentum_threshold": momentum_threshold,
        "liquidity_threshold": liquidity_threshold,
        "stale_data_strictness": stale_data_strictness,
        "report_only_handling": report_only_handling,
        "watchlist_add_threshold": watchlist_add_threshold,
        "watchlist_remove_threshold": watchlist_remove_threshold,
        "scanner_candidate_explosion_guardrail": 5,
    }


def evaluation_threshold_payload(
    *,
    minimum_technical_score: int = 60,
    minimum_net_profit_threshold: float = 0.01,
    maximum_break_even_move: float = 0.02,
    risk_block_threshold: int = 50,
):
    return {
        "minimum_technical_score": minimum_technical_score,
        "minimum_net_profit_threshold": minimum_net_profit_threshold,
        "maximum_break_even_move": maximum_break_even_move,
        "risk_block_threshold": risk_block_threshold,
        "technical_evidence_missing_policy": "BLOCK_OR_WATCH",
        "profitability_context_missing_policy": "BLOCK_OR_WATCH",
        "compatibility_mapping_preservation_policy": "PRESERVE",
    }


def policy_candidate_payload(
    *,
    policy_id: str = "BASELINE_POLICY",
    label: str = "Baseline policy",
    strategy_track: str = "DOMESTIC_KR",
    market_profile_summary: dict | None = None,
    scanner_threshold_config: dict | None = None,
    evaluation_threshold_config: dict | None = None,
):
    return {
        "policy_id": policy_id,
        "label": label,
        "strategy_track": strategy_track,
        "market_profile_summary": market_profile_summary or {
            "market_id": "KRX",
            "country": "KR",
            "base_currency": "KRW",
        },
        "scanner_threshold_config": scanner_threshold_config or scanner_threshold_payload(),
        "evaluation_threshold_config": evaluation_threshold_config or evaluation_threshold_payload(),
        "report_only_policy_markers": ["NON_ACTIONABLE_ONLY"],
        "stale_data_handling_markers": ["FAIL_CLOSED"],
        "provenance_markers": ["FIXTURE_ONLY"],
    }


def promotion_gate_criteria_payload(
    *,
    minimum_calibration_pack_size: int = 2,
    minimum_scenario_family_count: int = 2,
    minimum_window_coverage: int = 2,
):
    return {
        "minimum_calibration_pack_size": minimum_calibration_pack_size,
        "minimum_scenario_family_count": minimum_scenario_family_count,
        "minimum_window_coverage": minimum_window_coverage,
        "maximum_safety_regression_count": 0,
        "maximum_stale_data_regression_count": 0,
        "maximum_domestic_only_regression_count": 0,
        "maximum_report_only_invariant_regression_count": 0,
        "maximum_non_actionable_invariant_regression_count": 0,
        "maximum_unsafe_trigger_regression_count": 0,
        "minimum_safety_score": 100,
        "minimum_coverage_score": 70,
        "minimum_stability_score": 50,
    }


def calibration_run_config_payload(
    *,
    strategy_track: str = "DOMESTIC_KR",
    required_scenario_families: list[str] | None = None,
):
    return {
        "calibration_run_id": "domestic-calibration-run-1",
        "strategy_track": strategy_track,
        "baseline_policy_id": "BASELINE_POLICY",
        "candidate_policy_ids": ["STRICTER_POLICY", "LOOSER_POLICY"],
        "comparison_mode": "HYBRID_SINGLE_RUN_PLUS_PACK",
        "required_scenario_families": required_scenario_families or ["BASELINE", "STALE_REPORT_ONLY"],
        "minimum_replay_count": 2,
        "minimum_window_count": 2,
        "regression_policy": "FAIL_CLOSED",
        "coverage_policy": "PACK_REQUIRED",
        "promotion_gate_criteria": promotion_gate_criteria_payload(),
    }


def calibration_fixture_payload(tmp_path, *, run_config: dict | None = None, replay_reports: list[dict] | None = None):
    reports = replay_reports or [
        _replay_report_payload(tmp_path),
        _replay_report_payload(tmp_path),
    ]
    return {
        "schema_version": "4.6-domestic-calibration-fixture",
        "run_id": "domestic-calibration-fixture-1",
        "created_at": "2026-06-17T10:00:00+09:00",
        "calibration_run_config": run_config or calibration_run_config_payload(),
        "calibration_input_set": {
            "input_set_id": "calibration-input-set-1",
            "market_profile_summary": {"market_id": "KRX", "country": "KR", "base_currency": "KRW"},
            "scenario_family_labels": ["BASELINE", "STALE_REPORT_ONLY"],
            "advisory_context_markers": ["OFFLINE_ONLY"],
            "replay_reports": reports,
            "replay_fixture_provenance_markers": ["v4.5_fixture_only"],
        },
        "baseline_policy": policy_candidate_payload(),
        "candidate_policies": [
            policy_candidate_payload(
                policy_id="STRICTER_POLICY",
                label="Stricter",
                scanner_threshold_config=scanner_threshold_payload(volume_spike_threshold=3.0, momentum_threshold=1.5),
                evaluation_threshold_config=evaluation_threshold_payload(minimum_technical_score=75, minimum_net_profit_threshold=0.02),
            ),
            policy_candidate_payload(
                policy_id="LOOSER_POLICY",
                label="Looser",
                scanner_threshold_config=scanner_threshold_payload(volume_spike_threshold=1.5, momentum_threshold=0.5, watchlist_add_threshold=60),
                evaluation_threshold_config=evaluation_threshold_payload(minimum_technical_score=50, minimum_net_profit_threshold=0.005),
            ),
        ],
    }


def test_domestic_calibration_fixture_loads_valid_input(tmp_path):
    fixture = load_domestic_calibration_fixture(
        write(tmp_path, "domestic_calibration_fixture.json", calibration_fixture_payload(tmp_path))
    )
    assert fixture.calibration_run_config.strategy_track.value == "DOMESTIC_KR"
    assert len(fixture.calibration_input_set.replay_reports) == 2


def test_domestic_calibration_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_domestic_calibration_fixture(
            write(tmp_path, "domestic_calibration_fixture.txt", calibration_fixture_payload(tmp_path))
        )


def test_domestic_calibration_fixture_rejects_missing_strategy_track(tmp_path):
    payload = calibration_fixture_payload(tmp_path)
    del payload["calibration_run_config"]["strategy_track"]
    with pytest.raises(ValueError, match="strategy_track"):
        load_domestic_calibration_fixture(
            write(tmp_path, "domestic_calibration_fixture.json", payload)
        )


def test_domestic_calibration_fixture_rejects_missing_market_profile(tmp_path):
    payload = calibration_fixture_payload(tmp_path)
    del payload["baseline_policy"]["market_profile_summary"]
    with pytest.raises(ValueError, match="market_profile"):
        load_domestic_calibration_fixture(write(tmp_path, "domestic_calibration_fixture.json", payload))


def test_domestic_calibration_fixture_rejects_missing_replay_report(tmp_path):
    payload = calibration_fixture_payload(tmp_path)
    payload["calibration_input_set"]["replay_reports"] = []
    with pytest.raises(ValueError, match="replay"):
        load_domestic_calibration_fixture(write(tmp_path, "domestic_calibration_fixture.json", payload))


def test_domestic_calibration_fixture_rejects_overseas_track(tmp_path):
    payload = calibration_fixture_payload(
        tmp_path,
        run_config=calibration_run_config_payload(strategy_track="OVERSEAS_US"),
    )
    with pytest.raises(ValueError, match="DOMESTIC_KR"):
        load_domestic_calibration_fixture(write(tmp_path, "domestic_calibration_fixture.json", payload))


def test_domestic_calibration_fixture_exposes_gate_status_enum():
    assert PromotionGateStatus.PROMOTION_REJECTED.value == "PROMOTION_REJECTED"
