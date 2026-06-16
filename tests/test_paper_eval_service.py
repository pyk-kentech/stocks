from stock_risk_mcp.paper_eval_service import load_paper_eval_report, run_paper_eval
from tests.test_paper_eval_fixture import fixture_payload, write


def test_paper_eval_service_writes_optional_json_output_only(tmp_path):
    fixture_file = write(tmp_path, "paper_eval_fixture.json", fixture_payload())
    output_file = tmp_path / "paper_eval_report.json"

    report = run_paper_eval(fixture_file, output_file=output_file)

    assert output_file.exists()
    assert report.metrics.trade_count == 1
    assert report.metadata_json["external_network_calls"] is False


def test_paper_eval_report_loader_round_trips_json(tmp_path):
    fixture_file = write(tmp_path, "paper_eval_fixture.json", fixture_payload())
    output_file = tmp_path / "paper_eval_report.json"
    created = run_paper_eval(fixture_file, output_file=output_file)
    loaded = load_paper_eval_report(output_file)
    assert loaded == created
