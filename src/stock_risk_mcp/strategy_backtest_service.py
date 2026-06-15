from __future__ import annotations

import hashlib
from pathlib import Path

from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.strategy_backtest import StrategyBacktestRun, run_strategy_backtest
from stock_risk_mcp.strategy_backtest_fixture import load_strategy_backtest_fixture


class StrategyBacktestService:
    def __init__(self, repository: RiskRepository) -> None:
        self.repository = repository

    def run_fixture(self, path: str | Path) -> dict:
        selected = Path(path)
        fixture = load_strategy_backtest_fixture(selected)
        report = run_strategy_backtest(fixture)
        run = StrategyBacktestRun(
            backtest_run_id=report.backtest_run_id,
            fixture_checksum=hashlib.sha256(selected.read_bytes()).hexdigest(),
            initial_cash=fixture.backtest_config.initial_cash,
            final_cash=fixture.backtest_config.initial_cash * (1 + report.metric.total_return_pct / 100),
            decision_count=len(report.decisions),
        )
        self.repository.save_strategy_backtest_run(run)
        for trade in report.trades:
            self.repository.save_strategy_backtest_trade(trade)
        self.repository.save_strategy_backtest_metric(report.metric)
        self.repository.save_strategy_backtest_report(report)
        return {"run": run, "report": report}
