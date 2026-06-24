import json

from stock_risk_mcp.cli import main
from tests.test_kiwoom_rest_readonly_rank_models import kiwoom_rest_readonly_rank_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_kiwoom_rest_rank_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture_file = write(tmp_path / "kiwoom_rest_rank_fixture.json", kiwoom_rest_readonly_rank_payload())
    check = run(capsys, ["kiwoom-rest-rank-adapter-check", "--fixture-file", str(fixture_file)])
    request = run(capsys, ["kiwoom-rest-rank-request-report", "--fixture-file", str(fixture_file)])
    mocked = run(capsys, ["kiwoom-rest-rank-mocked-response-report", "--fixture-file", str(fixture_file)])
    canonical_rank = run(capsys, ["kiwoom-rest-canonical-rank-report", "--fixture-file", str(fixture_file)])
    canonical_outlier = run(capsys, ["kiwoom-rest-canonical-outlier-report", "--fixture-file", str(fixture_file)])
    continuation = run(capsys, ["kiwoom-rest-rank-continuation-report", "--fixture-file", str(fixture_file)])
    safety = run(capsys, ["kiwoom-rest-rank-readonly-safety-report", "--fixture-file", str(fixture_file)])
    integration = run(capsys, ["kiwoom-rest-rank-v7-integration-report", "--fixture-file", str(fixture_file)])
    gap = run(capsys, ["kiwoom-rest-rank-gap-report", "--fixture-file", str(fixture_file)])

    assert check["readiness"] in {"MOCKED_TRANSPORT_READY", "CANONICAL_RANK_READY", "CANONICAL_OUTLIER_READY", "READONLY_ADAPTER_READY", "DATA_GAP", "SCHEMA_GAP", "BLOCKED", "REJECTED"}
    for report in (request, mocked, canonical_rank, canonical_outlier, continuation, safety, integration, gap):
        assert report["report_only"] is True


def test_kiwoom_rest_rank_cli_rejects_remote_or_parquet_or_missing(capsys, tmp_path):
    missing = run(capsys, ["kiwoom-rest-rank-adapter-check", "--fixture-file", str(tmp_path / "missing.json")])
    remote = run(capsys, ["kiwoom-rest-rank-request-report", "--fixture-file", "https://example.com/rank.json"])
    parquet = run(capsys, ["kiwoom-rest-rank-request-report", "--fixture-file", "rank.parquet"])
    assert missing["status"] == "FAILED"
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
