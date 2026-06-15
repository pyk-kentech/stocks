import json
import pytest

from stock_risk_mcp.technical_evidence_fixture import load_technical_fixture


def payload(count=20):
    points = []
    for i in range(count):
        close = 100 + i
        points.append({"timestamp": f"2026-01-{i + 1:02d}T16:00:00+00:00", "open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 1000})
    return {"schema_version": "3.2", "as_of_timestamp": "2026-02-01T16:00:00+00:00", "config": {}, "series": [{"ticker": "abc", "points": points}]}


def write(tmp_path, value):
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_loads_strict_fixture(tmp_path):
    fixture = load_technical_fixture(write(tmp_path, payload()))
    assert fixture.series[0].ticker == "ABC"


def test_rejects_invalid_timestamps_ohlc_order_asof_and_duplicates(tmp_path):
    cases = []
    no_tz = payload(); no_tz["series"][0]["points"][0]["timestamp"] = "2026-01-01T16:00:00"; cases.append(no_tz)
    bad_ohlc = payload(); bad_ohlc["series"][0]["points"][0]["low"] = 200; cases.append(bad_ohlc)
    unordered = payload(); unordered["series"][0]["points"][1]["timestamp"] = unordered["series"][0]["points"][0]["timestamp"]; cases.append(unordered)
    future = payload(); future["as_of_timestamp"] = "2026-01-01T00:00:00+00:00"; cases.append(future)
    duplicate = payload(); duplicate["series"].append(duplicate["series"][0]); cases.append(duplicate)
    for value in cases:
        with pytest.raises(ValueError):
            load_technical_fixture(write(tmp_path, value))
