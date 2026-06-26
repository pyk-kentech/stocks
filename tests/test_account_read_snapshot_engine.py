from stock_risk_mcp.account_read_models import AccountReadPipelineInput
from stock_risk_mcp.account_read_snapshot_engine import build_account_read_snapshot_pipeline
from tests.test_account_read_models import account_read_payload


def test_account_read_snapshot_pipeline_builds_reports():
    result = build_account_read_snapshot_pipeline(AccountReadPipelineInput.model_validate(account_read_payload()), in_pytest=True)
    assert result.snapshot is not None
    assert result.snapshot.metadata.snapshot_id == "ACCOUNT-SNAPSHOT-TEST"
    assert result.freshness_report.stale is False
    assert result.completeness_report.average_cost_coverage == 1.0
    assert result.execution_decision.approved is False
