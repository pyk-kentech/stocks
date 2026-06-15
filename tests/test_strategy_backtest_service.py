import json

from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.strategy_backtest_service import StrategyBacktestService
from tests.test_strategy_backtest_fixture import payload


def test_backtest_service_persists_run_trades_report_and_metrics(tmp_path) -> None:
    path = tmp_path / "backtest.json"
    path.write_text(json.dumps(payload()), encoding="utf-8")
    repository = RiskRepository(tmp_path / "risk.sqlite3")

    result = StrategyBacktestService(repository).run_fixture(path)

    assert result["run"].fixture_checksum
    assert repository.get_strategy_backtest_run(result["run"].backtest_run_id) == result["run"]
    assert repository.get_strategy_backtest_report(result["report"].report_id) == result["report"]
    assert repository.list_strategy_backtest_trades(result["run"].backtest_run_id)
    metrics = repository.list_strategy_backtest_metrics(result["run"].backtest_run_id)
    assert metrics == [result["report"].metric]
    assert result["report"].metric == repository.get_strategy_backtest_report(result["report"].report_id).metric
