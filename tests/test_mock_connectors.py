from datetime import date

from stock_risk_mcp.connector_run import ConnectorRunStatus
from stock_risk_mcp.mock_connectors import MockMarketDataConnector, MockNewsSignalConnector


def test_mock_connectors_create_deterministic_normalized_csv(tmp_path) -> None:
    first = MockMarketDataConnector().fetch(date(2026, 6, 13), tmp_path / "one", tickers=["AAA"])
    second = MockMarketDataConnector().fetch(date(2026, 6, 13), tmp_path / "two", tickers=["AAA"])
    news = MockNewsSignalConnector().fetch(date(2026, 6, 13), tmp_path, tickers=["AAA", "BBB"])

    assert first.connector_run.status == ConnectorRunStatus.COMPLETED
    assert first.connector_run.row_count == 120
    assert open(first.output.output_path, encoding="utf-8").read() == open(second.output.output_path, encoding="utf-8").read()
    assert news.connector_run.row_count == 2
