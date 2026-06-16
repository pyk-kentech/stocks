from __future__ import annotations

from statistics import fmean

from stock_risk_mcp.paper_eval_models import (
    PaperEvalFixture,
    PaperEvalInput,
    PaperEvalMetrics,
    PaperEvalReport,
    PaperEvalSide,
    PaperPortfolioState,
    PaperPosition,
    PaperTrade,
)
from stock_risk_mcp.paper_fill_engine import evaluate_long_exit, should_fill_long_entry


def build_paper_eval_report(fixture: PaperEvalFixture, fixture_checksum: str) -> PaperEvalReport:
    price_paths = {path.ticker: path for path in fixture.price_paths}
    trades: list[PaperTrade] = []
    blocked_reasons: list[str] = []
    equity_curve: list[PaperPortfolioState] = []
    cash = fixture.config.initial_cash
    realized_pnl = 0.0
    peak_equity = fixture.config.initial_cash
    total_holding_seconds = 0.0

    for candidate in fixture.inputs:
        trade = PaperTrade(
            ticker=candidate.ticker,
            source_type=candidate.source_type,
            decision_time=candidate.decision_time,
            entry_reference=candidate.entry_reference,
            planned_quantity=candidate.suggested_quantity,
        )
        if candidate.side != PaperEvalSide.BUY:
            trade = trade.model_copy(update={"blocked": True, "block_reasons": ["UNSUPPORTED_SIDE"]})
            trades.append(trade)
            blocked_reasons.extend(trade.block_reasons)
            continue
        if candidate.stop_reference is None or candidate.stop_reference >= candidate.entry_reference:
            trade = trade.model_copy(update={"blocked": True, "block_reasons": ["INVALID_STOP"]})
            trades.append(trade)
            blocked_reasons.extend(trade.block_reasons)
            continue
        if candidate.target_reference is None or candidate.target_reference <= candidate.entry_reference:
            trade = trade.model_copy(update={"blocked": True, "block_reasons": ["INSUFFICIENT_TARGET"]})
            trades.append(trade)
            blocked_reasons.extend(trade.block_reasons)
            continue
        if candidate.plan_status != "TRADE_PLAN_READY":
            trade = trade.model_copy(update={"blocked": True, "block_reasons": ["PLAN_NOT_READY"]})
            trades.append(trade)
            blocked_reasons.extend(trade.block_reasons)
            continue

        path = price_paths.get(candidate.ticker)
        if path is None:
            trades.append(trade.model_copy(update={"missing_data": True, "block_reasons": ["MISSING_PRICE_PATH"]}))
            blocked_reasons.append("MISSING_PRICE_PATH")
            continue

        entry_cost = candidate.entry_reference * candidate.suggested_quantity
        entry_slippage = fixture.config.slippage_per_share * candidate.suggested_quantity
        total_entry_cash = entry_cost + fixture.config.fee_per_trade + entry_slippage
        if total_entry_cash > cash:
            trade = trade.model_copy(update={"blocked": True, "block_reasons": ["INSUFFICIENT_CASH"]})
            trades.append(trade)
            blocked_reasons.extend(trade.block_reasons)
            continue

        eligible_bars = [bar for bar in path.bars if bar.timestamp >= candidate.decision_time]
        entry_bar = next((bar for bar in eligible_bars if should_fill_long_entry(candidate.entry_reference, bar)), None)
        if entry_bar is None:
            trades.append(trade.model_copy(update={"block_reasons": ["ENTRY_NOT_FILLED"]}))
            blocked_reasons.append("ENTRY_NOT_FILLED")
            continue

        cash -= total_entry_cash
        position = PaperPosition(
            ticker=candidate.ticker,
            entry_time=entry_bar.timestamp,
            entry_price=candidate.entry_reference,
            stop_price=candidate.stop_reference,
            target_price=candidate.target_reference,
            quantity=candidate.suggested_quantity,
            entry_notional=entry_cost,
            source_type=candidate.source_type,
        )
        trade = trade.model_copy(
            update={
                "simulated_entry_time": entry_bar.timestamp,
                "simulated_entry_price": candidate.entry_reference,
            }
        )
        equity_curve.append(build_curve_point(entry_bar.timestamp, cash, realized_pnl, max(peak_equity, cash)))
        bars_after_entry = [bar for bar in eligible_bars if bar.timestamp >= entry_bar.timestamp]
        exit_bar_count = 0
        for bar in bars_after_entry:
            exit_bar_count += 1
            decision = evaluate_long_exit(position, bar)
            if decision is None:
                continue
            exit_reason, exit_price = decision
            trade = close_trade(trade, position, bar.timestamp, exit_price, exit_reason, fixture)
            cash += exit_price * position.quantity - fixture.config.fee_per_trade - entry_slippage
            realized_pnl += trade.net_pnl
            total_holding_seconds += trade.holding_seconds
            peak_equity = max(peak_equity, cash)
            equity_curve.append(build_curve_point(bar.timestamp, cash, realized_pnl, peak_equity))
            break
        else:
            final_bar = bars_after_entry[-1]
            trade = close_trade(trade, position, final_bar.timestamp, final_bar.close, "FORCED_END_OF_FIXTURE", fixture)
            cash += final_bar.close * position.quantity - fixture.config.fee_per_trade - entry_slippage
            realized_pnl += trade.net_pnl
            total_holding_seconds += trade.holding_seconds
            peak_equity = max(peak_equity, cash)
            equity_curve.append(build_curve_point(final_bar.timestamp, cash, realized_pnl, peak_equity))
        trade = trade.model_copy(update={"holding_bars": exit_bar_count})
        trades.append(trade)

    if not equity_curve:
        equity_curve.append(build_curve_point(fixture.created_at, cash, realized_pnl, peak_equity))
    metrics = build_metrics(fixture, trades, equity_curve, total_holding_seconds)
    return PaperEvalReport(
        fixture_checksum=fixture_checksum,
        run_id=fixture.run_id,
        created_at=fixture.created_at,
        config=fixture.config,
        inputs=fixture.inputs,
        paper_trades=trades,
        equity_curve=equity_curve,
        metrics=metrics,
        blocked_reasons=blocked_reasons,
    )


