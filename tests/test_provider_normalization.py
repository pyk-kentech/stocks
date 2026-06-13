import json
from datetime import date

from stock_risk_mcp.cli import main
from stock_risk_mcp.normalize_run import NormalizeRunStatus
from stock_risk_mcp.provider_normalization import normalize_sources
from stock_risk_mcp.repository import RiskRepository


def test_normalize_sources_isolates_failure_and_can_import(tmp_path, capsys) -> None:
    prices = tmp_path / "prices.csv"
    prices.write_text("Symbol,Day,Close,Volume\nAAA,2026-06-12,10,100\n", encoding="utf-8")
    config = {"sources": [
        {"normalizer": "generic-price-csv", "input_file": str(prices), "output_name": "prices.csv",
         "columns": {"ticker": "Symbol", "date": "Day", "close": "Close", "volume": "Volume"}},
        {"normalizer": "generic-news-csv", "input_file": str(tmp_path / "missing.csv"),
         "columns": {"ticker": "ticker", "observed_at": "observed_at"}},
    ]}
    repository = RiskRepository(tmp_path / "risk.sqlite3")

    run, imported = normalize_sources(
        config["sources"], tmp_path / "out", date(2026, 6, 13), repository=repository,
        save=True, import_outputs=True,
    )

    assert run.status == NormalizeRunStatus.PARTIAL
    assert imported is not None
    assert repository.get_all_price_history("AAA")
    assert repository.get_normalize_run(run.normalize_run_id).status == NormalizeRunStatus.PARTIAL

    config_file = tmp_path / "normalizers.json"
    config_file.write_text(json.dumps({"sources": [config["sources"][0]]}), encoding="utf-8")
    cli = _run(capsys, [
        "normalize-and-import", "--db", str(tmp_path / "cli.sqlite3"), "--config-file", str(config_file),
        "--output-dir", str(tmp_path / "cli-out"), "--as-of-date", "2026-06-13",
    ])
    assert cli["normalize_run_id"]
    assert cli["import_run_id"]


def test_normalize_sources_reports_no_input_and_failed(tmp_path) -> None:
    no_input, _ = normalize_sources([], tmp_path / "out")
    failed, _ = normalize_sources(
        [{"normalizer": "missing", "input_file": "missing.csv"}], tmp_path / "out",
    )

    assert no_input.status == NormalizeRunStatus.NO_INPUT
    assert failed.status == NormalizeRunStatus.FAILED


def test_normalize_and_import_stores_fx_output(tmp_path) -> None:
    raw = tmp_path / "fx.csv"
    raw.write_text("base,quote,day,value\nUSD,KRW,2026-06-12,1350\n", encoding="utf-8")
    repository = RiskRepository(tmp_path / "risk.sqlite3")

    run, imported = normalize_sources(
        [{
            "normalizer": "generic-fx-csv", "input_file": str(raw), "output_name": "fx.csv",
            "columns": {"base_currency": "base", "quote_currency": "quote", "date": "day", "rate": "value"},
        }],
        tmp_path / "out", date(2026, 6, 13), repository=repository, import_outputs=True,
    )

    assert run.status == NormalizeRunStatus.COMPLETED
    assert imported.status.value == "COMPLETED"
    assert repository.get_latest_fx_rate("USD", "KRW")["rate"] == 1350


def test_normalize_and_import_uses_all_outputs_of_same_type(tmp_path) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    first.write_text("Symbol,Day,Close,Volume\nAAA,2026-06-12,10,100\n", encoding="utf-8")
    second.write_text("Symbol,Day,Close,Volume\nBBB,2026-06-12,20,200\n", encoding="utf-8")
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    sources = [
        {
            "normalizer": "generic-price-csv", "input_file": str(path), "output_name": f"{path.stem}.csv",
            "columns": {"ticker": "Symbol", "date": "Day", "close": "Close", "volume": "Volume"},
        }
        for path in (first, second)
    ]

    _, imported = normalize_sources(
        sources, tmp_path / "out", date(2026, 6, 13), repository=repository, import_outputs=True,
    )

    assert imported.total_saved_count == 2
    assert repository.get_all_price_history("AAA")
    assert repository.get_all_price_history("BBB")


def test_normalize_file_and_inspection_cli(tmp_path, capsys) -> None:
    raw = tmp_path / "prices.csv"
    raw.write_text("Symbol,Day,Close,Volume\nAAA,2026-06-12,10,100\n", encoding="utf-8")
    db = tmp_path / "risk.sqlite3"

    result = _run(capsys, [
        "normalize-file", "--db", str(db), "--normalizer", "generic-price-csv",
        "--input-file", str(raw), "--output-dir", str(tmp_path / "out"), "--as-of-date", "2026-06-13",
        "--ticker-column", "Symbol", "--date-column", "Day", "--close-column", "Close",
        "--volume-column", "Volume", "--save",
    ])
    listed = _run(capsys, ["normalize-runs", "--db", str(db)])
    shown = _run(capsys, ["normalize-show", "--db", str(db), "--normalize-run-id", result["normalize_run_id"]])

    assert result["status"] == "COMPLETED"
    assert listed["normalize_runs"]
    assert shown["normalize_run_id"] == result["normalize_run_id"]


def test_normalize_run_cli_processes_config_without_import(tmp_path, capsys) -> None:
    raw = tmp_path / "prices.csv"
    raw.write_text("Symbol,Day,Close,Volume\nAAA,2026-06-12,10,100\n", encoding="utf-8")
    config = tmp_path / "normalizers.json"
    config.write_text(json.dumps({"sources": [{
        "normalizer": "generic-price-csv", "input_file": str(raw),
        "columns": {"ticker": "Symbol", "date": "Day", "close": "Close", "volume": "Volume"},
    }]}), encoding="utf-8")

    result = _run(capsys, [
        "normalize-run", "--db", str(tmp_path / "risk.sqlite3"), "--config-file", str(config),
        "--output-dir", str(tmp_path / "out"), "--as-of-date", "2026-06-13",
    ])

    assert result["status"] == "COMPLETED"
    assert result["import_run_id"] is None


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)
