from stock_risk_mcp.paper_fill_engine import evaluate_long_exit, should_fill_long_entry
from stock_risk_mcp.paper_eval_models import PaperPosition, PaperPriceBar


def bar(low, high, close=100.0):
    open_price = max(low, min(100.0, high))
    close_price = max(low, min(close, high))
    return PaperPriceBar(
        timestamp="2026-01-10T09:31:00+00:00",
        open=open_price,
        high=high,
        low=low,
        close=close_price,
    )


def position():
    return PaperPosition(
        ticker="ABC",
        entry_time="2026-01-10T09:31:00+00:00",
        entry_price=100.0,
        stop_price=96.0,
        target_price=108.0,
        quantity=10,
        entry_notional=1000.0,
        source_type="TRADE_PLAN",
    )


def test_buy_entry_fills_when_low_to_high_contains_entry():
    assert should_fill_long_entry(100.0, bar(low=99.0, high=101.0)) is True
    assert should_fill_long_entry(100.0, bar(low=100.1, high=101.0)) is False


def test_stop_hit_and_target_hit_are_deterministic():
    assert evaluate_long_exit(position(), bar(low=95.0, high=100.0)) == ("STOP_HIT", 96.0)
    assert evaluate_long_exit(position(), bar(low=100.0, high=109.0)) == ("TARGET_HIT", 108.0)


def test_same_bar_stop_and_target_conflict_uses_stop_first():
    assert evaluate_long_exit(position(), bar(low=95.0, high=109.0)) == ("STOP_HIT", 96.0)
