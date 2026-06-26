from stock_risk_mcp.historical_market_data_api_catalog import build_historical_market_data_api_catalog


def test_historical_market_data_api_catalog_reports_schema_ready_and_gaps() -> None:
    report = build_historical_market_data_api_catalog()

    assert "KA10080" in report.schema_ready_api_ids
    assert "KA10081" in report.schema_ready_api_ids
    assert "KA10079" in report.capability_only_api_ids
    assert "KA10082" in report.schema_gap_api_ids
