import json

from stock_risk_mcp.market_discovery_fixture import load_market_discovery_fixture
from stock_risk_mcp.market_discovery_scoring import scan_market_discovery
from stock_risk_mcp.market_discovery_service import run_market_discovery
from tests.test_market_discovery_fixture import payload, write_csv, write_json


def row(ticker, price=12, previous_close=10, volume=3_000_000, average_volume_20d=1_000_000, average_dollar_volume_20d=20_000_000):
    return {
        "ticker": ticker,
        "observed_at": "2026-01-01T15:59:00+00:00",
        "price": price,
        "previous_close": previous_close,
        "volume": volume,
        "average_volume_20d": average_volume_20d,
        "average_dollar_volume_20d": average_dollar_volume_20d,
    }


def test_fixed_scoring_classification_sorting_and_limit(tmp_path):
    fixture, _ = load_market_discovery_fixture(write_json(tmp_path, payload(
        rows=[
            row("BBB"),
            row("AAA"),
            row("WATCH", price=11, volume=2_000_000),
            row("LOW", average_dollar_volume_20d=1_000),
            row("NONE", price=10, volume=1_000_000, average_dollar_volume_20d=20_000_000),
        ],
        max_candidates=2,
    )))
    result = scan_market_discovery(fixture, "checksum", "JSON")

    assert [item.ticker for item in result.evaluations] == ["AAA", "BBB", "WATCH", "LOW", "NONE"]
    assert [(item.ticker, item.classification.value, item.score) for item in result.candidates] == [
        ("AAA", "DISCOVER", 90),
        ("BBB", "DISCOVER", 90),
    ]
    assert result.summary_counts == {"DISCOVER": 2, "WATCH": 1, "EXCLUDE": 2}
    assert result.evaluations[0].evidence.volume_spike_ratio == 3
    assert result.evaluations[0].evidence.dollar_volume == 36_000_000
    assert result.evaluations[3].classification.value == "EXCLUDE"
    assert "LIQUIDITY_BELOW_MINIMUM" in result.evaluations[3].reasons


def test_json_and_csv_services_produce_equivalent_normalized_results(tmp_path):
    value = payload(rows=[row("BBB"), row("AAA")])
    json_result = run_market_discovery(write_json(tmp_path, value))
    csv_result = run_market_discovery(write_csv(tmp_path, value))

    assert json_result.evaluations == csv_result.evaluations
    assert json_result.candidates == csv_result.candidates
    assert json_result.metadata_json["advisory_only"] is True
    assert json_result.metadata_json["external_network_calls"] is False


def test_service_writes_and_loads_strict_result(tmp_path):
    from stock_risk_mcp.market_discovery_service import load_market_discovery_result

    output = tmp_path / "result.json"
    result = run_market_discovery(write_json(tmp_path, payload()), output)
    loaded = load_market_discovery_result(output)
    assert loaded == result
    invalid = json.loads(output.read_text(encoding="utf-8"))
    invalid["unexpected"] = True
    output.write_text(json.dumps(invalid), encoding="utf-8")
    try:
        load_market_discovery_result(output)
    except ValueError:
        pass
    else:
        raise AssertionError("strict result validation must reject unknown fields")
