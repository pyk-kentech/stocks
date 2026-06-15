from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_backtest_fixture import StrategyBacktestFixture, StrategyBacktestPricePoint
from stock_risk_mcp.strategy_core import (
    DeterministicStrategyEngine,
    StrategyCandidateSide,
    StrategyDecision,
    StrategyDecisionStatus,
)


class StrategyBacktestReason(StrEnum):
    FILLED = "FILLED"
    BLOCKED_ALREADY_POSITIONED = "BLOCKED_ALREADY_POSITIONED"
    BLOCKED_INSUFFICIENT_CASH = "BLOCKED_INSUFFICIENT_CASH"
    BLOCKED_NO_POSITION = "BLOCKED_NO_POSITION"
    BLOCKED_STRATEGY_DECISION = "BLOCKED_STRATEGY_DECISION"
    STRATEGY_NO_TRADE = "STRATEGY_NO_TRADE"
    NEEDS_MORE_DATA = "NEEDS_MORE_DATA"
    FORCED_END_OF_FIXTURE = "FORCED_END_OF_FIXTURE"
    STRATEGY_SELL = "STRATEGY_SELL"


class StrategyBacktestTradeStatus(StrEnum):
    CLOSED = "CLOSED"
    BLOCKED = "BLOCKED"
    NEEDS_MORE_DATA = "NEEDS_MORE_DATA"
    SKIPPED = "SKIPPED"


class StrategyBacktestRun(StrictModel):
    backtest_run_id: str = Field(default_factory=lambda: f"strategy_backtest_run_{uuid4().hex}")
    fixture_checksum: str = ""
    status: str = "COMPLETED"
    initial_cash: float
    final_cash: float
    decision_count: int
    metadata_json: dict = Field(default_factory=lambda: {
        "offline": True, "network_called": False, "credentials_read": False,
        "account_data_read": False, "orders_submitted": False,
    })
    created_at: datetime = Field(default_factory=datetime.now)


class StrategyBacktestTrade(StrictModel):
    trade_id: str = Field(default_factory=lambda: f"strategy_backtest_trade_{uuid4().hex}")
    backtest_run_id: str
    candidate_id: str
    decision_id: str
    ticker: str
    side: StrategyCandidateSide
    status: StrategyBacktestTradeStatus
    reason: StrategyBacktestReason
    decision_timestamp: datetime
    fill_timestamp: datetime | None = None
    exit_timestamp: datetime | None = None
    quantity: float | None = None
    entry_price: float | None = None
    exit_price: float | None = None
    realized_pnl: float | None = None
    realized_return_pct: float | None = None
    exit_reason: StrategyBacktestReason | None = None


class StrategyBacktestMetric(StrictModel):
    metric_id: str = Field(default_factory=lambda: f"strategy_backtest_metric_{uuid4().hex}")
    backtest_run_id: str
    total_return_pct: float
    max_drawdown_pct: float
    win_rate: float
    average_win_pct: float
    average_loss_pct: float
    trade_count: int
    exposure_time_pct: float
    blocked_decision_count: int
    missing_data_count: int
    stop_loss_hit_count: int = 0


class StrategyBacktestReport(StrictModel):
    report_id: str = Field(default_factory=lambda: f"strategy_backtest_report_{uuid4().hex}")
    backtest_run_id: str
    metric: StrategyBacktestMetric
    trades: list[StrategyBacktestTrade]
    decisions: list[StrategyDecision]
    created_at: datetime = Field(default_factory=datetime.now)


@dataclass
class _Position:
    trade_index: int
    quantity: float
    entry_price: float
    entry_timestamp: datetime