def close_trade(trade, position, exit_time, exit_price, exit_reason, fixture):
    gross_pnl = (exit_price - position.entry_price) * position.quantity
    total_slippage = fixture.config.slippage_per_share * position.quantity * 2
    total_fees = fixture.config.fee_per_trade * 2
    net_pnl = gross_pnl - total_slippage - total_fees
    return trade.model_copy(
        update={
            "simulated_exit_time": exit_time,
            "simulated_exit_price": exit_price,
            "exit_reason": exit_reason,
            "gross_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "holding_seconds": max((exit_time - position.entry_time).total_seconds(), 0.0),
            "stop_hit": exit_reason == "STOP_HIT",
            "target_hit": exit_reason == "TARGET_HIT",
        }
    )


def build_curve_point(timestamp, cash, realized_pnl, peak_equity):
    drawdown_amount = max(peak_equity - cash, 0.0)
    drawdown_pct = (drawdown_amount / peak_equity * 100) if peak_equity else 0.0
    return PaperPortfolioState(
        timestamp=timestamp,
        cash_available=cash,
        realized_pnl=realized_pnl,
        equity=cash,
        peak_equity=peak_equity,
        drawdown_amount=drawdown_amount,
        drawdown_pct=drawdown_pct,
    )


def build_metrics(fixture, trades, equity_curve, total_holding_seconds):
    closed = [trade for trade in trades if trade.simulated_exit_time is not None]
    wins = [trade.net_pnl for trade in closed if trade.net_pnl > 0]
    losses = [trade.net_pnl for trade in closed if trade.net_pnl < 0]
    gross_profit = sum(wins)
    gross_loss = sum(losses)
    total_timeline = max(
        (max(bar.timestamp for path in fixture.price_paths for bar in path.bars) - min(bar.timestamp for path in fixture.price_paths for bar in path.bars)).total_seconds(),
        0.0,
    )
    final_equity = equity_curve[-1].equity if equity_curve else fixture.config.initial_cash
    return PaperEvalMetrics(
        total_return_pct=((final_equity - fixture.config.initial_cash) / fixture.config.initial_cash * 100),
        max_drawdown_pct=max((point.drawdown_pct for point in equity_curve), default=0.0),
        win_rate=(len(wins) / len(closed) * 100) if closed else None,
        average_win_amount=fmean(wins) if wins else None,
        average_loss_amount=fmean(losses) if losses else None,
        profit_factor=(gross_profit / abs(gross_loss)) if gross_loss else None,
        expectancy_amount=(sum(trade.net_pnl for trade in closed) / len(closed)) if closed else None,
        exposure_time_pct=(total_holding_seconds / total_timeline * 100) if total_timeline else 0.0,
        trade_count=len(closed),
        stop_hit_count=sum(trade.stop_hit for trade in closed),
        target_hit_count=sum(trade.target_hit for trade in closed),
        blocked_plan_count=sum(trade.blocked for trade in trades),
        missing_data_count=sum(trade.missing_data for trade in trades),
    )
