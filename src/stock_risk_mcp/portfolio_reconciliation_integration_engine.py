from __future__ import annotations

from stock_risk_mcp.account_read_models import AccountReadPipelineInput
from stock_risk_mcp.account_read_snapshot_engine import build_account_read_snapshot_pipeline
from stock_risk_mcp.portfolio_reconciliation_engine import build_portfolio_reconciliation
from stock_risk_mcp.portfolio_reconciliation_models import (
    PortfolioReconciliationPipelineInput,
    PortfolioReconciliationPipelineResult,
)


def build_portfolio_reconciliation_pipeline(
    account_read_input: AccountReadPipelineInput,
    reconciliation_input: PortfolioReconciliationPipelineInput,
    *,
    in_pytest: bool = False,
) -> PortfolioReconciliationPipelineResult:
    account_snapshot_result = build_account_read_snapshot_pipeline(account_read_input, in_pytest=in_pytest)
    pipeline_input = PortfolioReconciliationPipelineInput.model_validate(
        {
            **reconciliation_input.model_dump(mode="json"),
            "account_snapshot": account_snapshot_result.snapshot.model_dump(mode="json")
            if account_snapshot_result.snapshot
            else reconciliation_input.account_snapshot.model_dump(mode="json"),
        }
    )
    return build_portfolio_reconciliation(pipeline_input)
