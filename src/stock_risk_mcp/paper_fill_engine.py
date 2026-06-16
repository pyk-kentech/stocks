from __future__ import annotations

from stock_risk_mcp.paper_eval_models import PaperPosition, PaperPriceBar


def should_fill_long_entry(entry_price: float, bar: PaperPriceBar) -> bool:
    return bar.low <= entry_price <= bar.high


def evaluate_long_exit(position: PaperPosition, bar: PaperPriceBar) -> tuple[str, float] | None:
    stop_hit = bar.low <= position.stop_price
    target_hit = bar.high >= position.target_price
    if stop_hit and target_hit:
        return ("STOP_HIT", position.stop_price)
    if stop_hit:
        return ("STOP_HIT", position.stop_price)
    if target_hit:
        return ("TARGET_HIT", position.target_price)
    return None
