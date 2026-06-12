import json
from datetime import date, timedelta

from stock_risk_mcp.cli import main
from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.repository import RiskRepository


def test_candidate_scan_cli_commands(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    repository = RiskRepository(db)
    repository.save_price_bars(_bars())

    scan = _run(capsys, [
        "scan-candidates", "--db", str(db), "--as-of-date", "2026-01-20",
        "--ticker", "AAA", "--max-candidates", "1", "--save",
    ])
    runs = _run(capsys, ["scan-runs", "--db", str(db)])
    results = _run(capsys, ["scan-results", "--db", str(db), "--scan-run-id", scan["scan_run_id"]])
    basket = _run(capsys, [
        "scan-to-basket", "--db", str(db), "--scan-run-id", scan["scan_run_id"],
        "--account-equity", "10000", "--cash-available", "5000",
    ])
    replay = _run(capsys, [
        "scan-to-replay-snapshot", "--db", str(db), "--scan-run-id", scan["scan_run_id"],
        "--as-of-date", "2026-01-20",
    ])

    assert scan["saved"] is True
    assert runs["scan_runs"][0]["scan_run_id"] == scan["scan_run_id"]
    assert results["results"][0]["ticker"] == "AAA"
    assert basket["saved_to_basket_plans"] is False
    assert repository.count_rows("basket_plans") == 0
    assert replay["source_type"] == "SCAN_RUN"


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def _bars():
    start = date(2025, 9, 1)
    return [
        PriceBar(
            ticker="AAA",
            date=start + timedelta(days=index),
            open=10 + index * .1,
            high=11 + index * .1,
            low=9.5 + index * .1,
            close=10.5 + index * .1,
            volume=5_000_000 + index * 100_000,
        )
        for index in range(140)
    ]
