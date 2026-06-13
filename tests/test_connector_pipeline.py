import json
from datetime import date

from stock_risk_mcp.cli import main
from stock_risk_mcp.connector_pipeline import run_connectors, run_connectors_and_import
from stock_risk_mcp.connector_registry import ConnectorRegistry, default_connector_registry
from stock_risk_mcp.connector_run import ConnectorMode, ConnectorType
from stock_risk_mcp.repository import RiskRepository


class FailingConnector:
    name = "failing"
    connector_type = ConnectorType.NEWS
    mode = ConnectorMode.MOCK

    def fetch(self, as_of_date, output_dir, **kwargs):
        raise ValueError("expected connector failure")


def test_pipeline_persists_failures_and_continues(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    registry = default_connector_registry()
    registry.register_connector(FailingConnector())

    results = run_connectors(
        repository, registry, date(2026, 6, 13), tmp_path / "outputs",
        ["failing", "mock_news_signal"], ["AAA"],
    )

    assert [item.connector_run.status.value for item in results] == ["FAILED", "COMPLETED"]
    assert len(repository.list_connector_runs()) == 2


def test_no_outputs_still_creates_failed_import_run(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    registry = ConnectorRegistry()
    registry.register_connector(FailingConnector())

    report = run_connectors_and_import(
        repository, registry, date(2026, 6, 13), tmp_path / "outputs", ["failing"], ["AAA"],
    )

    assert report["overall_status"] == "FAILED"
    assert report["output_file_count"] == 0
    assert report["import_status"] == "FAILED"
    assert "no connector output files available for import" in repository.get_import_run(report["import_run_id"]).notes


def test_connector_cli_commands_and_import(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    output = tmp_path / "outputs"

    listed = _run(capsys, ["connectors"])
    result = _run(capsys, [
        "run-connectors-and-import", "--db", str(db), "--as-of-date", "2026-06-13",
        "--output-dir", str(output), "--connector", "mock_market_data", "--connector", "mock_news_signal",
        "--ticker", "AAA",
    ])
    runs = _run(capsys, ["connector-runs", "--db", str(db)])
    shown = _run(capsys, ["connector-show", "--db", str(db), "--connector-run-id", result["connector_runs"][0]["connector_run_id"]])

    assert listed["connectors"]
    assert result["overall_status"] == "COMPLETED"
    assert result["import_status"] == "COMPLETED"
    assert runs["connector_runs"]
    assert shown["connector_name"] == "mock_market_data"


def test_connector_cli_returns_failed_json_when_all_connectors_fail(tmp_path, capsys) -> None:
    result = _run(capsys, [
        "run-connectors-and-import", "--db", str(tmp_path / "risk.sqlite3"),
        "--as-of-date", "2026-06-13", "--output-dir", str(tmp_path / "outputs"),
        "--connector", "missing_connector",
    ])

    assert result["overall_status"] == "FAILED"
    assert result["status"] == "FAILED"
    assert result["output_file_count"] == 0
    assert result["import_run_id"]
    assert result["connector_error_summary"][0]["status"] == "FAILED"


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)
