import json

from stock_risk_mcp.connector_outputs import count_output_rows, write_csv_output


def test_connector_output_writes_csv_and_counts_rows(tmp_path) -> None:
    path = tmp_path / "out.csv"
    write_csv_output(path, [{"ticker": "AAA", "value": 1}, {"ticker": "BBB", "value": 2}])

    assert count_output_rows(path) == 2
    assert path.read_text(encoding="utf-8").splitlines()[0] == "ticker,value"


def test_connector_output_counts_json_mapping_records(tmp_path) -> None:
    path = tmp_path / "out.json"
    path.write_text(json.dumps({"AAA": {"ticker": "AAA"}, "BBB": {"ticker": "BBB"}}), encoding="utf-8")

    assert count_output_rows(path) == 2
