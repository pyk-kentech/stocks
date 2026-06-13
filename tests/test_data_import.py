import json
from datetime import date

from stock_risk_mcp.cli import main
from stock_risk_mcp.data_import import import_compliance_file, import_price_history_file, import_signal_file, run_unified_import
from stock_risk_mcp.import_run import ImportRunStatus, ImportSourceType
from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.repository import RiskRepository


def test_price_import_is_append_only_and_skips_db_and_file_duplicates(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    repository.save_price_bars([PriceBar(ticker="AAA", date=date(2026, 1, 1), close=10)])
    path = tmp_path / "prices.json"
    path.write_text(json.dumps([
        {"ticker": "AAA", "date": "2026-01-01", "close": 99},
        {"ticker": "BBB", "date": "2026-01-02", "close": 20},
        {"ticker": "BBB", "date": "2026-01-02", "close": 30},
        {"ticker": "BAD", "date": "not-a-date", "close": 1},
    ]), encoding="utf-8")

    result = import_price_history_file(repository, path)

    assert result.row_count == 4
    assert result.saved_count == 1
    assert result.skipped_duplicate_count == 2
    assert result.error_count == 1
    assert repository.get_all_price_history("AAA")[0].close == 10
    assert repository.get_all_price_history("BBB")[0].close == 20


def test_unified_import_records_partial_and_failed_runs(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    prices = tmp_path / "prices.csv"
    prices.write_text("ticker,date,close\nAAA,2026-01-01,10\n", encoding="utf-8")

    partial = run_unified_import(repository, price_history_file=prices, news_signal_file=tmp_path / "missing.csv")
    failed = run_unified_import(repository)

    assert partial.status == ImportRunStatus.PARTIAL
    assert failed.status == ImportRunStatus.FAILED
    assert repository.get_import_run(partial.import_run_id).status == ImportRunStatus.PARTIAL


def test_compliance_import_skips_duplicates_and_future_records(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    path = tmp_path / "compliance.json"
    path.write_text(json.dumps([
        {"ticker": "AAA", "notice_date": "2026-01-01", "issue": "Bid price"},
        {"ticker": "AAA", "notice_date": "2026-01-01", "issue": "Bid price"},
        {"ticker": "BBB", "notice_date": "2026-07-01", "issue": "Bid price"},
    ]), encoding="utf-8")

    first = import_compliance_file(repository, path, date(2026, 6, 13))
    second = import_compliance_file(repository, path, date(2026, 6, 13))

    assert first.saved_count == 1
    assert first.skipped_duplicate_count == 2
    assert second.saved_count == 0
    assert second.skipped_duplicate_count == 3


def test_signal_import_saves_valid_rows_and_skips_future_and_duplicate_rows(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    path = tmp_path / "news.json"
    path.write_text(json.dumps([
        {"ticker": "AAA", "observed_at": "2026-01-01", "title": "Contract", "event_type": "CONTRACT"},
        {"ticker": "AAA", "observed_at": "2026-01-01", "title": "Contract", "event_type": "CONTRACT"},
        {"ticker": "BBB", "observed_at": "2026-07-01", "title": "Future", "event_type": "CONTRACT"},
        {"ticker": "BAD", "observed_at": "not-a-date", "event_type": "CONTRACT"},
    ]), encoding="utf-8")

    result = import_signal_file(repository, path, ImportSourceType.NEWS_SIGNAL, date(2026, 6, 13))

    assert result.row_count == 4
    assert result.saved_count == 1
    assert result.skipped_duplicate_count == 2
    assert result.error_count == 1
    assert repository.count_rows("ticker_signals") == 1


def test_import_data_cli_and_run_inspection(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    prices = tmp_path / "prices.csv"
    prices.write_text("ticker,date,close\nAAA,2026-01-01,10\n", encoding="utf-8")

    imported = _run(capsys, ["import-data", "--db", str(db), "--price-history-file", str(prices)])
    listed = _run(capsys, ["import-runs", "--db", str(db)])
    shown = _run(capsys, ["import-show", "--db", str(db), "--import-run-id", imported["import_run_id"]])

    assert imported["status"] == "COMPLETED"
    assert listed["import_runs"][0]["import_run_id"] == imported["import_run_id"]
    assert shown["total_saved_count"] == 1


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)
