from stock_risk_mcp.historical_market_data_import_engine import import_historical_chart_responses
from stock_risk_mcp.historical_market_data_models import HistoricalMarketDataPipelineInput
from tests.test_historical_market_data_models import historical_market_data_payload, write_manual_daily_payload


def test_historical_market_data_import_engine_loads_manual_json(tmp_path) -> None:
    manual_file = tmp_path / "manual_daily.json"
    write_manual_daily_payload(manual_file)
    fixture = HistoricalMarketDataPipelineInput.model_validate(
        historical_market_data_payload(
            store_root=str(tmp_path / "normalized"),
            raw_lake_root=str(tmp_path / "raw_lake"),
            manual_payload_path=str(manual_file),
        )
    )

    responses = import_historical_chart_responses(fixture)

    assert len(responses) == 1
    assert responses[0].api_id.value == "KA10081"
    assert responses[0].raw_payload_redacted is True
