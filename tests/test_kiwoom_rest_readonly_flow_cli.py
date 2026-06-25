import json

from stock_risk_mcp.cli import main
from tests.test_kiwoom_rest_readonly_flow_models import kiwoom_rest_readonly_flow_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_kiwoom_rest_flow_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture_file = write(tmp_path / "kiwoom_rest_flow_fixture.json", kiwoom_rest_readonly_flow_payload())
    check = run(capsys, ["kiwoom-rest-flow-adapter-check", "--fixture-file", str(fixture_file)])
    request = run(capsys, ["kiwoom-rest-flow-request-report", "--fixture-file", str(fixture_file)])
    mocked = run(capsys, ["kiwoom-rest-flow-mocked-response-report", "--fixture-file", str(fixture_file)])
    investor = run(capsys, ["kiwoom-rest-canonical-investor-flow-report", "--fixture-file", str(fixture_file)])
    program = run(capsys, ["kiwoom-rest-canonical-program-flow-report", "--fixture-file", str(fixture_file)])
    short_lending = run(capsys, ["kiwoom-rest-short-lending-capability-report", "--fixture-file", str(fixture_file)])
    matrix = run(capsys, ["kiwoom-rest-flow-capability-matrix-report", "--fixture-file", str(fixture_file)])
    continuation = run(capsys, ["kiwoom-rest-flow-continuation-report", "--fixture-file", str(fixture_file)])
    safety = run(capsys, ["kiwoom-rest-flow-readonly-safety-report", "--fixture-file", str(fixture_file)])
    integration = run(capsys, ["kiwoom-rest-flow-v7-integration-report", "--fixture-file", str(fixture_file)])
    gap = run(capsys, ["kiwoom-rest-flow-gap-report", "--fixture-file", str(fixture_file)])

    assert check["readiness"] in {"MOCKED_TRANSPORT_READY", "CANONICAL_FLOW_READY", "INVESTOR_FLOW_READY", "PROGRAM_FLOW_READY", "SHORT_LENDING_CAPABILITY_MAPPED", "READONLY_ADAPTER_READY", "DATA_GAP", "SCHEMA_GAP", "FUTURE_SUPPORTED", "BLOCKED", "REJECTED"}
    for report in (request, mocked, investor, program, short_lending, matrix, continuation, safety, integration, gap):
        assert report["report_only"] is True


def test_kiwoom_rest_flow_cli_rejects_remote_or_parquet_or_missing(capsys, tmp_path):
    missing = run(capsys, ["kiwoom-rest-flow-adapter-check", "--fixture-file", str(tmp_path / "missing.json")])
    remote = run(capsys, ["kiwoom-rest-flow-request-report", "--fixture-file", "https://example.com/flow.json"])
    parquet = run(capsys, ["kiwoom-rest-flow-request-report", "--fixture-file", "flow.parquet"])
    assert missing["status"] == "FAILED"
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