def run_strategy_backtest(fixture: StrategyBacktestFixture) -> StrategyBacktestReport:
    engine = DeterministicStrategyEngine()
    snapshots = {item.snapshot.snapshot_id: item.snapshot for item in fixture.snapshots}
    paths = {item.ticker: item.points for item in fixture.price_paths}
    events = sorted(fixture.candidate_events, key=lambda item: (item.decision_timestamp, snapshots[item.candidate.snapshot_id].ticker))
    run_id = f"strategy_backtest_run_{uuid4().hex}"
    cash = fixture.backtest_config.initial_cash
    positions: dict[str, _Position] = {}
    trades: list[StrategyBacktestTrade] = []
    decisions: list[StrategyDecision] = []
    timeline: list[tuple[datetime, str, str, float, float]] = []
    blocked = 0
    missing = 0

    for event in events:
        snapshot = snapshots[event.candidate.snapshot_id]
        ticker = snapshot.ticker
        decision = engine.decide(snapshot, event.candidate, fixture.strategy_config)
        decisions.append(decision)
        if decision.status not in (StrategyDecisionStatus.CANDIDATE_BUY, StrategyDecisionStatus.CANDIDATE_SELL):
            if decision.status == StrategyDecisionStatus.NEEDS_MORE_DATA:
                status, reason = StrategyBacktestTradeStatus.NEEDS_MORE_DATA, StrategyBacktestReason.NEEDS_MORE_DATA
            elif decision.status == StrategyDecisionStatus.BLOCKED:
                status, reason = StrategyBacktestTradeStatus.BLOCKED, StrategyBacktestReason.BLOCKED_STRATEGY_DECISION
            else:
                status, reason = StrategyBacktestTradeStatus.SKIPPED, StrategyBacktestReason.STRATEGY_NO_TRADE
            trades.append(_audit(run_id, event, decision, ticker, status, reason))
            missing += status == StrategyBacktestTradeStatus.NEEDS_MORE_DATA
            blocked += status == StrategyBacktestTradeStatus.BLOCKED
            continue
        if event.candidate.side == StrategyCandidateSide.BUY and ticker in positions:
            trades.append(_audit(run_id, event, decision, ticker, StrategyBacktestTradeStatus.BLOCKED, StrategyBacktestReason.BLOCKED_ALREADY_POSITIONED))
            blocked += 1
            continue
        if event.candidate.side == StrategyCandidateSide.SELL and ticker not in positions:
            trades.append(_audit(run_id, event, decision, ticker, StrategyBacktestTradeStatus.BLOCKED, StrategyBacktestReason.BLOCKED_NO_POSITION))
            blocked += 1
            continue
        fill = _first_after(paths.get(ticker, []), event.decision_timestamp)
        if fill is None:
            trades.append(_audit(run_id, event, decision, ticker, StrategyBacktestTradeStatus.NEEDS_MORE_DATA, StrategyBacktestReason.NEEDS_MORE_DATA))
            missing += 1
            continue
        if event.candidate.side == StrategyCandidateSide.BUY:
            quantity = fixture.backtest_config.fixed_quantity
            cost = quantity * fill.price
            if cost > cash:
                trades.append(_audit(run_id, event, decision, ticker, StrategyBacktestTradeStatus.BLOCKED, StrategyBacktestReason.BLOCKED_INSUFFICIENT_CASH))
                blocked += 1
                continue
            cash -= cost
            trade = _audit(run_id, event, decision, ticker, StrategyBacktestTradeStatus.CLOSED, StrategyBacktestReason.FILLED)
            trade = trade.model_copy(update={"fill_timestamp": fill.timestamp, "quantity": quantity, "entry_price": fill.price})
            trades.append(trade)
            positions[ticker] = _Position(len(trades) - 1, quantity, fill.price, fill.timestamp)
            timeline.append((fill.timestamp, "BUY", ticker, quantity, fill.price))
        else:
            position = positions[ticker]
            cash += position.quantity * fill.price
            trades[position.trade_index] = _close_trade(trades[position.trade_index], fill, StrategyBacktestReason.STRATEGY_SELL)
            timeline.append((fill.timestamp, "SELL", ticker, position.quantity, fill.price))
            del positions[ticker]

    for ticker, position in list(positions.items()):
        points = paths.get(ticker, [])
        if not points:
            missing += 1
            trades[position.trade_index] = trades[position.trade_index].model_copy(
                update={"status": StrategyBacktestTradeStatus.NEEDS_MORE_DATA, "reason": StrategyBacktestReason.NEEDS_MORE_DATA}
            )
            continue
        exit_point = points[-1]
        cash += position.quantity * exit_point.price
        trades[position.trade_index] = _close_trade(trades[position.trade_index], exit_point, StrategyBacktestReason.FORCED_END_OF_FIXTURE)
        timeline.append((exit_point.timestamp, "SELL", ticker, position.quantity, exit_point.price))

    equity_curve, equity_missing = _equity_curve(fixture, timeline)
    missing += equity_missing
    closed = [item for item in trades if item.status == StrategyBacktestTradeStatus.CLOSED and item.exit_price is not None]
    returns = [item.realized_return_pct or 0 for item in closed]
    wins = [item for item in returns if item > 0]
    losses = [item for item in returns if item < 0]
    metric = StrategyBacktestMetric(
        backtest_run_id=run_id,
        total_return_pct=(cash - fixture.backtest_config.initial_cash) / fixture.backtest_config.initial_cash * 100,
        max_drawdown_pct=_max_drawdown(equity_curve),
        win_rate=len(wins) / len(closed) * 100 if closed else 0,
        average_win_pct=sum(wins) / len(wins) if wins else 0,
        average_loss_pct=sum(losses) / len(losses) if losses else 0,
        trade_count=len(closed), exposure_time_pct=_exposure_time(fixture, timeline),
        blocked_decision_count=blocked, missing_data_count=missing,
    )
    return StrategyBacktestReport(backtest_run_id=run_id, metric=metric, trades=trades, decisions=decisions)


