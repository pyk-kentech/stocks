import json

from stock_risk_mcp.cli import run_command
from tests.test_feature_store_models import feature_store_payload


def test_feature_store_cli_reports_build_from_fixture(tmp_path):
    fixture_file = tmp_path / "feature_store_fixture.json"
    fixture_file.write_text(json.dumps(feature_store_payload(store_root=str(tmp_path / "feature_store"))), encoding="utf-8")

    parser = __import__("stock_risk_mcp.cli", fromlist=["build_command_parser"]).build_command_parser()

    args = parser.parse_args(["feature-store-training-dataset-manifest-build", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert result["readiness_status"] == "LABELED_DATASET_READY"

    args = parser.parse_args(["feature-store-v7-integration-report", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert result["v71_point_in_time_universe_ready"] is True

    args = parser.parse_args(["feature-store-v8-integration-report", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert result["local_kiwoom_chart_label_source_ready"] is True

    args = parser.parse_args(["feature-store-v9-integration-report", "--fixture-file", str(fixture_file)])
    result = run_command(args)
    assert result["macro_snapshot_feature_ready"] is True
