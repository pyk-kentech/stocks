import json

from stock_risk_mcp.cli import main
from tests.test_local_model_decision_report_fixture import (
    benchmark_pack_fixture_payload,
    benchmark_report_payload,
    write,
)


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_local_model_decision_report_commands_return_json_safe_outputs(tmp_path, capsys):
    pack_file = write(tmp_path, "local_model_benchmark_pack_fixture.json", benchmark_pack_fixture_payload(report_files=["ko.json", "en.json", "mixed.json"]))
    write(tmp_path, "ko.json", benchmark_report_payload("ko", language_tags=["KOREAN"], domain_tags=["TECHNICAL_EVIDENCE"]))
    write(tmp_path, "en.json", benchmark_report_payload("en", language_tags=["ENGLISH"], domain_tags=["RISK_EXPLANATION"]))
    write(tmp_path, "mixed.json", benchmark_report_payload("mixed", language_tags=["MIXED"], domain_tags=["MISSING_DATA", "ASSUMPTION_CHALLENGE"]))
    output_file = tmp_path / "local_model_decision_report.json"
    summary = run(capsys, ["local-model-decision-report", "--pack-file", str(pack_file), "--output-file", str(output_file)])
    validated = run(capsys, ["local-model-benchmark-pack-validate", "--pack-file", str(pack_file)])
    assert summary["status"] == "COMPLETED"
    assert validated["coverage_complete"] is True


def test_local_model_decision_report_invalid_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["local-model-decision-report", "--pack-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]
