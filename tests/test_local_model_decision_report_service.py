import json

from stock_risk_mcp.local_model_decision_report_service import (
    load_local_model_decision_report,
    run_local_model_decision_report_cli,
    validate_local_model_benchmark_pack,
)
from tests.test_local_model_decision_report_fixture import (
    benchmark_pack_fixture_payload,
    benchmark_report_payload,
    write,
)


def test_local_model_decision_report_service_writes_optional_json_output(tmp_path):
    pack_file = write(tmp_path, "local_model_benchmark_pack_fixture.json", benchmark_pack_fixture_payload(report_files=["ko.json", "en.json", "mixed.json"]))
    write(tmp_path, "ko.json", benchmark_report_payload("ko", language_tags=["KOREAN"], domain_tags=["TECHNICAL_EVIDENCE"]))
    write(tmp_path, "en.json", benchmark_report_payload("en", language_tags=["ENGLISH"], domain_tags=["RISK_EXPLANATION"]))
    write(tmp_path, "mixed.json", benchmark_report_payload("mixed", language_tags=["MIXED"], domain_tags=["MISSING_DATA", "ASSUMPTION_CHALLENGE"]))
    output_file = tmp_path / "local_model_decision_report.json"
    decision = run_local_model_decision_report_cli(pack_file, output_file=output_file)
    assert output_file.exists()
    assert decision.metadata_json["decision_report_offline_only"] is True


def test_local_model_decision_report_loader_round_trips_json(tmp_path):
    pack_file = write(tmp_path, "local_model_benchmark_pack_fixture.json", benchmark_pack_fixture_payload(report_files=["ko.json", "en.json", "mixed.json"]))
    write(tmp_path, "ko.json", benchmark_report_payload("ko", language_tags=["KOREAN"], domain_tags=["TECHNICAL_EVIDENCE"]))
    write(tmp_path, "en.json", benchmark_report_payload("en", language_tags=["ENGLISH"], domain_tags=["RISK_EXPLANATION"]))
    write(tmp_path, "mixed.json", benchmark_report_payload("mixed", language_tags=["MIXED"], domain_tags=["MISSING_DATA", "ASSUMPTION_CHALLENGE"]))
    output_file = tmp_path / "local_model_decision_report.json"
    created = run_local_model_decision_report_cli(pack_file, output_file=output_file)
    loaded = load_local_model_decision_report(output_file)
    assert loaded == created


def test_local_model_benchmark_pack_validator_returns_expected_coverage_summary(tmp_path):
    pack_file = write(tmp_path, "local_model_benchmark_pack_fixture.json", benchmark_pack_fixture_payload(report_files=["ko.json", "en.json", "mixed.json"]))
    write(tmp_path, "ko.json", benchmark_report_payload("ko", language_tags=["KOREAN"], domain_tags=["TECHNICAL_EVIDENCE"]))
    write(tmp_path, "en.json", benchmark_report_payload("en", language_tags=["ENGLISH"], domain_tags=["RISK_EXPLANATION"]))
    write(tmp_path, "mixed.json", benchmark_report_payload("mixed", language_tags=["MIXED"], domain_tags=["MISSING_DATA", "ASSUMPTION_CHALLENGE"]))
    result = validate_local_model_benchmark_pack(pack_file)
    assert result["coverage_complete"] is True
    assert result["report_count"] == 3
