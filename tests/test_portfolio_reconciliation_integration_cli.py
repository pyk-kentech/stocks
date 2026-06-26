import json

from stock_risk_mcp.cli import run_command
from tests.test_account_read_models import account_read_payload
from tests.test_portfolio_reconciliation_engine import portfolio_reconciliation_payload


def portfolio_reconciliation_fixture_payload():
    return {
        "account_read_input": account_read_payload(),
        "reconciliation_input": portfolio_reconciliation_payload(),
    }


def test_portfolio_reconciliation_cli_reports_build_from_fixture(tmp_path):
    fixture_file = tmp_path / "portfolio_reconciliation_fixture.json"
    fixture_file.write_text(json.dumps(portfolio_reconciliation_fixture_payload()), encoding="utf-8")

    parser = __import__("stock_risk_mcp.cli", fromlist=["build_command_parser"]).build_command_parser()

    args = parser.parse_args(["account-read-snapshot-report", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert result["metadata"]["account_ref"].startswith("acct-redacted")

    args = parser.parse_args(["portfolio-reconciliation-report", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert result["dataset_id"] == "PAPER-EVALUATION-TEST"

    args = parser.parse_args(["portfolio-reconciliation-integration-report", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert result["account_snapshot_ready"] is True
