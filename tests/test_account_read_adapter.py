from stock_risk_mcp.account_read_adapter import (
    build_account_read_provider_capability_report,
    build_account_read_request_preview,
)
from stock_risk_mcp.account_read_models import AccountReadPipelineInput
from tests.test_account_read_models import account_read_payload


def test_account_read_provider_capability_report_lists_preview_and_setup_gaps():
    report = build_account_read_provider_capability_report()
    assert any(row.provider == "KIWOOM" and row.exact_api_evidence_present for row in report.capability_rows)
    assert any(row.provider == "LS" and row.capability_status == "PROVIDER_SETUP_REQUIRED" for row in report.capability_rows)


def test_account_read_request_preview_is_read_only_and_non_executable():
    preview = build_account_read_request_preview(AccountReadPipelineInput.model_validate(account_read_payload()))
    assert preview.request_method == "GET"
    assert preview.can_execute_real_read is False
    assert preview.account_ref.startswith("acct-redacted")
