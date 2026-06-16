import json

import pytest

from stock_risk_mcp.paper_eval_fixture import load_paper_eval_fixture


def fixture_payload(inputs=None, price_paths=None, config=None):
    return {
        "schema_version": "3.6-paper-eval-fixture",
        "run_id": "paper-eval-run-1",
        "created_at": "2026-01-12T16:00:00+00:00",
        "config": config or {
            "initial_cash": 100000.0,
            "allow_limit_entry_only": True,
            "fee_per_trade": 0.0,
            "slippage_per_share": 0.0,
            "same_bar_exit_policy": "STOP_FIRST",
            "max_open_positions": 10,
        },
        "inputs": inputs or [{
            "ticker": "abc",
            "source_type": "TRADE_PLAN",
            "decision_time": "2026-01-10T09:30:00+00:00",
            "side": "BUY",
            "setup_grade": "A",
            "entry_reference": 100.0,
            "stop_reference": 96.0,
            "target_reference": 108.0,
            "suggested_quantity": 10,
            "plan_status": "TRADE_PLAN_READY",
            "technical_evidence_summary": "Tight pullback",
            "market_discovery_summary": "Volume spike candidate",
            "llm_signal_summary": "Positive catalyst",
        }],
        "price_paths": price_paths or [{
            "ticker": "abc",
            "bars": [
                {
                    "timestamp": "2026-01-10T09:31:00+00:00",
                    "open": 99.5,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.5,
                },
                {
                    "timestamp": "2026-01-10T09:32:00+00:00",
                    "open": 100.5,
                    "high": 109.0,
                    "low": 100.0,
                    "close": 108.5,
                },
            ],
        }],
    }


def write(tmp_path, name, value):
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_paper_eval_fixture_normalizes_tickers_and_validates_ohlc(tmp_path):
    fixture = load_paper_eval_fixture(write(tmp_path, "paper_eval_fixture.json", fixture_payload()))
    assert fixture.inputs[0].ticker == "ABC"
    assert fixture.price_paths[0].ticker == "ABC"
    assert fixture.price_paths[0].bars[0].low == 99.0


def test_paper_eval_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_paper_eval_fixture(write(tmp_path, "paper_eval_fixture.txt", fixture_payload()))


@pytest.mark.parametrize("change", [
    lambda value: value.update(created_at="2026-01-12T16:00:00"),
    lambda value: value["config"].update(same_bar_exit_policy="TARGET_FIRST"),
    lambda value: value["inputs"][0].update(suggested_quantity=-1),
    lambda value: value["inputs"][0].update(entry_reference=True),
    lambda value: value["price_paths"][0]["bars"][0].update(low=102.0),
    lambda value: value["price_paths"][0]["bars"].append(dict(value["price_paths"][0]["bars"][0])),
])
def test_paper_eval_fixture_rejects_invalid_values(tmp_path, change):
    value = fixture_payload()
    change(value)
    with pytest.raises(ValueError):
        load_paper_eval_fixture(write(tmp_path, "paper_eval_fixture.json", value))
