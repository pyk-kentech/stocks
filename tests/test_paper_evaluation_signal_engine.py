import pytest

from stock_risk_mcp.paper_evaluation_models import PaperEvaluationPipelineInput, PaperEvaluationSide, PaperEvaluationSignalStatus
from stock_risk_mcp.paper_evaluation_signal_engine import build_paper_evaluation_signals
from tests.test_paper_evaluation_models import paper_evaluation_payload


def test_paper_evaluation_signal_replay_builds_signals_without_labels():
    signals, intents = build_paper_evaluation_signals(PaperEvaluationPipelineInput.model_validate(paper_evaluation_payload()))
    assert signals
    assert intents
    assert all(signal.side in {PaperEvaluationSide.BUY, PaperEvaluationSide.WATCH, PaperEvaluationSide.NO_TRADE, PaperEvaluationSide.HOLD} for signal in signals)


def test_paper_evaluation_signal_replay_blocks_event_risk():
    payload = paper_evaluation_payload()
    payload["feature_rows"][0]["feature_values"]["event_window_active"] = True
    signals, _ = build_paper_evaluation_signals(PaperEvaluationPipelineInput.model_validate(payload))
    assert signals[0].signal_status == PaperEvaluationSignalStatus.BLOCKED_EVENT_RISK


def test_paper_evaluation_signal_replay_rejects_label_like_feature_names():
    payload = paper_evaluation_payload()
    payload["feature_rows"][0]["feature_values"]["forward_return"] = 0.1
    with pytest.raises(ValueError):
        build_paper_evaluation_signals(PaperEvaluationPipelineInput.model_validate(payload))
