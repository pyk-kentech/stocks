from stock_risk_mcp.walk_forward_policy_engine import build_walk_forward_policy_report
from stock_risk_mcp.walk_forward_policy_models import WalkForwardPolicyFixture
from tests.test_walk_forward_policy_fixture import fixture_payload


def fixture(value=None):
    return WalkForwardPolicyFixture.model_validate(value or fixture_payload())


def test_baseline_and_candidate_are_rerun_on_same_replay_fixture():
    report = build_walk_forward_policy_report(fixture(), "fixture-checksum")
    window = report.window_results[0]
    assert window.baseline.replay_row_count == window.candidate_results[0].replay_row_count
    assert window.baseline.eval_window_dates == window.candidate_results[0].eval_window_dates


def test_report_is_deterministic_and_can_promote_candidate():
    report = build_walk_forward_policy_report(fixture(), "fixture-checksum")
    same = build_walk_forward_policy_report(fixture(), "fixture-checksum")
    comparison = report.candidate_comparisons[0]
    assert same == report
    assert comparison.promotion_decision == "PROMOTE_CANDIDATE_POLICY"
    assert report.metadata_json["advisory_only"] is True
    assert report.metadata_json["production_policy_changed"] is False


def test_insufficient_sample_and_unsafe_policy_are_gated():
    insufficient = build_walk_forward_policy_report(
        fixture(fixture_payload(
            window_config={"train_window_count": 2, "eval_window_count": 1, "window_stride": 1, "minimum_eval_trades": 5},
            promotion_gates={
                "minimum_sample_count": 5,
                "max_drawdown_pct_cap": 12.0,
                "minimum_return_improvement_pct": 2.0,
                "minimum_stability_score": 0.6,
                "max_missing_data_rate": 0.5,
                "max_blocked_rate": 0.5,
            },
        )),
        "fixture-checksum",
    )
    unsafe = build_walk_forward_policy_report(
        fixture(fixture_payload(candidate_policies=[{
            "policy_id": "candidate-unsafe",
            "score_weights": {"technical": 0.7, "discovery": 0.2, "llm": 0.1},
            "minimum_score_threshold": 70.0,
            "minimum_risk_reward": 2.0,
            "allowed_setup_grades": ["A", "B"],
            "max_risk_pct_per_trade": 0.01,
            "max_basket_risk_pct": 0.03,
            "llm_weight_cap": 0.20,
            "allow_short": False,
            "allow_margin": True,
            "allow_leverage": False,
            "allow_market_orders": False,
        }])),
        "fixture-checksum",
    )
    assert insufficient.candidate_comparisons[0].promotion_decision == "INSUFFICIENT_EVIDENCE"
    assert unsafe.candidate_comparisons[0].promotion_decision == "REJECT_UNSAFE_POLICY"


