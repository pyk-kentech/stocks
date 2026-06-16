import json

import pytest

from stock_risk_mcp.trade_plan_fixture import load_trade_plan_fixture


def candidate_payload(candidates=None):
    return {
        "schema_version": "3.5-trade-plan-fixture",
        "run_id": "trade-plan-run-1",
        "created_at": "2026-01-10T15:30:00+00:00",
        "config": {
            "portfolio_equity": 100000.0,
            "risk_pct_per_trade": 0.01,
            "max_basket_risk_pct": 0.03,
            "fixed_min_risk_reward": 2.0,
        },
        "candidates": candidates or [{
            "ticker": "abc",
            "side": "BUY",
            "setup_type": "BREAKOUT_PULLBACK",
            "setup_grade": "A",
            "entry_reference": 100.0,
            "stop_reference": 96.0,
            "target_reference": 108.0,
            "atr_value": 2.0,
            "stop_distance_evidence": 4.0,
            "support_level": 95.5,
            "resistance_level": 108.0,
            "technical_evidence_summary": "Tight pullback",
            "llm_signal_summary": "Positive catalyst",
            "warnings": ["Needs open-range confirmation", "Needs open-range confirmation"],
        }],
    }


def write(tmp_path, name, value):
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_trade_plan_fixture_normalizes_ticker_and_warning_lists(tmp_path):
    fixture = load_trade_plan_fixture(write(tmp_path, "trade_plan_fixture.json", candidate_payload()))
    candidate = fixture.candidates[0]
    assert candidate.ticker == "ABC"
    assert candidate.warnings == ["Needs open-range confirmation"]


def test_trade_plan_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_trade_plan_fixture(write(tmp_path, "trade_plan_fixture.txt", candidate_payload()))


@pytest.mark.parametrize("change", [
    lambda value: value["candidates"][0].update(entry_reference=True),
    lambda value: value["candidates"][0].update(warnings=["ok", ""]),
    lambda value: value.update(created_at="2026-01-10T15:30:00"),
    lambda value: value["config"].update(risk_pct_per_trade=0),
    lambda value: value["config"].update(max_basket_risk_pct=2),
    lambda value: value["candidates"].append(dict(value["candidates"][0])),
])
def test_trade_plan_fixture_rejects_invalid_or_duplicate_values(tmp_path, change):
    value = candidate_payload()
    change(value)
    with pytest.raises(ValueError):
        load_trade_plan_fixture(write(tmp_path, "trade_plan_fixture.json", value))
