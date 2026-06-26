from stock_risk_mcp.offline_strategy_backtest_engine import build_offline_strategy_backtest
from stock_risk_mcp.offline_strategy_models import OfflineStrategyCandidate
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
    assert all(intent.non_executable for intent in intents)
