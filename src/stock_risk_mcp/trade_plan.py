from __future__ import annotations

import statistics

from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.price_history import sort_price_bars
from stock_risk_mcp.risk_reward import calculate_risk_reward
from stock_risk_mcp.setup import SetupDirection, SetupGrade, SetupSignal, TradeDecision, TradePlan, TradeSizingPolicy
from stock_risk_mcp.trade_sizing import calculate_trade_size


TARGET_RR = {SetupGrade.A: 4.0, SetupGrade.B: 3.0}
MINIMUM_RR = {SetupGrade.A: 3.0, SetupGrade.B: 2.5}


def create_trade_plan(setup: SetupSignal, bars: list[PriceBar], policy: TradeSizingPolicy) -> TradePlan:
    if setup.grade in {SetupGrade.C, SetupGrade.NO_TRADE} or setup.direction != SetupDirection.LONG:
        return _no_trade_plan(setup)

    ticker_bars = [bar for bar in sort_price_bars(bars) if bar.ticker == setup.ticker]
    if len(ticker_bars) < 20:
        return _blocked_plan(setup, "진입가와 손절가 계산에 필요한 가격 데이터가 부족합니다.")
    entry = ticker_bars[-1].close
    stop = _long_stop(ticker_bars, entry)
    if stop is None or stop >= entry:
        return _blocked_plan(setup, "유효한 손절가를 계산할 수 없습니다.")

    target_rr = TARGET_RR[setup.grade]
    target = entry + (entry - stop) * target_rr
    risk_reward = calculate_risk_reward(entry, stop, target)
    if risk_reward.risk_reward_ratio < MINIMUM_RR[setup.grade]:
        return _blocked_plan(setup, "최소 손익비 기준을 충족하지 못했습니다.")
    sizing = calculate_trade_size(entry, risk_reward.risk_per_share, setup.grade, policy)
    if sizing.position_size <= 0:
        return _blocked_plan(setup, "계산된 포지션 크기가 0 이하입니다.")

    decision = TradeDecision.PROPOSE if setup.grade == SetupGrade.A else TradeDecision.REVIEW
    return TradePlan(
        ticker=setup.ticker,
        direction=setup.direction,
        setup_grade=setup.grade,
        setup_score=setup.score,
        entry_price=entry,
        stop_price=stop,
        target_price=target,
        risk_reward_ratio=risk_reward.risk_reward_ratio,
        max_loss_amount=sizing.max_loss_amount,
        max_loss_currency=policy.currency,
        position_size=sizing.position_size,
        notional_value=sizing.notional_value,
        decision=decision,
        reasons=[*setup.reasons, "가격 히스토리 기반 진입/손절/목표가를 계산했습니다."],
        warnings=[*setup.warnings, "실제 주문 전 기존 Risk Engine 최종 검사가 필요합니다."],
        beginner_summary=f"{setup.grade.value} 셋업 후보지만 실제 주문이 아닌 paper trade proposal입니다.",
    )


def _long_stop(bars: list[PriceBar], entry: float) -> float | None:
    recent = bars[-20:]
    lows = [bar.low for bar in recent if bar.low is not None]
    atr = _atr(bars, 14)
    if not lows or atr is None:
        return None
    return min(min(float(low) for low in lows), entry - 1.5 * atr)


def _atr(bars: list[PriceBar], window: int) -> float | None:
    selected = bars[-(window + 1) :]
    if len(selected) <= window or any(bar.high is None or bar.low is None for bar in selected[1:]):
        return None
    ranges = [
        max(
            float(current.high) - float(current.low),
            abs(float(current.high) - previous.close),
            abs(float(current.low) - previous.close),
        )
        for previous, current in zip(selected[:-1], selected[1:])
    ]
    return statistics.fmean(ranges)


def _no_trade_plan(setup: SetupSignal) -> TradePlan:
    return TradePlan(
        ticker=setup.ticker,
        direction=setup.direction,
        setup_grade=setup.grade,
        setup_score=setup.score,
        decision=TradeDecision.NO_TRADE,
        reasons=setup.reasons,
        warnings=setup.warnings,
        beginner_summary="C 또는 NO_TRADE 셋업은 기본적으로 매매하지 않습니다.",
    )


def _blocked_plan(setup: SetupSignal, reason: str) -> TradePlan:
    return TradePlan(
        ticker=setup.ticker,
        direction=setup.direction,
        setup_grade=setup.grade,
        setup_score=setup.score,
        decision=TradeDecision.BLOCK,
        reasons=[*setup.reasons, reason],
        warnings=setup.warnings,
        beginner_summary=reason,
    )
