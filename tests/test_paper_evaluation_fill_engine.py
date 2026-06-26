from stock_risk_mcp.paper_evaluation_fill_engine import build_paper_evaluation_fills
from stock_risk_mcp.paper_evaluation_models import (
    PaperEvaluationFillStatus,
    PaperEvaluationPipelineInput,
)
from stock_risk_mcp.paper_evaluation_signal_engine import build_paper_evaluation_signals
from tests.test_paper_evaluation_models import paper_evaluation_payload


def test_paper_evaluation_fill_engine_uses_next_bar_fill():
    pipeline = PaperEvaluationPipelineInput.model_validate(paper_evaluation_payload())
    _, intents = build_paper_evaluation_signals(pipeline)
    fills = build_paper_evaluation_fills(pipeline, intents)
    assert any(fill.fill_status == PaperEvaluationFillStatus.FILLED for fill in fills)


def test_paper_evaluation_fill_engine_reports_fill_gap_when_future_bar_missing():
    payload = paper_evaluation_payload()
    payload["price_history_rows"] = payload["price_history_rows"][:1]
    pipeline = PaperEvaluationPipelineInput.model_validate(payload)
    _, intents = build_paper_evaluation_signals(pipeline)
    fills = build_paper_evaluation_fills(pipeline, intents)
    assert any(fill.fill_status == PaperEvaluationFillStatus.FILL_GAP for fill in fills)


def test_paper_evaluation_fill_engine_blocks_same_bar_leakage():
    payload = paper_evaluation_payload()
    payload["feature_rows"][0]["feature_values"]["signal_score"] = 0.95
    payload["price_history_rows"][0]["available_at"] = "2026-06-02T16:35:00+09:00"
    pipeline = PaperEvaluationPipelineInput.model_validate(payload)
    _, intents = build_paper_evaluation_signals(pipeline)
    fills = build_paper_evaluation_fills(pipeline, intents)
    assert any(fill.fill_status == PaperEvaluationFillStatus.LEAKAGE_BLOCKED for fill in fills)
