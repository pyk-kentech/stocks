import json

from stock_risk_mcp.cli import main
from tests.test_kiwoom_rest_readonly_chart_models import kiwoom_rest_readonly_chart_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_kiwoom_rest_chart_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture_file = write(tmp_path / "kiwoom_rest_chart_fixture.json", kiwoom_rest_readonly_chart_payload())
    check = run(capsys, ["kiwoom-rest-chart-adapter-check", "--fixture-file", str(fixture_file)])
    request = run(capsys, ["kiwoom-rest-chart-request-report", "--fixture-file", str(fixture_file)])
    mocked = run(capsys, ["kiwoom-rest-chart-mocked-response-report", "--fixture-file", str(fixture_file)])
    canonical = run(capsys, ["kiwoom-rest-canonical-ohlcv-report", "--fixture-file", str(fixture_file)])
    continuation = run(capsys, ["kiwoom-rest-chart-continuation-report", "--fixture-file", str(fixture_file)])
    safety = run(capsys, ["kiwoom-rest-chart-readonly-safety-report", "--fixture-file", str(fixture_file)])
    integration = run(capsys, ["kiwoom-rest-chart-integration-compatibility-report", "--fixture-file", str(fixture_file)])
    gap = run(capsys, ["kiwoom-rest-chart-gap-report", "--fixture-file", str(fixture_file)])

    assert check["readiness"] in {"MOCKED_TRANSPORT_READY", "CANONICAL_OHLCV_READY", "READONLY_ADAPTER_READY", "DATA_GAP", "SCHEMA_GAP", "BLOCKED", "REJECTED"}
    for report in (request, mocked, canonical, continuation, safety, integration, gap):
        assert report["report_only"] is True


def test_kiwoom_rest_chart_cli_rejects_remote_or_parquet_or_missing(capsys, tmp_path):
    missing = run(capsys, ["kiwoom-rest-chart-adapter-check", "--fixture-file", str(tmp_path / "missing.json")])
    remote = run(capsys, ["kiwoom-rest-chart-request-report", "--fixture-file", "https://example.com/chart.json"])
    parquet = run(capsys, ["kiwoom-rest-chart-request-report", "--fixture-file", "chart.parquet"])
    assert missing["status"] == "FAILED"
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
