import json
from datetime import date

from stock_risk_mcp.cli import main
from stock_risk_mcp.repository import RiskRepository
from tests.test_operational_pipeline import _bars
from tests.test_operational_pipeline import _replay


def test_operational_pipeline_cli_commands(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    repository = RiskRepository(db)
    for ticker in ("AAA", "BBB", "CCC"):
        repository.save_price_bars(_bars(ticker))
    for index in range(5):
        repository.save_policy_replay_result(_replay(f"r{index}", "v1", 50, 1))
        repository.save_policy_replay_result(_replay(f"r{index}", "v2", 56, 3))

    scan = _run(capsys, ["run-scan-pipeline", "--db", str(db), "--as-of-date", "2026-01-20"])
    paper = _run(capsys, [
        "run-paper-pipeline", "--db", str(db), "--as-of-date", "2026-01-20",
        "--account-equity", "10000", "--cash-available", "5000", "--horizon-days", "10",
    ])
    runs = _run(capsys, ["pipeline-runs", "--db", str(db)])
    shown = _run(capsys, ["pipeline-show", "--db", str(db), "--pipeline-run-id", paper["pipeline_run_id"]])
    alerts = _run(capsys, ["alerts", "--db", str(db), "--pipeline-run-id", scan["pipeline_run_id"]])
    watched = _run(capsys, [
        "watch-loop", "--db", str(db), "--as-of-date", "2026-01-20",
        "--account-equity", "10000", "--cash-available", "5000",
        "--interval-seconds", "0", "--max-iterations", "1", "--no-paper-trade",
    ])
    policy = _run(capsys, [
        "run-policy-evaluation-pipeline", "--db", str(db),
        "--baseline-policy-id", "default", "--baseline-policy-version", "v1",
        "--candidate-policy-id", "default", "--candidate-policy-version", "v2",
        "--horizon-days", "10", "--account-equity", "10000", "--cash-available", "5000",
        *[value for index in range(5) for value in ("--replay-run-id", f"r{index}")],
    ])

    assert scan["scan_run_id"] is not None
    assert paper["paper_result_persisted"] is False
    assert paper["basket_saved_to_basket_plans"] is False
    assert runs["pipeline_runs"]
    assert shown["run"]["pipeline_run_id"] == paper["pipeline_run_id"]
    assert "alerts" in alerts
    assert len(watched["iterations"]) == 1
    assert policy["policy_recommendation"] == "ACCEPT"


def test_paper_pipeline_notify_records_notification_without_changing_pipeline_status(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    repository = RiskRepository(db)
    for ticker in ("AAA", "BBB", "CCC"):
        repository.save_price_bars(_bars(ticker))

    result = _run(capsys, [
        "run-paper-pipeline", "--db", str(db), "--as-of-date", "2026-01-20",
        "--account-equity", "10000", "--cash-available", "5000", "--horizon-days", "10",
        "--notify", "--notification-channel", "mock", "--notification-min-severity", "info",
    ])
    run = repository.get_pipeline_run(result["pipeline_run_id"])

    assert result["notification_run_id"]
    assert any(result["notification_run_id"] in note for note in run.notes)
    assert run.status.value == result["status"]


def test_paper_pipeline_notification_failure_does_not_change_pipeline_status(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    bad_output = tmp_path / "existing-directory"
    bad_output.mkdir()
    repository = RiskRepository(db)
    for ticker in ("AAA", "BBB", "CCC"):
        repository.save_price_bars(_bars(ticker))

    result = _run(capsys, [
        "run-paper-pipeline", "--db", str(db), "--as-of-date", "2026-01-20",
        "--account-equity", "10000", "--cash-available", "5000", "--horizon-days", "10",
        "--notify", "--notification-channel", "local-file", "--notification-output-file", str(bad_output),
    ])
    run = repository.get_pipeline_run(result["pipeline_run_id"])

    assert result["notification_status"] == "FAILED"
    assert run.status.value == result["status"]


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)
