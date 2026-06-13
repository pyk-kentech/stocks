from stock_risk_mcp.connectors import BaseConnector
from stock_risk_mcp.http_connector import PublicHTTPConnector
from stock_risk_mcp.mock_connectors import (
    MockDilutionSignalConnector, MockFlowSignalConnector, MockMarketDataConnector,
    MockNewsSignalConnector, MockTossSignalConnector,
)


class ConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, BaseConnector] = {}

    def register_connector(self, connector: BaseConnector) -> None:
        self._connectors[connector.name] = connector

    def get_connector(self, name: str) -> BaseConnector:
        try:
            return self._connectors[name]
        except KeyError as error:
            raise LookupError(f"Connector not found: {name}") from error

    def list_connectors(self) -> list[BaseConnector]:
        return list(self._connectors.values())


def default_connector_registry() -> ConnectorRegistry:
    registry = ConnectorRegistry()
    for connector in (
        MockMarketDataConnector(), MockNewsSignalConnector(), MockDilutionSignalConnector(),
        MockTossSignalConnector(), MockFlowSignalConnector(),
    ):
        registry.register_connector(connector)
    return registry


def register_http_providers(
    registry: ConnectorRegistry,
    configs: list,
    enable_network: bool = False,
    runtime_allowed_hosts: list[str] | None = None,
    client=None,
) -> ConnectorRegistry:
    for config in configs:
        registry.register_connector(PublicHTTPConnector(
            config, enable_network=enable_network,
            runtime_allowed_hosts=runtime_allowed_hosts, client=client,
        ))
    return registry
