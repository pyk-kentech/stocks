from stock_risk_mcp.connector_registry import default_connector_registry


def test_default_registry_contains_mock_connectors() -> None:
    registry = default_connector_registry()

    assert [item.name for item in registry.list_connectors()] == [
        "mock_market_data", "mock_news_signal", "mock_dilution_signal",
        "mock_toss_signal", "mock_flow_signal",
    ]
    assert registry.get_connector("mock_market_data").name == "mock_market_data"
