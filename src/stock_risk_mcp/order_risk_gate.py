from __future__ import annotations

from dataclasses import dataclass, field

from stock_risk_mcp.order_intent import OrderIntent, OrderSide, OrderType, RiskGateDecision
from stock_risk_mcp.realtime_market_data import MarketRegion, WatchlistEntry, WatchlistStatus


@dataclass(frozen=True)
class RiskGateConfig:
    allow_market_orders: bool = False
    max_risk_per_trade: float | None = None
    max_position_notional: float | None = None
    max_daily_loss: float | None = None
    current_daily_loss: float = 0
    blocked_tickers: set[str] = field(default_factory=set)


def evaluate_risk_gate(
    intent: OrderIntent,
    config: RiskGateConfig,
    watchlist_entry: WatchlistEntry | None = None,
) -> RiskGateDecision:
    hits: list[str] = []
    if not intent.ticker:
        hits.append("missing_ticker")
    if intent.region == MarketRegion.UNKNOWN:
        hits.append("unknown_region")
    if intent.side not in {OrderSide.BUY, OrderSide.SELL}:
        hits.append("invalid_side")
    if intent.order_type == OrderType.MARKET and not config.allow_market_orders:
        hits.append("market_order_disabled")
    if intent.quantity is None and intent.notional is None:
        hits.append("missing_quantity_and_notional")
    if intent.quantity is not None and intent.quantity <= 0:
        hits.append("non_positive_quantity")
    if intent.notional is not None and intent.notional <= 0:
        hits.append("non_positive_notional")
    if intent.order_type in {OrderType.LIMIT, OrderType.STOP_LIMIT} and (
        intent.limit_price is None or intent.limit_price <= 0
    ):
        hits.append("invalid_limit_price")

    entry_price = _entry_price(intent)
    quantity = _derived_quantity(intent, entry_price)
    position_notional = intent.notional if intent.notional is not None else (
        quantity * entry_price if quantity is not None and entry_price is not None else None
    )
    estimated_loss = None
    if intent.side == OrderSide.BUY:
        if intent.stop_loss_price is None:
            hits.append("buy_stop_loss_required")
        elif entry_price is not None and intent.stop_loss_price >= entry_price:
            hits.append("buy_stop_loss_not_below_entry")
        if entry_price is not None and quantity is not None and intent.stop_loss_price is not None:
            estimated_loss = (entry_price - intent.stop_loss_price) * quantity
        if estimated_loss is None or estimated_loss < 0:
            hits.append("buy_risk_not_calculable")
    if config.max_risk_per_trade is not None and estimated_loss is not None and estimated_loss > config.max_risk_per_trade:
        hits.append("max_risk_per_trade_exceeded")
    if (
        config.max_position_notional is not None
        and position_notional is not None
        and position_notional > config.max_position_notional
    ):
        hits.append("max_position_notional_exceeded")
    if (
        config.max_daily_loss is not None
        and estimated_loss is not None
        and config.current_daily_loss + estimated_loss > config.max_daily_loss
    ):
        hits.append("max_daily_loss_exceeded")

    metadata = intent.metadata_json
    if metadata.get("margin") is True:
        hits.append("margin_disabled")
    if metadata.get("short") is True:
        hits.append("short_selling_disabled")
    if str(metadata.get("instrument_type", "")).upper() in {"OPTION", "OPTIONS"}:
        hits.append("options_disabled")
    if str(metadata.get("instrument_type", "")).upper() in {"FUTURE", "FUTURES"}:
        hits.append("futures_disabled")
    try:
        if float(metadata.get("leverage", 1)) > 1:
            hits.append("leverage_disabled")
    except (TypeError, ValueError):
        hits.append("invalid_leverage")
    if intent.ticker in {item.strip().upper() for item in config.blocked_tickers}:
        hits.append("ticker_blocked")
    if watchlist_entry is not None and watchlist_entry.status == WatchlistStatus.BLOCKED:
        hits.append("watchlist_blocked")
    hits = list(dict.fromkeys(hits))
    return RiskGateDecision(
        order_intent_id=intent.order_intent_id,
        approved=not hits,
        decision="APPROVED" if not hits else "BLOCKED",
        reasons_json=[item.replace("_", " ") for item in hits],
        rule_hits_json=hits,
    )


def _entry_price(intent: OrderIntent) -> float | None:
    if intent.order_type == OrderType.MARKET:
        try:
            value = float(intent.metadata_json.get("reference_price"))
            return value if value > 0 else None
        except (TypeError, ValueError):
            return None
    return intent.limit_price if intent.limit_price is not None and intent.limit_price > 0 else None


def _derived_quantity(intent: OrderIntent, entry_price: float | None) -> float | None:
    if intent.quantity is not None and intent.quantity > 0:
        return intent.quantity
    if intent.notional is not None and intent.notional > 0 and entry_price is not None:
        return intent.notional / entry_price
    return None