def _audit(run_id, event, decision, ticker, status, reason) -> StrategyBacktestTrade:
    return StrategyBacktestTrade(
        backtest_run_id=run_id, candidate_id=event.candidate.candidate_id,
        decision_id=decision.decision_id, ticker=ticker, side=event.candidate.side,
        status=status, reason=reason, decision_timestamp=event.decision_timestamp,
    )


def _first_after(points: list[StrategyBacktestPricePoint], timestamp: datetime) -> StrategyBacktestPricePoint | None:
    return next((item for item in points if item.timestamp > timestamp), None)


def _close_trade(trade: StrategyBacktestTrade, point: StrategyBacktestPricePoint, reason: StrategyBacktestReason) -> StrategyBacktestTrade:
    pnl = (point.price - (trade.entry_price or 0)) * (trade.quantity or 0)
    return trade.model_copy(update={
        "exit_timestamp": point.timestamp, "exit_price": point.price, "realized_pnl": pnl,
        "realized_return_pct": (point.price - (trade.entry_price or 0)) / (trade.entry_price or 1) * 100,
        "exit_reason": reason,
    })


def _equity_curve(fixture: StrategyBacktestFixture, timeline) -> tuple[list[float], int]:
    timestamps = sorted({point.timestamp for path in fixture.price_paths for point in path.points})
    paths = {path.ticker: path.points for path in fixture.price_paths}
    cash = fixture.backtest_config.initial_cash
    positions: dict[str, float] = {}
    values: list[float] = []
    missing = 0
    for timestamp in timestamps:
        for event_time, side, ticker, quantity, price in sorted(timeline, key=lambda item: item[0]):
            if event_time != timestamp:
                continue
            if side == "BUY":
                cash -= quantity * price
                positions[ticker] = quantity
            else:
                cash += quantity * price
                positions.pop(ticker, None)
        equity = cash
        for ticker, quantity in positions.items():
            latest = [point.price for point in paths.get(ticker, []) if point.timestamp <= timestamp]
            if not latest:
                missing += 1
                break
            equity += quantity * latest[-1]
        else:
            values.append(equity)
    return values, missing


def _max_drawdown(values: list[float]) -> float:
    peak = 0.0
    drawdown = 0.0
    for value in values:
        peak = max(peak, value)
        if peak:
            drawdown = min(drawdown, (value - peak) / peak * 100)
    return drawdown


def _exposure_time(fixture: StrategyBacktestFixture, timeline) -> float:
    timestamps = sorted({point.timestamp for path in fixture.price_paths for point in path.points})
    if len(timestamps) < 2:
        return 0
    positions: set[str] = set()
    exposed = 0.0
    for current, following in zip(timestamps, timestamps[1:]):
        for event_time, side, ticker, _quantity, _price in sorted(timeline, key=lambda item: item[0]):
            if event_time == current:
                positions.add(ticker) if side == "BUY" else positions.discard(ticker)
        if positions:
            exposed += (following - current).total_seconds()
    total = (timestamps[-1] - timestamps[0]).total_seconds()
    return exposed / total * 100 if total else 0
