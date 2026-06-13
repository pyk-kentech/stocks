from __future__ import annotations

import math

from pydantic import Field

from stock_risk_mcp.models import StrictModel


class FXAwareSizingResult(StrictModel):
    ticker: str
    account_currency: str
    trading_currency: str
    entry_price_trading: float
    stop_price_trading: float
    max_loss_account: float | None = None
    max_loss_trading: float
    shares: int
    notional_trading: float
    notional_account: float | None = None
    estimated_loss_trading: float
    estimated_loss_account: float | None = None
    fx_rate: float | None = None
    warnings: list[str] = Field(default_factory=list)


def build_fx_aware_sizing(ticker: str, entry_price: float, stop_price: float, max_loss_account: float, context) -> FXAwareSizingResult:
    max_loss_trading = context.account_to_trading(max_loss_account)
    if max_loss_trading is None:
        max_loss_trading = max_loss_account
    risk_per_share = max(entry_price - stop_price, 0)
    shares = math.floor(max_loss_trading / risk_per_share) if risk_per_share > 0 else 0
    notional_trading = shares * entry_price
    estimated_loss_trading = shares * risk_per_share
    return FXAwareSizingResult(
        ticker=ticker.upper(), account_currency=context.account_currency, trading_currency=context.trading_currency,
        entry_price_trading=entry_price, stop_price_trading=stop_price,
        max_loss_account=max_loss_account if context.fx_rate is not None else None,
        max_loss_trading=max_loss_trading, shares=shares, notional_trading=notional_trading,
        notional_account=context.trading_to_account(notional_trading),
        estimated_loss_trading=estimated_loss_trading,
        estimated_loss_account=context.trading_to_account(estimated_loss_trading),
        fx_rate=context.fx_rate, warnings=context.warnings,
    )


def apply_fx_to_trade_plan(plan, context):
    payload = plan.model_dump() if hasattr(plan, "model_dump") else dict(plan)
    max_loss = payload.get("max_loss_amount")
    notional = payload.get("notional_value")
    estimated = (
        (payload.get("entry_price") - payload.get("stop_price")) * payload.get("position_size")
        if payload.get("entry_price") is not None and payload.get("stop_price") is not None and payload.get("position_size") is not None
        else None
    )
    payload.update({
        "account_currency": context.account_currency, "trading_currency": context.trading_currency,
        "fx_rate": context.fx_rate, "fx_date": context.fx_date, "fx_source_name": context.fx_source_name,
        "fx_stale": context.fx_stale, "max_loss_account": context.trading_to_account(max_loss),
        "max_loss_trading": max_loss, "notional_account": context.trading_to_account(notional),
        "notional_trading": notional, "estimated_loss_account": context.trading_to_account(estimated),
        "estimated_loss_trading": estimated, "fx_warnings_json": context.warnings,
    })
    return payload


def apply_fx_to_basket(plan, context):
    allocations = [
        item.model_copy(update={
            "account_currency": context.account_currency, "trading_currency": context.trading_currency,
            "fx_rate": context.fx_rate, "allocated_loss_account": context.trading_to_account(item.allocated_loss_amount),
            "allocated_loss_trading": item.allocated_loss_amount,
            "notional_account": context.trading_to_account(item.allocated_notional_value),
            "notional_trading": item.allocated_notional_value, "fx_warnings_json": context.warnings,
        })
        for item in plan.allocations
    ]
    total_notional = plan.risk_summary.total_notional_value
    total_loss = plan.risk_summary.total_allocated_loss
    values = {
        "account_currency": context.account_currency, "trading_currency": context.trading_currency,
        "fx_rate": context.fx_rate, "fx_date": context.fx_date,
        "total_notional_account": context.trading_to_account(total_notional),
        "total_notional_trading": total_notional, "total_max_loss_account": context.trading_to_account(total_loss),
        "total_max_loss_trading": total_loss, "fx_warnings_json": context.warnings,
    }
    return plan.model_copy(update={
        **values, "allocations": allocations, "risk_summary": plan.risk_summary.model_copy(update=values),
    })


def apply_fx_to_paper_result(result, context):
    return result.model_copy(update={
        "realized_pnl_account": context.trading_to_account(result.realized_pnl),
        "realized_pnl_trading": result.realized_pnl, "return_account_pct": result.realized_return_pct,
        "return_trading_pct": result.realized_return_pct, "fx_rate": context.fx_rate,
        "account_currency": context.account_currency, "trading_currency": context.trading_currency,
        "fx_warnings_json": context.warnings,
    })
