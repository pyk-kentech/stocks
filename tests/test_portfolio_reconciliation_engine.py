from stock_risk_mcp.account_read_models import AccountReadPipelineInput
from stock_risk_mcp.paper_evaluation_integration_engine import build_paper_evaluation_pipeline
from stock_risk_mcp.paper_evaluation_models import PaperEvaluationPipelineInput
from stock_risk_mcp.portfolio_reconciliation_engine import build_portfolio_reconciliation
from stock_risk_mcp.portfolio_reconciliation_models import PortfolioReconciliationPipelineInput
from tests.test_account_read_models import account_read_payload
from tests.test_paper_evaluation_models import paper_evaluation_payload


def portfolio_reconciliation_payload():
    paper = build_paper_evaluation_pipeline(PaperEvaluationPipelineInput.model_validate(paper_evaluation_payload()))
    account_input = AccountReadPipelineInput.model_validate(account_read_payload())
    return {
        "pipeline_id": "portfolio-reconciliation-test",
        "dataset_id": "paper-evaluation-test",
        "paper_evaluation": paper.model_dump(mode="json"),
        "account_snapshot": account_input.snapshot_fixture.model_dump(mode="json"),
        "target_positions": [{"instrument_id": "005930", "market": "KRX", "currency": "KRW", "quantity": 1.0, "target_weight": 1.0}],
        "audit_records": [
            {
                "audit_record_id": "portfolio-reconciliation-audit-test",
                "created_at": "2026-06-26T16:35:00+09:00",
                "source_path": "fixtures/reconciliation/portfolio_reconciliation_fixture.json",
                "operator_context": "offline reconciliation unit test",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
        "evaluated_at": "2026-06-26T16:35:00+09:00",
    }


def test_portfolio_reconciliation_builds_dual_view_report():
    result = build_portfolio_reconciliation(PortfolioReconciliationPipelineInput.model_validate(portfolio_reconciliation_payload()))
    assert result.plan_report.target_positions_supplied is True
    assert result.reconciliation_report.paper_vs_account_mismatch_count >= 0
    assert result.integration_report.account_snapshot_ready is True
    assert result.safety_report.no_order is True
