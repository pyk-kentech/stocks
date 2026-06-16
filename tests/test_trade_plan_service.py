from stock_risk_mcp.trade_plan_service import load_trade_plan_report, run_trade_plan
from tests.test_trade_plan_fixture import candidate_payload, write


def test_trade_plan_service_writes_optional_json_output_only(tmp_path):
    fixture_file = write(tmp_path, "trade_plan_fixture.json", candidate_payload())
    output_file = tmp_path / "trade_plan_report.json"

    result = run_trade_plan(fixture_file, output_file=output_file)

    assert result.summary_counts["ready_count"] == 1
    assert output_file.exists()
    assert result.metadata_json["external_network_calls"] is False


def test_trade_plan_report_loader_round_trips_json(tmp_path):
    fixture_file = write(tmp_path, "trade_plan_fixture.json", candidate_payload())
    output_file = tmp_path / "trade_plan_report.json"

    created = run_trade_plan(fixture_file, output_file=output_file)
    loaded = load_trade_plan_report(output_file)

    assert loaded == created
