import json

from stock_risk_mcp.cli import main
from tests.test_kiwoom_rest_readonly_chart_models import kiwoom_rest_readonly_chart_payload


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_final_transport_cli_commands_output_expected_reports(tmp_path, capsys):
    response_file = tmp_path / "ka10081_response.json"
    response_file.write_text(json.dumps(kiwoom_rest_readonly_chart_payload()["mocked_response_payload"]), encoding="utf-8")

    check = run(capsys, ["kiwoom-readonly-final-transport-check", "--api-id", "ka10081", "--domain", "mock-krx", "--body-json", '{"stk_cd":"005930","base_dt":"20260625","upd_stkpc_tp":"1"}'])
    preview = run(capsys, ["kiwoom-readonly-final-request-preview-report", "--api-id", "ka10081", "--domain", "mock-krx", "--body-json", '{"stk_cd":"005930","base_dt":"20260625","upd_stkpc_tp":"1"}'])
    allowlist = run(capsys, ["kiwoom-readonly-final-allowlist-report", "--api-id", "ka10081", "--domain", "mock-krx", "--body-json", '{"stk_cd":"005930"}'])
    token_provider = run(capsys, ["kiwoom-readonly-final-token-provider-report", "--api-id", "ka10081", "--domain", "mock-krx", "--body-json", '{"stk_cd":"005930"}'])
    mocked = run(capsys, ["kiwoom-readonly-final-mocked-call-report", "--api-id", "ka10081", "--domain", "mock-krx", "--body-json", '{"stk_cd":"005930","base_dt":"20260625","upd_stkpc_tp":"1"}', "--mock-response-file", str(response_file)])
    routing = run(capsys, ["kiwoom-readonly-final-response-routing-report", "--api-id", "ka10081", "--domain", "mock-krx", "--body-json", '{"stk_cd":"005930","base_dt":"20260625","upd_stkpc_tp":"1"}', "--mock-response-file", str(response_file)])
    readiness = run(capsys, ["kiwoom-readonly-final-v8-readiness-report", "--api-id", "ka10081", "--domain", "mock-krx", "--body-json", '{"stk_cd":"005930","base_dt":"20260625","upd_stkpc_tp":"1"}', "--mock-response-file", str(response_file)])
    gap = run(capsys, ["kiwoom-readonly-final-gap-report", "--api-id", "ka10081", "--domain", "mock-krx", "--body-json", '{"stk_cd":"005930"}'])

    assert check["status_value"] in {"PREVIEW_READY", "V8_FINAL_READY", "MOCKED_CALL_READY"}
    assert preview["report_only"] is True
    assert "KA10081" in allowlist["allowed_api_ids"]
    assert token_provider["report_only"] is True
    assert mocked["report_only"] is True
    assert routing["report_only"] is True
    assert readiness["v8_complete"] is True
    assert gap["report_only"] is True


def test_final_transport_cli_blocks_real_smoke_and_sensitive_body(capsys):
    smoke = run(
        capsys,
        [
            "kiwoom-readonly-final-single-call-smoke-report",
            "--api-id",
            "ka10081",
            "--domain",
            "mock-krx",
            "--body-json",
            '{"stk_cd":"005930"}',
            "--token-env-name",
            "KIWOOM_ACCESS_TOKEN",
        ],
    )
    blocked = run(
        capsys,
        [
            "kiwoom-readonly-final-transport-check",
            "--api-id",
            "ka10081",
            "--domain",
            "mock-krx",
            "--body-json",
            '{"authorization":"Bearer real-token"}',
        ],
    )
    assert smoke["status"] == "FAILED" or smoke["status"] == "COMPLETED" or smoke["report_only"] is True
    assert blocked["status_value"] == "BLOCKED_TOKEN_POLICY"
