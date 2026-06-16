from stock_risk_mcp.local_model_benchmark_service import (
    load_local_model_benchmark_report,
    run_local_model_benchmark_cli,
    rank_local_model_candidates_from_report,
)
from tests.test_local_model_benchmark_fixture import (
    benchmark_fixture_payload,
    candidate_output_fixture_payload,
    write,
)


def test_local_model_benchmark_service_writes_optional_json_output(tmp_path):
    benchmark_file = write(tmp_path, "local_model_benchmark_fixture.json", benchmark_fixture_payload())
    candidate_file = write(tmp_path, "local_model_candidate_output_fixture.json", candidate_output_fixture_payload())
    output_file = tmp_path / "local_model_benchmark_report.json"
    report = run_local_model_benchmark_cli(benchmark_file, candidate_file, output_file=output_file)
    assert output_file.exists()
    assert report.metadata_json["benchmark_offline_only"] is True


def test_local_model_benchmark_report_loader_round_trips_json(tmp_path):
    benchmark_file = write(tmp_path, "local_model_benchmark_fixture.json", benchmark_fixture_payload())
    candidate_file = write(tmp_path, "local_model_candidate_output_fixture.json", candidate_output_fixture_payload())
    output_file = tmp_path / "local_model_benchmark_report.json"
    created = run_local_model_benchmark_cli(benchmark_file, candidate_file, output_file=output_file)
    loaded = load_local_model_benchmark_report(output_file)
    assert loaded == created


def test_local_model_candidates_rank_service_returns_ranked_eligible_candidates_only(tmp_path):
    benchmark_file = write(tmp_path, "local_model_benchmark_fixture.json", benchmark_fixture_payload())
    candidate_file = write(tmp_path, "local_model_candidate_output_fixture.json", candidate_output_fixture_payload())
    output_file = tmp_path / "local_model_benchmark_report.json"
    run_local_model_benchmark_cli(benchmark_file, candidate_file, output_file=output_file)
    ranked = rank_local_model_candidates_from_report(output_file)
    assert len(ranked) == 1
    assert ranked[0]["candidate_model_id"] == "mock-qwen-7b-q4"
