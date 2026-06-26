import json

from stock_risk_mcp.cli import run_command
from tests.test_paper_evaluation_models import paper_evaluation_payload


def test_paper_evaluation_cli_reports_build_from_fixture(tmp_path):
    fixture_file = tmp_path / "paper_evaluation_fixture.json"
    fixture_file.write_text(json.dumps(paper_evaluation_payload()), encoding="utf-8")

    parser = __import__("stock_risk_mcp.cli", fromlist=["build_command_parser"]).build_command_parser()

    args = parser.parse_args(["paper-evaluation-plan-report", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert result["readiness_status"] == "PLAN_READY"

    args = parser.parse_args(["paper-evaluation-metrics-report", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert result["dataset_id"] == "PAPER-EVALUATION-TEST"

    args = parser.parse_args(["paper-evaluation-integration-report", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert result["v10_manifest_integration_ready"] is True

    args = parser.parse_args(["paper-evaluation-safety-report", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert "NO_MODEL_TRAINING" in result["findings"]
