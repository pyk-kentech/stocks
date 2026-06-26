from stock_risk_mcp.paper_evaluation_integration_engine import build_paper_evaluation_pipeline
from stock_risk_mcp.paper_evaluation_models import PaperEvaluationPipelineInput
from tests.test_paper_evaluation_models import paper_evaluation_payload


def test_paper_evaluation_metrics_reports_compute_trade_and_split_outputs():
    result = build_paper_evaluation_pipeline(PaperEvaluationPipelineInput.model_validate(paper_evaluation_payload()))
    assert result.metrics_report.trade_count >= 0
    assert result.split_report.split_metrics
    assert result.regime_report.regime_metrics is not None
    assert result.event_window_report.event_window_metrics is not None
