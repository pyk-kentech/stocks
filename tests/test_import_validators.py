import json

from stock_risk_mcp.import_validators import load_import_records


def test_load_import_records_validates_extension_and_required_columns(tmp_path) -> None:
    valid = tmp_path / "rows.json"
    valid.write_text(json.dumps([{"ticker": "AAA", "date": "2026-01-01"}]), encoding="utf-8")
    missing = tmp_path / "missing.csv"
    missing.write_text("ticker\nAAA\n", encoding="utf-8")

    records = load_import_records(valid, {"ticker", "date"})

    assert records == [{"ticker": "AAA", "date": "2026-01-01"}]
    try:
        load_import_records(missing, {"ticker", "date"})
    except ValueError as error:
        assert "required columns" in str(error)
    else:
        raise AssertionError("missing required columns should fail")
