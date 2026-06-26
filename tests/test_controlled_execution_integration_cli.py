import json

from stock_risk_mcp.cli import run_command
from tests.test_controlled_execution_models import controlled_execution_payload


def test_controlled_execution_cli_reports_build_from_fixture(tmp_path):
    fixture_file = tmp_path / "controlled_execution_fixture.json"
    fixture_file.write_text(json.dumps(controlled_execution_payload()), encoding="utf-8")

    parser = __import__("stock_risk_mcp.cli", fromlist=["build_command_parser"]).build_command_parser()

    args = parser.parse_args(["controlled-execution-readiness-report", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert result["all_green"] is True

    args = parser.parse_args(["controlled-execution-approval-packet-report", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert result["order_draft_hash"].startswith("DRAFT-")

    args = parser.parse_args(["controlled-execution-mock-execution-report", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert result["accepted"] is True
