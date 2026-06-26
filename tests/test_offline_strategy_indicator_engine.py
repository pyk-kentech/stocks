from stock_risk_mcp.offline_strategy_indicator_engine import calculate_offline_strategy_indicators
from stock_risk_mcp.offline_strategy_models import OfflineStrategyCandidate
from tests.test_offline_strategy_models import offline_strategy_rows_payload


def test_offline_strategy_indicator_engine_builds_indicator_snapshot() -> None:
    rows = [__import__("stock_risk_mcp.historical_market_data_models", fromlist=["HistoricalOhlcvRow"]).HistoricalOhlcvRow.model_validate(item) for item in offline_strategy_rows_payload()]
    candidate = OfflineStrategyCandidate.model_validate(
        {
            "candidate_id": "candidate-1",
            "dataset_id": "offline-strategy-test",
            "template_id": "MACD_RSI_MOMENTUM_V1",
            "family": "MACD_RSI_MOMENTUM",
            "direction": "LONG_ONLY",
            "parameter_values": {},
        }
    )
    result = calculate_offline_strategy_indicators(rows, candidate)
    assert "rsi_level" in result
    assert "macd_golden_cross" in result