def test_demotion_keep_and_stability_threshold_are_reported():
    keep = build_walk_forward_policy_report(
        fixture(fixture_payload(candidate_policies=[{
            "policy_id": "candidate-keep",
            "score_weights": {"technical": 0.5, "discovery": 0.3, "llm": 0.2},
            "minimum_score_threshold": 70.0,
            "minimum_risk_reward": 2.0,
            "allowed_setup_grades": ["A", "B"],
            "max_risk_pct_per_trade": 0.01,
            "max_basket_risk_pct": 0.03,
            "llm_weight_cap": 0.20,
            "allow_short": False,
            "allow_margin": False,
            "allow_leverage": False,
            "allow_market_orders": False,
        }])),
        "fixture-checksum",
    )
    demote = build_walk_forward_policy_report(
        fixture(fixture_payload(
            promotion_gates={
                "minimum_sample_count": 0,
                "max_drawdown_pct_cap": 12.0,
                "minimum_return_improvement_pct": 2.0,
                "minimum_stability_score": 0.6,
                "max_missing_data_rate": 0.5,
                "max_blocked_rate": 0.5,
            },
            candidate_policies=[{
                "policy_id": "candidate-demote",
                "score_weights": {"technical": 0.1, "discovery": 0.1, "llm": 0.1},
                "minimum_score_threshold": 90.0,
                "minimum_risk_reward": 4.0,
                "allowed_setup_grades": ["A"],
                "max_risk_pct_per_trade": 0.01,
                "max_basket_risk_pct": 0.03,
                "llm_weight_cap": 0.10,
                "allow_short": False,
                "allow_margin": False,
                "allow_leverage": False,
                "allow_market_orders": False,
            }],
        )),
        "fixture-checksum",
    )
    unstable_fixture = fixture_payload(
        replay_rows=[
            {
                "ticker": "ABC", "timestamp": "2026-01-10T09:30:00+00:00", "setup_grade": "A",
                "technical_score": 80.0, "discovery_score": 70.0, "llm_score": 60.0,
                "entry_reference": 100.0, "stop_reference": 96.0, "target_reference": 108.0, "price_path_id": "ABC-1",
            },
            {
                "ticker": "ABC", "timestamp": "2026-01-11T09:30:00+00:00", "setup_grade": "A",
                "technical_score": 85.0, "discovery_score": 70.0, "llm_score": 60.0,
                "entry_reference": 100.0, "stop_reference": 96.0, "target_reference": 108.0, "price_path_id": "ABC-2",
            },
            {
                "ticker": "ABC", "timestamp": "2026-01-12T09:30:00+00:00", "setup_grade": "A",
                "technical_score": 90.0, "discovery_score": 70.0, "llm_score": 60.0,
                "entry_reference": 100.0, "stop_reference": 96.0, "target_reference": 108.0, "price_path_id": "ABC-3",
            },
            {
                "ticker": "ABC", "timestamp": "2026-01-13T09:30:00+00:00", "setup_grade": "A",
                "technical_score": 95.0, "discovery_score": 70.0, "llm_score": 60.0,
                "entry_reference": 100.0, "stop_reference": 96.0, "target_reference": 108.0, "price_path_id": "ABC-4",
            },
        ],
        price_paths=[
            {
                "price_path_id": "ABC-1", "ticker": "ABC",
                "bars": [
                    {"timestamp": "2026-01-10T09:31:00+00:00", "open": 99.5, "high": 101.0, "low": 99.0, "close": 100.0},
                    {"timestamp": "2026-01-10T09:32:00+00:00", "open": 100.0, "high": 109.0, "low": 100.0, "close": 108.0},
                ],
            },
            {
                "price_path_id": "ABC-2", "ticker": "ABC",
                "bars": [
                    {"timestamp": "2026-01-11T09:31:00+00:00", "open": 99.5, "high": 101.0, "low": 99.0, "close": 100.0},
                    {"timestamp": "2026-01-11T09:32:00+00:00", "open": 95.5, "high": 96.0, "low": 95.0, "close": 96.0},
                ],
            },
            {
                "price_path_id": "ABC-3", "ticker": "ABC",
                "bars": [
                    {"timestamp": "2026-01-12T09:31:00+00:00", "open": 99.5, "high": 101.0, "low": 99.0, "close": 100.0},
                    {"timestamp": "2026-01-12T09:32:00+00:00", "open": 100.0, "high": 109.0, "low": 100.0, "close": 108.0},
                ],
            },
            {
                "price_path_id": "ABC-4", "ticker": "ABC",
                "bars": [
                    {"timestamp": "2026-01-13T09:31:00+00:00", "open": 99.5, "high": 101.0, "low": 99.0, "close": 100.0},
                    {"timestamp": "2026-01-13T09:32:00+00:00", "open": 95.5, "high": 96.0, "low": 95.0, "close": 96.0},
                ],
            },
        ],
        window_config={"train_window_count": 1, "eval_window_count": 1, "window_stride": 1, "minimum_eval_trades": 1},
        promotion_gates={
            "minimum_sample_count": 1,
            "max_drawdown_pct_cap": 20.0,
            "minimum_return_improvement_pct": 2.0,
            "minimum_stability_score": 0.9,
            "max_missing_data_rate": 0.5,
            "max_blocked_rate": 0.5,
        },
        candidate_policies=[{
            "policy_id": "candidate-unstable",
            "score_weights": {"technical": 0.7, "discovery": 0.2, "llm": 0.1},
            "minimum_score_threshold": 70.0,
            "minimum_risk_reward": 2.0,
            "allowed_setup_grades": ["A", "B"],
            "max_risk_pct_per_trade": 0.01,
            "max_basket_risk_pct": 0.03,
            "llm_weight_cap": 0.20,
            "allow_short": False,
            "allow_margin": False,
            "allow_leverage": False,
            "allow_market_orders": False,
        }],
    )
    unstable = build_walk_forward_policy_report(fixture(unstable_fixture), "fixture-checksum")
    assert keep.candidate_comparisons[0].promotion_decision == "KEEP_BASELINE_POLICY"
    assert demote.candidate_comparisons[0].promotion_decision == "DEMOTE_CANDIDATE_POLICY"
    assert unstable.candidate_comparisons[0].promotion_decision == "INSUFFICIENT_EVIDENCE"
