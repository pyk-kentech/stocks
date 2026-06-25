import json

from stock_risk_mcp.cli import main
from tests.test_kiwoom_rest_readonly_sector_models import kiwoom_rest_readonly_sector_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_kiwoom_rest_sector_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture_file = write(tmp_path / "kiwoom_rest_sector_fixture.json", kiwoom_rest_readonly_sector_payload())
    check = run(capsys, ["kiwoom-rest-sector-adapter-check", "--fixture-file", str(fixture_file)])
    request = run(capsys, ["kiwoom-rest-sector-request-report", "--fixture-file", str(fixture_file)])
    mocked = run(capsys, ["kiwoom-rest-sector-mocked-response-report", "--fixture-file", str(fixture_file)])
    leadership = run(capsys, ["kiwoom-rest-canonical-theme-leadership-report", "--fixture-file", str(fixture_file)])
    membership = run(capsys, ["kiwoom-rest-canonical-theme-membership-report", "--fixture-file", str(fixture_file)])
    etf = run(capsys, ["kiwoom-rest-canonical-etf-trend-report", "--fixture-file", str(fixture_file)])
    matrix = run(capsys, ["kiwoom-rest-sector-etf-capability-matrix-report", "--fixture-file", str(fixture_file)])
    continuation = run(capsys, ["kiwoom-rest-sector-continuation-report", "--fixture-file", str(fixture_file)])
    safety = run(capsys, ["kiwoom-rest-sector-readonly-safety-report", "--fixture-file", str(fixture_file)])
    integration = run(capsys, ["kiwoom-rest-sector-v7-integration-report", "--fixture-file", str(fixture_file)])
    gap = run(capsys, ["kiwoom-rest-sector-gap-report", "--fixture-file", str(fixture_file)])

    assert check["readiness"] in {"MOCKED_TRANSPORT_READY", "THEME_LEADERSHIP_READY", "THEME_MEMBERSHIP_READY", "ETF_TREND_READY", "SECTOR_CAPABILITY_MAPPED", "READONLY_ADAPTER_READY", "DATA_GAP", "SCHEMA_GAP", "FUTURE_SUPPORTED", "BLOCKED", "REJECTED"}
    for report in (request, mocked, leadership, membership, etf, matrix, continuation, safety, integration, gap):
        assert report["report_only"] is True


def test_kiwoom_rest_sector_cli_rejects_remote_or_parquet_or_missing(capsys, tmp_path):
    missing = run(capsys, ["kiwoom-rest-sector-adapter-check", "--fixture-file", str(tmp_path / "missing.json")])
    remote = run(capsys, ["kiwoom-rest-sector-request-report", "--fixture-file", "https://example.com/sector.json"])
    parquet = run(capsys, ["kiwoom-rest-sector-request-report", "--fixture-file", "sector.parquet"])
    assert missing["status"] == "FAILED"
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
