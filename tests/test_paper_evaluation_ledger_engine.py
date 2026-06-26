from stock_risk_mcp.paper_evaluation_fill_engine import build_paper_evaluation_fills
from stock_risk_mcp.paper_evaluation_ledger_engine import build_paper_evaluation_ledger
from stock_risk_mcp.paper_evaluation_models import PaperEvaluationPipelineInput
from stock_risk_mcp.paper_evaluation_portfolio_engine import build_paper_evaluation_portfolio
from stock_risk_mcp.paper_evaluation_signal_engine import build_paper_evaluation_signals
from tests.test_paper_evaluation_models import paper_evaluation_payload


def test_paper_evaluation_ledger_updates_cash_and_generates_positions():
    pipeline = PaperEvaluationPipelineInput.model_validate(paper_evaluation_payload())
    _, intents = build_paper_evaluation_signals(pipeline)
    fills = build_paper_evaluation_fills(pipeline, intents)
    ledger_entries, positions, trades = build_paper_evaluation_ledger(pipeline, intents, fills)
    assert ledger_entries
    assert positions
    assert trades


def test_paper_evaluation_portfolio_forces_close_open_positions():
    pipeline = PaperEvaluationPipelineInput.model_validate(paper_evaluation_payload())
    _, intents = build_paper_evaluation_signals(pipeline)
    fills = build_paper_evaluation_fills(pipeline, intents)
    ledger_entries, positions, trades = build_paper_evaluation_ledger(pipeline, intents, fills)
    updated_positions, updated_trades, snapshots, equity_curve = build_paper_evaluation_portfolio(pipeline, ledger_entries, positions, trades)
    assert snapshots
    assert equity_curve.points
    assert any(trade.forced_close for trade in updated_trades)
    assert all(position.closed for position in updated_positions)
