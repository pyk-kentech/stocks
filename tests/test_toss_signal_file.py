import json
from datetime import date

from stock_risk_mcp.toss_signal_file import load_toss_signals


def test_toss_file_aggregates_investors_and_clamps_positive_and_negative(tmp_path) -> None:
    path = tmp_path / "toss.json"
    path.write_text(json.dumps([
        {"ticker": "BUY", "observed_at": "2026-01-01", "investor_id": "1", "investor_rank_group": "TOP", "holding_weight": 5, "change_type": "BUY", "change_pct": 20},
        {"ticker": "BUY", "observed_at": "2026-01-01", "investor_id": "2", "investor_rank_group": "TOP", "holding_weight": 5, "change_type": "BUY", "change_pct": 20},
        {"ticker": "SELL", "observed_at": "2026-01-01", "investor_id": "1", "investor_rank_group": "TOP", "holding_weight": 0, "change_type": "EXIT", "change_pct": -100},
        {"ticker": "SELL", "observed_at": "2026-01-01", "investor_id": "2", "investor_rank_group": "TOP", "holding_weight": 0, "change_type": "EXIT", "change_pct": -100},
    ]), encoding="utf-8")

    signals = load_toss_signals(path, date(2026, 1, 2))

    assert {item.ticker: item.score_delta for item in signals} == {"BUY": 10, "SELL": -10}
