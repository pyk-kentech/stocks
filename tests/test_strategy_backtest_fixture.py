import json

import pytest

from stock_risk_mcp.strategy_backtest_fixture import load_strategy_backtest_fixture


def payload():
    return {
        "schema_version": "3.1",
        "strategy_config": {},
        "backtest_config": {"initial_cash": 1000, "fixed_quantity": 1},
        "snapshots": [{
            "snapshot": {
                "snapshot_id": "s1", "ticker": "ABC", "region": "US",
                "observed_at": "2026-01-01T09:00:00+00:00",
                "features": {"signal_score": 0.8, "risk_score": 0.2, "hard_block": False},
            },
            "features_available_at": "2026-01-01T09:00:00+00:00",
        }],
        "candidate_events": [{
            "candidate": {
                "candidate_id": "c1", "snapshot_id": "s1", "side": "BUY",
                "order_type": "LIMIT", "rationale": "fixture",
            },
            "decision_timestamp": "2026-01-01T09:05:00+00:00",
        }],
        "price_paths": [{
            "ticker": "ABC",
            "points": [
                {"timestamp": "2026-01-01T09:05:00+00:00", "price": 99},
                {"timestamp": "2026-01-01T09:06:00+00:00", "price": 100},
                {"timestamp": "2026-01-01T09:07:00+00:00", "price": 110},
            ],
        }],
    }


def write(tmp_path, value):
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "backtest.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_loads_strict_valid_backtest_fixture(tmp_path) -> None:
    fixture = load_strategy_backtest_fixture(write(tmp_path, payload()))
    assert fixture.backtest_config.initial_cash == 1000
    assert fixture.candidate_events[0].candidate.snapshot_id == "s1"


@pytest.mark.parametrize("field,value", [("initial_cash", 0), ("fixed_quantity", -1)])
def test_requires_positive_backtest_config(tmp_path, field, value) -> None:
    value_payload = payload()
    value_payload["backtest_config"][field] = value
    with pytest.raises(ValueError):
        load_strategy_backtest_fixture(write(tmp_path, value_payload))


def test_rejects_timezone_lookahead_duplicates_and_unordered_prices(tmp_path) -> None:
    cases = []
    no_timezone = payload()
    no_timezone["candidate_events"][0]["decision_timestamp"] = "2026-01-01T09:05:00"
    cases.append(no_timezone)
    snapshot_no_timezone = payload()
    snapshot_no_timezone["snapshots"][0]["snapshot"]["observed_at"] = "2026-01-01T09:00:00"
    cases.append(snapshot_no_timezone)
    lookahead = payload()
    lookahead["snapshots"][0]["features_available_at"] = "2026-01-01T09:06:00+00:00"
    cases.append(lookahead)
    duplicate = payload()
    duplicate["candidate_events"].append(dict(duplicate["candidate_events"][0]))
    duplicate["candidate_events"][1] = json.loads(json.dumps(duplicate["candidate_events"][1]))
    duplicate["candidate_events"][1]["candidate"]["candidate_id"] = "c2"
    cases.append(duplicate)
    unordered = payload()
    unordered["price_paths"][0]["points"][1]["timestamp"] = "2026-01-01T09:04:00+00:00"
    cases.append(unordered)

    for index, value in enumerate(cases):
        with pytest.raises(ValueError):
            load_strategy_backtest_fixture(write(tmp_path / str(index), value))
