from stock_risk_mcp.historical_market_data_models import HistoricalChartRequestPreview
from stock_risk_mcp.historical_market_data_transport import MockHistoricalMarketDataTransport


def test_historical_market_data_mock_transport_returns_stubbed_payload() -> None:
    transport = MockHistoricalMarketDataTransport(
        {"REQUEST-1": {"status_code": 200, "headers": {}, "body_json": {"return_code": 0, "return_msg": "OK"}}}
    )
    preview = HistoricalChartRequestPreview.model_validate(
        {
            "report_id": "REQUEST-1-REQUEST-PREVIEW",
            "api_id": "KA10081",
            "provider": "KIWOOM_REST",
            "path": "/api/dostk/chart",
            "headers": {"api-id": "KA10081"},
            "body_json": {"stk_cd": "005930"},
        }
    )
    result = transport.execute(preview)
    assert result["body_json"]["return_code"] == 0
