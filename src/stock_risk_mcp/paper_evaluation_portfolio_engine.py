from __future__ import annotations

from collections import defaultdict

from stock_risk_mcp.paper_evaluation_models import (
    PaperEvaluationEquityCurve,
    PaperEvaluationLedgerEntry,
    PaperEvaluationPipelineInput,
    PaperEvaluationPortfolioSnapshot,
    PaperEvaluationPosition,
    PaperEvaluationTrade,
)


def build_paper_evaluation_portfolio(
    pipeline_input: PaperEvaluationPipelineInput,
    ledger_entries: list[PaperEvaluationLedgerEntry],
    positions: list[PaperEvaluationPosition],
    trades: list[PaperEvaluationTrade],
) -> tuple[list[PaperEvaluationPosition], list[PaperEvaluationTrade], list[PaperEvaluationPortfolioSnapshot], PaperEvaluationEquityCurve]:
    latest_bar_by_instrument = defaultdict(lambda: None)
    for bar in pipeline_input.price_history_rows:
        latest_bar_by_instrument[bar.instrument_id] = bar

    updated_positions: list[PaperEvaluationPosition] = []
    updated_trades: list[PaperEvaluationTrade] = []
    for position in positions:
        latest = latest_bar_by_instrument[position.instrument_id]
        if latest is None:
            updated_positions.append(position)
            continue
        market_price = latest.close_price
        market_value = market_price * position.open_quantity
        unrealized = (market_price - position.average_entry_price) * position.open_quantity
        forced_close = position.open_quantity > 0
        updated_positions.append(
            position.model_copy(
                update={
                    "market_price": market_price,
                    "market_value": 0.0 if forced_close else market_value,
                    "unrealized_pnl": 0.0 if forced_close else unrealized,
                    "open_quantity": 0.0 if forced_close else position.open_quantity,
                    "closed": forced_close or position.closed,
                }
            )
        )
        trade = next((item for item in trades if item.instrument_id == position.instrument_id and item.split_id == position.split_id), None)
        if trade is not None:
            updated_trades.append(
                trade.model_copy(
                    update={
                        "exit_time": latest.available_at if forced_close else trade.exit_time,
                        "exit_price": market_price if forced_close else trade.exit_price,
                        "gross_pnl": ((market_price - trade.entry_price) * trade.quantity) if forced_close else trade.gross_pnl,
                        "net_pnl": ((market_price - trade.entry_price) * trade.quantity) if forced_close else trade.net_pnl,
                        "holding_bars": max(trade.holding_bars, 1),
                        "forced_close": forced_close or trade.forced_close,
                    }
                )
            )

    existing_trade_ids = {trade.trade_id for trade in updated_trades}
    for trade in trades:
        if trade.trade_id not in existing_trade_ids:
            updated_trades.append(trade)

    snapshots: list[PaperEvaluationPortfolioSnapshot] = []
    peak_equity = pipeline_input.config.starting_cash
    for index, entry in enumerate(sorted(ledger_entries, key=lambda item: (item.event_time, item.ledger_entry_id))):
        open_positions = [position for position in updated_positions if position.open_quantity > 0]
        market_value = sum(position.market_value for position in open_positions)
        equity = entry.cash_after + market_value
        peak_equity = max(peak_equity, equity)
        drawdown_amount = max(0.0, peak_equity - equity)
        drawdown_pct = drawdown_amount / peak_equity if peak_equity else 0.0
        snapshots.append(
            PaperEvaluationPortfolioSnapshot(
                snapshot_id=f"{pipeline_input.dataset_id}-SNAPSHOT-{index}",
                dataset_id=pipeline_input.dataset_id,
                split_id=entry.split_id,
                observed_at=entry.event_time,
                cash=entry.cash_after,
                equity=equity,
                gross_exposure=market_value,
                net_exposure=market_value,
                drawdown_amount=drawdown_amount,
                drawdown_pct=drawdown_pct,
                open_position_count=len(open_positions),
            )
        )

    equity_curve = PaperEvaluationEquityCurve(
        curve_id=f"{pipeline_input.dataset_id}-EQUITY-CURVE",
        dataset_id=pipeline_input.dataset_id,
        points=snapshots,
    )
    return updated_positions, updated_trades, snapshots, equity_curve
