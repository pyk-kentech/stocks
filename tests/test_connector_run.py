from datetime import date

from stock_risk_mcp.connector_run import ConnectorMode, ConnectorRun, ConnectorRunStatus, ConnectorType
from stock_risk_mcp.repository import RiskRepository


def test_connector_run_repository_round_trip(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    run = ConnectorRun(
        connector_run_id="connector_test",
        as_of_date=date(2026, 6, 13),
        connector_name="mock_news_signal",
        connector_type=ConnectorType.NEWS,
        mode=ConnectorMode.MOCK,
        status=ConnectorRunStatus.COMPLETED,
        output_path="news.csv",
        row_count=2,
    )

    repository.save_connector_run(run)

    assert repository.get_connector_run("connector_test") == run
    assert repository.list_connector_runs() == [run]
