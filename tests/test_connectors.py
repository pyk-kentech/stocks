from datetime import date

from stock_risk_mcp.connector_pipeline import run_connectors
from stock_risk_mcp.connector_registry import ConnectorRegistry
from stock_risk_mcp.connector_run import ConnectorMode, ConnectorRunStatus, ConnectorType
from stock_risk_mcp.repository import RiskRepository


class DisabledConnector:
    name = "disabled_news"
    connector_type = ConnectorType.NEWS
    mode = ConnectorMode.DISABLED

    def fetch(self, as_of_date, output_dir, **kwargs):
        raise AssertionError("disabled connector must not fetch")


def test_disabled_connector_is_recorded_without_fetching(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    registry = ConnectorRegistry()
    registry.register_connector(DisabledConnector())

    result = run_connectors(repository, registry, date(2026, 6, 13), tmp_path, ["disabled_news"], [])

    assert result[0].connector_run.status == ConnectorRunStatus.DISABLED
    assert repository.list_connector_runs()[0].warnings == ["Connector is disabled."]
