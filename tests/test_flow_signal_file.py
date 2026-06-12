import json
from datetime import date

from stock_risk_mcp.flow_signal_file import load_flow_signals
from stock_risk_mcp.signals import SignalDirection


def test_flow_file_rewards_joint_buying_and_ignores_future(tmp_path) -> None:
    path = tmp_path / "flow.json"
    path.write_text(json.dumps([
        {"ticker": "AAA", "observed_at": "2026-01-01", "foreign_net_buy": 10, "institution_net_buy": 20, "foreign_ownership_change": 1, "flow_window_days": 5},
        {"ticker": "AAA", "observed_at": "2026-01-03", "foreign_net_buy": -10, "institution_net_buy": -20, "flow_window_days": 5},
    ]), encoding="utf-8")

    signals = load_flow_signals(path, date(2026, 1, 2))

    assert len(signals) == 1
    assert signals[0].direction == SignalDirection.POSITIVE
    assert signals[0].score_delta > 0
