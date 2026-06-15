import csv
import json

import pytest

from stock_risk_mcp.market_discovery_fixture import CSV_FIELDS, load_market_discovery_fixture


def payload(rows=None, **config_overrides):
    config = {
        "min_price": 1,
        "max_price": 100,
        "min_price_change_pct": 2,
        "min_volume_spike_ratio": 1.5,
        "min_dollar_volume_spike_ratio": 1.5,
        "min_average_dollar_volume_20d": 10_000_000,
        "max_candidates": 100,
        **config_overrides,
    }
    return {
        "schema_version": "3.3",
        "as_of_timestamp": "2026-01-01T16:00:00+00:00",
        "scanner_config": config,
        "rows": rows or [{
            "ticker": "abc",
            "observed_at": "2026-01-01T15:59:00+00:00",
            "price": 12.5,
            "previous_close": 12,
            "volume": 2_500_000,
            "average_volume_20d": 1_000_000,
            "average_dollar_volume_20d": 15_000_000,
        }],
    }


def write_json(tmp_path, value):
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def write_csv(tmp_path, value):
    path = tmp_path / "fixture.csv"
    config = value["scanner_config"]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in value["rows"]:
            writer.writerow({
                "schema_version": value["schema_version"],
                "as_of_timestamp": value["as_of_timestamp"],
                **config,
                **row,
            })
    return path


def test_loads_equivalent_strict_json_and_csv(tmp_path):
    json_fixture, json_format = load_market_discovery_fixture(write_json(tmp_path, payload()))
    csv_fixture, csv_format = load_market_discovery_fixture(write_csv(tmp_path, payload()))

    assert json_fixture == csv_fixture
    assert json_fixture.rows[0].ticker == "ABC"
    assert json_format == "JSON"
    assert csv_format == "CSV"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["rows"][0].update(observed_at="2026-01-01T15:59:00"),
        lambda value: value["rows"][0].update(observed_at="2026-01-01T16:01:00+00:00"),
        lambda value: value["rows"].append(dict(value["rows"][0])),
        lambda value: value["rows"][0].update(average_volume_20d=0),
        lambda value: value["rows"][0].update(price=float("inf")),
        lambda value: value["rows"][0].pop("volume"),
        lambda value: value["scanner_config"].update(min_price_change_pct=0),
        lambda value: value.update(unknown=True),
    ],
)
def test_rejects_invalid_json_fixture(tmp_path, mutate):
    value = payload()
    mutate(value)
    with pytest.raises(ValueError):
        load_market_discovery_fixture(write_json(tmp_path, value))


def test_rejects_csv_header_and_repeated_config_mismatch(tmp_path):
    path = write_csv(tmp_path, payload(rows=[
        payload()["rows"][0],
        {**payload()["rows"][0], "ticker": "XYZ"},
    ]))
    lines = path.read_text(encoding="utf-8").splitlines()
    cells = lines[2].split(",")
    cells[2] = "2"
    lines[2] = ",".join(cells)
    path.write_text("\n".join(lines), encoding="utf-8")

    with pytest.raises(ValueError):
        load_market_discovery_fixture(path)

    path.write_text(path.read_text(encoding="utf-8").replace("ticker,", "symbol,", 1), encoding="utf-8")
    with pytest.raises(ValueError):
        load_market_discovery_fixture(path)


def test_csv_compares_repeated_as_of_after_strict_timestamp_parsing(tmp_path):
    path = write_csv(tmp_path, payload(rows=[
        payload()["rows"][0],
        {**payload()["rows"][0], "ticker": "XYZ"},
    ]))
    lines = path.read_text(encoding="utf-8").splitlines()
    cells = lines[2].split(",")
    cells[1] = "2026-01-01T16:00:00Z"
    lines[2] = ",".join(cells)
    path.write_text("\n".join(lines), encoding="utf-8")

    fixture, fixture_format = load_market_discovery_fixture(path)
    assert fixture_format == "CSV"
    assert len(fixture.rows) == 2


def test_rejects_unsupported_extension(tmp_path):
    path = tmp_path / "fixture.txt"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="extension"):
        load_market_discovery_fixture(path)
