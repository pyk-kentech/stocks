from stock_risk_mcp.historical_market_data_import_engine import import_historical_chart_responses
from stock_risk_mcp.historical_market_data_models import HistoricalMarketDataPipelineInput
from stock_risk_mcp.historical_market_data_normalizer import normalize_historical_ohlcv_rows
from tests.test_historical_market_data_models import historical_market_data_payload, write_manual_daily_payload


def test_historical_market_data_normalizer_builds_daily_ohlcv_rows(tmp_path) -> None:
    manual_file = tmp_path / "manual_daily.json"
    write_manual_daily_payload(manual_file)
    fixture = HistoricalMarketDataPipelineInput.model_validate(
        historical_market_data_payload(
            store_root=str(tmp_path / "normalized"),
            raw_lake_root=str(tmp_path / "raw_lake"),
            manual_payload_path=str(manual_file),
        )
    )

    rows = normalize_historical_ohlcv_rows(fixture.dataset_id, import_historical_chart_responses(fixture))

    assert len(rows) == 3
    assert rows[0].interval.value == "1D"
    assert rows[-1].close_price == 82400
