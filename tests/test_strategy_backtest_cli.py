import json

from stock_risk_mcp.cli import main
from tests.test_strategy_backtest_fixture import payload


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_strategy_backtest_run_list_show_cli(tmp_path, capsys) -> None:
    fixture = tmp_path / "backtest.json"
    fixture.write_text(json.dumps(payload()), encoding="utf-8")
    db = tmp_path / "risk.sqlite3"

    result = run(capsys, ["strategy-backtest-run", "--db", str(db), "--fixture-file", str(fixture)])
    reports = run(capsys, ["strategy-backtest-reports", "--db", str(db)])
    shown = run(capsys, ["strategy-backtest-show", "--db", str(db), "--report-id", result["report"]["report_id"]])

    assert result["run"]["status"] == "COMPLETED"
    assert reports["reports"]
    assert shown["metric"]["trade_count"] == 1
    assert "secret" not in json.dumps([result, reports, shown]).lower()


def test_strategy_backtest_invalid_fixture_is_json_safe(tmp_path, capsys) -> None:
    result = run(capsys, [
        "strategy-backtest-run", "--db", str(tmp_path / "risk.sqlite3"),
        "--fixture-file", str(tmp_path / "missing.json"),
    ])
    assert result["status"] == "FAILED"
    assert result["errors"]
