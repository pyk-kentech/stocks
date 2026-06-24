import json

from stock_risk_mcp.cli import main
from tests.test_controlled_mock_readiness_models import controlled_mock_readiness_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture_file = write(tmp_path / "controlled_mock_readiness_fixture.json", controlled_mock_readiness_payload())
    check = run(capsys, ["controlled-mock-readiness-check", "--fixture-file", str(fixture_file)])
    summary = run(capsys, ["mock-readiness-summary-report", "--fixture-file", str(fixture_file)])
    dependency = run(capsys, ["mock-readiness-dependency-report", "--fixture-file", str(fixture_file)])
    evidence = run(capsys, ["paper-pass-evidence-report", "--fixture-file", str(fixture_file)])
    infra = run(capsys, ["mock-infrastructure-readiness-report", "--fixture-file", str(fixture_file)])
    safety = run(capsys, ["mock-safety-policy-report", "--fixture-file", str(fixture_file)])
    boundary = run(capsys, ["mock-boundary-violation-report", "--fixture-file", str(fixture_file)])
    gap = run(capsys, ["mock-readiness-gap-report", "--fixture-file", str(fixture_file)])
    assert check["decision"] in {"MOCK_REVIEW_READY", "MOCK_DRY_RUN_READY", "GAP", "BLOCKED", "RESEARCH_ONLY"}
    assert summary["report_only"] is True
    assert dependency["report_only"] is True
    assert evidence["report_only"] is True
    assert infra["report_only"] is True
    assert safety["report_only"] is True
    assert boundary["report_only"] is True
    assert gap["report_only"] is True


def test_cli_missing_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["controlled-mock-readiness-check", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_cli_rejects_remote_or_parquet_paths(capsys):
    remote = run(capsys, ["mock-readiness-summary-report", "--fixture-file", "https://example.com/mock.json"])
    parquet = run(capsys, ["mock-readiness-summary-report", "--fixture-file", "mock.parquet"])
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
