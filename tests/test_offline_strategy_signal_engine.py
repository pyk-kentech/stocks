from stock_risk_mcp.offline_strategy_models import OfflineStrategyCandidate
from stock_risk_mcp.offline_strategy_signal_engine import build_offline_strategy_signal_bundle, build_offline_strategy_signals
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
    assert len(signals) >= 1
    assert all(signal.report_only is True for signal in signals)


def test_offline_strategy_signal_bundle_reports_schema_gap() -> None:
    row_model = __import__("stock_risk_mcp.historical_market_data_models", fromlist=["HistoricalOhlcvRow"]).HistoricalOhlcvRow
    payload = offline_strategy_rows_payload()
    for item in payload:
        item["volume"] = None
    rows = [row_model.model_validate(item) for item in payload]
    candidate = OfflineStrategyCandidate.model_validate(
        {
            "candidate_id": "candidate-2",
            "dataset_id": "offline-strategy-test",
            "template_id": "VOLUME_PULLBACK_LONG_V1",
            "family": "VOLUME_PULLBACK_LONG",
            "direction": "LONG_ONLY",
            "parameter_values": {"VOLUME_MULTIPLIER": 0.95},
        }
    )
    bundle = build_offline_strategy_signal_bundle("offline-strategy-test", {"005930": rows}, candidate)
    diagnostics = bundle.diagnostics_by_instrument["005930"]
    assert diagnostics["signal_input_schema_gap"] is True
    assert "VOLUME" in diagnostics["missing_indicator_columns"]
    assert diagnostics["entry_signal_count"] == 0
