from stock_risk_mcp.connector_registry import default_connector_registry, register_http_providers
from stock_risk_mcp.provider_config import HTTPProviderConfig, ProviderDataKind


def test_default_registry_contains_mock_connectors() -> None:
    registry = default_connector_registry()

    assert [item.name for item in registry.list_connectors()] == [
        "mock_market_data", "mock_news_signal", "mock_dilution_signal",
        "mock_toss_signal", "mock_flow_signal",
    ]
    assert registry.get_connector("mock_market_data").name == "mock_market_data"


def test_http_connectors_are_registered_only_when_explicitly_supplied() -> None:
    registry = default_connector_registry()

    register_http_providers(registry, [_provider()], enable_network=False)

    assert registry.get_connector("sample_prices").name == "sample_prices"
    assert "sample_prices" not in [item.name for item in default_connector_registry().list_connectors()]


def _provider() -> HTTPProviderConfig:
    return HTTPProviderConfig(
        provider_name="sample_prices", url="https://example.com/prices.csv",
        data_kind=ProviderDataKind.PRICE_HISTORY, output_format="CSV",
        allowed_hosts=["example.com"], enabled=True,
    )
