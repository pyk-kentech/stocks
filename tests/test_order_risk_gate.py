from stock_risk_mcp.order_intent import OrderIntent, OrderSide, OrderType
from stock_risk_mcp.order_risk_gate import RiskGateConfig, evaluate_risk_gate
from stock_risk_mcp.realtime_market_data import MarketRegion, WatchlistEntry, WatchlistStatus


def test_risk_gate_approves_valid_buy_limit() -> None:
    decision = evaluate_risk_gate(_intent(), RiskGateConfig(max_risk_per_trade=10, max_position_notional=200))
    assert decision.approved is True
    assert decision.rule_hits_json == []


def test_risk_gate_blocks_core_invalid_requests() -> None:
    invalid_side = _intent().model_copy(update={"side": "INVALID"})
    cases = [
        (_intent(region=MarketRegion.UNKNOWN), "unknown_region"),
        (invalid_side, "invalid_side"),
        (_intent(quantity=None, notional=None), "missing_quantity_and_notional"),
        (_intent(quantity=-1), "non_positive_quantity"),
        (_intent(quantity=None, notional=-1), "non_positive_notional"),
        (_intent(order_type=OrderType.MARKET, limit_price=None), "market_order_disabled"),
        (_intent(stop_loss_price=None), "buy_stop_loss_required"),
        (_intent(stop_loss_price=100), "buy_stop_loss_not_below_entry"),
    ]
    for intent, expected in cases:
        assert expected in evaluate_risk_gate(intent, RiskGateConfig()).rule_hits_json


def test_risk_gate_market_opt_in_and_amount_limits() -> None:
    market = _intent(order_type=OrderType.MARKET, limit_price=None, metadata_json={"reference_price": 100})
    assert evaluate_risk_gate(market, RiskGateConfig(allow_market_orders=True)).approved
    assert "max_risk_per_trade_exceeded" in evaluate_risk_gate(
        _intent(quantity=3), RiskGateConfig(max_risk_per_trade=10)
    ).rule_hits_json
    assert "max_position_notional_exceeded" in evaluate_risk_gate(
        _intent(), RiskGateConfig(max_position_notional=99)
    ).rule_hits_json
    assert "max_daily_loss_exceeded" in evaluate_risk_gate(
        _intent(), RiskGateConfig(max_daily_loss=10, current_daily_loss=6)
    ).rule_hits_json


def test_risk_gate_blocks_products_blocklist_and_blocked_watchlist_but_not_hot() -> None:
    unsafe = [
        {"margin": True}, {"short": True}, {"instrument_type": "OPTION"},
        {"instrument_type": "FUTURE"}, {"leverage": 2},
    ]
    for metadata in unsafe:
        assert not evaluate_risk_gate(_intent(metadata_json=metadata), RiskGateConfig()).approved
    assert "ticker_blocked" in evaluate_risk_gate(
        _intent(), RiskGateConfig(blocked_tickers={"AAPL"})
    ).rule_hits_json
    assert not evaluate_risk_gate(_intent(), RiskGateConfig(), _entry(WatchlistStatus.BLOCKED)).approved
    assert evaluate_risk_gate(_intent(), RiskGateConfig(), _entry(WatchlistStatus.HOT)).approved


def _intent(**updates):
    values = dict(
        ticker="AAPL", region=MarketRegion.US, side=OrderSide.BUY, order_type=OrderType.LIMIT,
        quantity=1, notional=None, limit_price=100, stop_loss_price=95,
        source_type="manual", source_id="test", reason="test", confidence_score=0.5,
    )
    values.update(updates)
    return OrderIntent(**values)


def _entry(status):
    from datetime import datetime
    return WatchlistEntry(
        symbol="AAPL", region=MarketRegion.US, status=status,
        first_seen_at=datetime.now(), last_seen_at=datetime.now(),
        promotion_reason="test", score=1, metrics_json="{}",
    )
