from stock_risk_mcp.controlled_execution_adapter import build_controlled_execution_adapter_capability_report
from stock_risk_mcp.controlled_execution_models import ControlledExecutionPipelineInput
from tests.test_controlled_execution_models import controlled_execution_payload


def test_controlled_execution_adapter_report_exposes_mock_and_dry_run_and_blocked_live():
    report = build_controlled_execution_adapter_capability_report(
        ControlledExecutionPipelineInput.model_validate(controlled_execution_payload(provider="KIWOOM"))
    )
    assert any(row.provider == "LOCAL_MOCK" and row.adapter_status == "MOCK_READY" for row in report.adapter_rows)
    assert any(row.provider == "KIWOOM" and row.exact_schema_evidence_present for row in report.adapter_rows)
    assert report.blocked_submit_preview["blocked"] is True
