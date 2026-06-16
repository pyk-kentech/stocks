import json

import pytest

from stock_risk_mcp.walk_forward_policy_fixture import load_walk_forward_policy_fixture


def fixture_payload(candidate_policies=None, replay_rows=None, price_paths=None, window_config=None, promotion_gates=None):
    return {
        "schema_version": "3.7-policy-replay-fixture",
        "run_id": "policy-replay-run-1",
        "created_at": "2026-01-20T16:00:00+00:00",
        "window_config": window_config or {
            "train_window_count": 2,
            "eval_window_count": 1,
            "window_stride": 1,
            "minimum_eval_trades": 1,
        },
        "promotion_gates": promotion_gates or {
            "minimum_sample_count": 1,
            "max_drawdown_pct_cap": 12.0,
            "minimum_return_improvement_pct": 2.0,
            "minimum_stability_score": 0.6,
            "max_missing_data_rate": 0.5,
            "max_blocked_rate": 0.5,
        },
        "baseline_policy": {
            "policy_id": "baseline-v1",
            "score_weights": {"technical": 0.5, "discovery": 0.3, "llm": 0.2},
            "minimum_score_threshold": 70.0,
            "minimum_risk_reward": 2.0,
            "allowed_setup_grades": ["A", "B"],
            "max_risk_pct_per_trade": 0.01,
            "max_basket_risk_pct": 0.03,
            "llm_weight_cap": 0.25,
            "allow_short": False,
            "allow_margin": False,
            "allow_leverage": False,
            "allow_market_orders": False,
        },
        "candidate_policies": candidate_policies or [{
            "policy_id": "candidate-v2",
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
        "replay_rows": replay_rows or [
            {
                "ticker": "abc",
                "timestamp": "2026-01-10T09:30:00+00:00",
                "setup_grade": "A",
                "technical_score": 80.0,
                "discovery_score": 70.0,
                "llm_score": 60.0,
                "entry_reference": 100.0,
                "stop_reference": 96.0,
                "target_reference": 108.0,
                "price_path_id": "ABC-1",
            },
            {
                "ticker": "abc",
                "timestamp": "2026-01-11T09:30:00+00:00",
                "setup_grade": "A",
                "technical_score": 85.0,
                "discovery_score": 70.0,
                "llm_score": 60.0,
                "entry_reference": 100.0,
                "stop_reference": 96.0,
                "target_reference": 108.0,
                "price_path_id": "ABC-2",
            },
            {
                "ticker": "abc",
                "timestamp": "2026-01-12T09:30:00+00:00",
                "setup_grade": "A",
                "technical_score": 90.0,
                "discovery_score": 70.0,
                "llm_score": 60.0,
                "entry_reference": 100.0,
                "stop_reference": 96.0,
                "target_reference": 108.0,
                "price_path_id": "ABC-3",
            },
        ],
        "price_paths": price_paths or [
            {
                "price_path_id": "ABC-1",
                "ticker": "abc",
                "bars": [
                    {"timestamp": "2026-01-10T09:31:00+00:00", "open": 99.5, "high": 101.0, "low": 99.0, "close": 100.0},
                    {"timestamp": "2026-01-10T09:32:00+00:00", "open": 100.0, "high": 109.0, "low": 100.0, "close": 108.0},
                ],
            },
            {
                "price_path_id": "ABC-2",
                "ticker": "abc",
                "bars": [
                    {"timestamp": "2026-01-11T09:31:00+00:00", "open": 99.5, "high": 101.0, "low": 99.0, "close": 100.0},
                    {"timestamp": "2026-01-11T09:32:00+00:00", "open": 100.0, "high": 109.0, "low": 100.0, "close": 108.0},
                ],
            },
            {
                "price_path_id": "ABC-3",
                "ticker": "abc",
                "bars": [
                    {"timestamp": "2026-01-12T09:31:00+00:00", "open": 99.5, "high": 101.0, "low": 99.0, "close": 100.0},
                    {"timestamp": "2026-01-12T09:32:00+00:00", "open": 100.0, "high": 109.0, "low": 100.0, "close": 108.0},
                ],
            },
        ],
    }


def write(tmp_path, name, value):
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_policy_replay_fixture_normalizes_tickers_and_policy_ids(tmp_path):
    fixture = load_walk_forward_policy_fixture(write(tmp_path, "policy_replay_fixture.json", fixture_payload()))
    assert fixture.replay_rows[0].ticker == "ABC"
    assert fixture.price_paths[0].ticker == "ABC"
    assert fixture.baseline_policy.policy_id == "baseline-v1"


def test_policy_replay_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_walk_forward_policy_fixture(write(tmp_path, "policy_replay_fixture.txt", fixture_payload()))


@pytest.mark.parametrize("change", [
    lambda value: value.update(created_at="2026-01-20T16:00:00"),
    lambda value: value["candidate_policies"][0].update(policy_id="baseline-v1"),
    lambda value: value["candidate_policies"][0]["score_weights"].update(llm=True),
    lambda value: value["replay_rows"][0].update(entry_reference=True),
    lambda value: value["price_paths"][0]["bars"][0].update(low=102.0),
    lambda value: value["replay_rows"][0].update(price_path_id="MISSING"),
])
def test_policy_replay_fixture_rejects_invalid_values(tmp_path, change):
    value = fixture_payload()
    change(value)
    with pytest.raises(ValueError):
        load_walk_forward_policy_fixture(write(tmp_path, "policy_replay_fixture.json", value))
