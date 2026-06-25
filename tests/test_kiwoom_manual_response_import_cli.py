import json

from stock_risk_mcp.cli import main
from tests.test_kiwoom_rest_readonly_chart_models import kiwoom_rest_readonly_chart_payload


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_manual_response_import_cli_commands_output_expected_reports(tmp_path, capsys):
    response_file = tmp_path / "ka10081_response.json"
    response_file.write_text(json.dumps(kiwoom_rest_readonly_chart_payload()["mocked_response_payload"]), encoding="utf-8")

    check = run(capsys, ["kiwoom-manual-response-import-check", "--api-id", "ka10081", "--file", str(response_file), "--symbol", "005930", "--canonical-instrument-key", "005930_KRX", "--available-at", "2026-06-25T15:35:00+09:00"])
    classification = run(capsys, ["kiwoom-manual-response-file-classification-report", "--api-id", "ka10081", "--file", str(response_file), "--symbol", "005930", "--canonical-instrument-key", "005930_KRX", "--available-at", "2026-06-25T15:35:00+09:00"])
    scan = run(capsys, ["kiwoom-manual-response-sensitive-scan-report", "--api-id", "ka10081", "--file", str(response_file), "--symbol", "005930", "--canonical-instrument-key", "005930_KRX", "--available-at", "2026-06-25T15:35:00+09:00"])
    routing = run(capsys, ["kiwoom-manual-response-routing-report", "--api-id", "ka10081", "--file", str(response_file), "--symbol", "005930", "--canonical-instrument-key", "005930_KRX", "--available-at", "2026-06-25T15:35:00+09:00"])
    canonical = run(capsys, ["kiwoom-manual-response-canonical-output-report", "--api-id", "ka10081", "--file", str(response_file), "--symbol", "005930", "--canonical-instrument-key", "005930_KRX", "--available-at", "2026-06-25T15:35:00+09:00"])
    snapshot = run(capsys, ["kiwoom-manual-response-snapshot-report", "--api-id", "ka10081", "--file", str(response_file), "--symbol", "005930", "--canonical-instrument-key", "005930_KRX", "--available-at", "2026-06-25T15:35:00+09:00", "--compose-snapshot"])
    safety = run(capsys, ["kiwoom-manual-response-safety-report", "--api-id", "ka10081", "--file", str(response_file), "--symbol", "005930", "--canonical-instrument-key", "005930_KRX", "--available-at", "2026-06-25T15:35:00+09:00"])
    gap = run(capsys, ["kiwoom-manual-response-gap-report", "--api-id", "ka10081", "--file", str(response_file), "--symbol", "005930", "--canonical-instrument-key", "005930_KRX", "--available-at", "2026-06-25T15:35:00+09:00"])

    assert check["readiness"] in {"PARSED_CANONICAL_READY", "SNAPSHOT_COMPOSED", "READONLY_SCHEMA_GAP", "CAPABILITY_ONLY", "DATA_GAP", "SCHEMA_GAP", "BLOCKED_SENSITIVE_CONTENT", "BLOCKED_ACCOUNT_API", "BLOCKED_ORDER_API", "BLOCKED_NETWORK_PATH", "BLOCKED_CREDENTIAL_PATH", "BLOCKED_UNSUPPORTED_FORMAT", "REJECTED"}
    for report in (classification, scan, routing, canonical, snapshot, safety, gap):
        assert report["report_only"] is True


def test_manual_response_import_cli_rejects_missing_remote_and_parquet(capsys, tmp_path):
    missing = run(capsys, ["kiwoom-manual-response-import-check", "--api-id", "ka10081", "--file", str(tmp_path / "missing.json")])
    remote = run(capsys, ["kiwoom-manual-response-import-check", "--api-id", "ka10081", "--file", "https://example.com/ka10081.json"])
    parquet = run(capsys, ["kiwoom-manual-response-import-check", "--api-id", "ka10081", "--file", "ka10081.parquet"])
    assert missing["readiness"] == "DATA_GAP"
    assert remote["readiness"] == "BLOCKED_NETWORK_PATH"
    assert parquet["readiness"] == "BLOCKED_UNSUPPORTED_FORMAT"
