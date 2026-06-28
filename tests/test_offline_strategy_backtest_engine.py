from stock_risk_mcp.offline_strategy_backtest_engine import build_offline_strategy_backtest
from datetime import datetime, timedelta

from stock_risk_mcp.offline_strategy_models import OfflineStrategyCandidate, OfflineStrategySignal
from stock_risk_mcp.offline_strategy_signal_engine import build_offline_strategy_signals
from tests.test_offline_strategy_models import offline_strategy_rows_payload


def test_offline_strategy_backtest_engine_uses_next_bar_fill() -> None:
    row_model = __import__("stock_risk_mcp.historical_market_data_models", fromlist=["HistoricalOhlcvRow"]).HistoricalOhlcvRow
    rows = [row_model.model_validate(item) for item in offline_strategy_rows_payload()]
    candidate = OfflineStrategyCandidate.model_validate(
        {
            "candidate_id": "candidate-1",
            "dataset_id": "offline-strategy-test",
            "template_id": "VOLUME_PULLBACK_LONG_V1",
            "family": "VOLUME_PULLBACK_LONG",
            "direction": "LONG_ONLY",
            "parameter_values": {"VOLUME_MULTIPLIER": 1.0},
        }
    )
    signals = build_offline_strategy_signals("offline-strategy-test", {"005930": rows}, candidate)
    intents, backtest = build_offline_strategy_backtest("offline-strategy-test", {"005930": rows}, candidate, signals, 5.0, 10.0)
    if backtest.trades:
        assert backtest.trades[0].entry_at > signals[0].observed_at
    assert backtest.trade_audit_summary["fill_policy"] == "CONSERVATIVE_NEXT_BAR_FILL"
    assert backtest.trade_audit_summary["next_bar_fill_used"] is True
    assert backtest.same_bar_fill_count == 0
    assert backtest.lookahead_violation_count == 0
    assert all(intent.non_executable for intent in intents)


def test_offline_strategy_backtest_engine_detects_same_bar_fill_violation() -> None:
    row_model = __import__("stock_risk_mcp.historical_market_data_models", fromlist=["HistoricalOhlcvRow"]).HistoricalOhlcvRow
    payload = offline_strategy_rows_payload()
    base_dt = datetime.fromisoformat(payload[0]["observed_at"])
    payload[1]["observed_at"] = (base_dt - timedelta(minutes=1)).isoformat()
    rows = [row_model.model_validate(item) for item in payload]
    candidate = OfflineStrategyCandidate.model_validate(
        {
            "candidate_id": "candidate-2",
            "dataset_id": "offline-strategy-test",
            "template_id": "VOLUME_PULLBACK_LONG_V1",
            "family": "VOLUME_PULLBACK_LONG",
            "direction": "LONG_ONLY",
            "parameter_values": {"VOLUME_MULTIPLIER": 1.0},
        }
    )
    bad_signal = OfflineStrategySignal.model_validate(
        {
            "signal_id": "bad-signal-1",
            "candidate_id": candidate.candidate_id,
            "instrument_id": "005930",
            "observed_at": rows[0].observed_at,
            "action": "ENTER_LONG",
            "rationale": "fixture",
            "signal_features": {},
        }
    )
    _intents, backtest = build_offline_strategy_backtest("offline-strategy-test", {"005930": rows}, candidate, [bad_signal], 5.0, 10.0)
    assert backtest.leakage_audit_status == "LEAKAGE_AUDIT_FAILED"
    assert backtest.same_bar_fill_count == 1
    assert backtest.lookahead_violation_count == 1
