from stock_risk_mcp.offline_strategy_models import OfflineStrategyCandidate
from stock_risk_mcp.offline_strategy_signal_engine import build_offline_strategy_signals
from tests.test_offline_strategy_models import offline_strategy_rows_payload


def test_offline_strategy_signal_engine_emits_signals() -> None:
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
    assert len(signals) == 1
    assert signals[0].report_only is True
