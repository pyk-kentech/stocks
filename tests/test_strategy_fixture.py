import json

import pytest

from stock_risk_mcp.strategy_fixture import load_strategy_fixture


def test_fixture_loads_only_strict_explicit_json(tmp_path) -> None:
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps({
        "schema_version": "3.0",
        "config": {},
        "snapshots": [{"snapshot_id": "s1", "ticker": "ABC", "region": "US", "observed_at": "2026-06-15T00:00:00", "features": {"signal_score": 0.8, "risk_score": 0.2, "hard_block": False}}],
        "candidates": [{"candidate_id": "c1", "snapshot_id": "s1", "side": "BUY", "order_type": "LIMIT", "quantity": 1, "limit_price": 10, "rationale": "fixture"}],
    }), encoding="utf-8")

    fixture = load_strategy_fixture(path)
    assert fixture.snapshots[0].ticker == "ABC"

    bad = tmp_path / "bad.json"
    bad.write_text('{"schema_version":"3.0","config":{},"snapshots":[],"candidates":[],"extra":true}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_strategy_fixture(bad)
    wrong_version = tmp_path / "wrong-version.json"
    wrong_version.write_text('{"schema_version":"2.0","config":{},"snapshots":[],"candidates":[]}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_strategy_fixture(wrong_version)


def test_fixture_rejects_broken_snapshot_reference(tmp_path) -> None:
    path = tmp_path / "fixture.json"
    path.write_text('{"schema_version":"3.0","config":{},"snapshots":[],"candidates":[{"candidate_id":"c1","snapshot_id":"missing","side":"BUY","order_type":"LIMIT","quantity":1,"limit_price":1,"rationale":"x"}]}', encoding="utf-8")
    with pytest.raises(ValueError, match="snapshot"):
        load_strategy_fixture(path)
