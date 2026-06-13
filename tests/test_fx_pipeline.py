from datetime import date, datetime

from stock_risk_mcp.analysis_report import build_pipeline_summary_report
from stock_risk_mcp.dashboard import build_pipeline_dashboard
from stock_risk_mcp.fx_risk import apply_fx_to_basket, apply_fx_to_paper_result, apply_fx_to_trade_plan
from stock_risk_mcp.fx_service import FXService
from stock_risk_mcp.models import BacktestOutcome
from stock_risk_mcp.operational_pipeline import OperationalPipeline
from stock_risk_mcp.paper_trading import BasketBacktestResult
from stock_risk_mcp.pipeline_run import PipelineMode, PipelineRun, PipelineRunStatus
from stock_risk_mcp.portfolio_currency import PortfolioCurrencyContext, build_portfolio_currency_context
from stock_risk_mcp.repository import RiskRepository
from tests.test_basket_backtest import _plan
from tests.test_basket_builder import candidate
from tests.test_operational_pipeline import _bars


def test_fx_metadata_propagates_to_trade_basket_paper_and_pipeline(tmp_path) -> None:
    context = _context()
    trade = apply_fx_to_trade_plan({
        "entry_price": 10, "stop_price": 9, "position_size": 10,
        "max_loss_amount": 10, "notional_value": 100,
    }, context)
    basket = apply_fx_to_basket(_plan(), context)
    paper = apply_fx_to_paper_result(BasketBacktestResult(
        basket_id="b", horizon_days=10, entry_date=date(2026, 6, 13), total_notional_value=100,
        total_allocated_loss=10, realized_pnl=5, realized_return_pct=5, win_count=1, loss_count=0,
        flat_count=0, no_data_count=0, closed_trade_count=1, outcome=BacktestOutcome.WIN, created_at=datetime.now(),
    ), context)

    assert trade["account_currency"] == "KRW"
    assert basket.account_currency == "KRW"
    assert basket.risk_summary.total_notional_account is not None
    assert paper.realized_pnl_account == 6900


def test_report_and_dashboard_show_fx_summary(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    run = PipelineRun(
        pipeline_run_id="fx-pipe", mode=PipelineMode.PAPER_BASKET, as_of_date=date(2026, 6, 13),
        status=PipelineRunStatus.COMPLETED, candidate_count=0, included_count=0, watch_count=0,
        basket_allocation_count=0, alert_count=0, created_at=datetime.now(),
        account_currency="KRW", trading_currency="USD", fx_rate=1380, fx_stale=True,
        fx_warnings_json=["FX rate is stale"],
    )
    repository.save_pipeline_run(run)

    report = build_pipeline_summary_report(repository, "fx-pipe")
    build_pipeline_dashboard(repository, "fx-pipe", tmp_path / "dashboard.html")

    assert report.key_metrics["fx_rate"] == 1380
    assert "FX rate is stale" in report.warnings
    assert "FX summary" in (tmp_path / "dashboard.html").read_text(encoding="utf-8")


def test_krw_pipeline_uses_usd_trading_values_and_persists_fx_metadata(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    for ticker in ("AAA", "BBB", "CCC"):
        repository.save_price_bars(_bars(ticker))
    context = build_portfolio_currency_context(
        FXService(repository), "KRW", "USD", date(2026, 1, 20),
        account_equity=10_000_000, cash_available=5_000_000, manual_rate=1380,
    )

    execution = OperationalPipeline(repository).run_paper_basket_pipeline(
        date(2026, 1, 20), context.account_equity_trading, context.cash_available_trading, 10,
        tickers=["AAA", "BBB", "CCC"], save_basket=True, currency_context=context,
    )
    stored = repository.get_basket_plan(execution.basket.basket_id)
    paper = repository.get_basket_backtest_result(execution.basket.basket_id)

    assert round(execution.run.account_equity_trading, 2) == 7246.38
    assert repository.list_candidate_scan_results(execution.run.scan_run_id)[0].metadata["trade_plan"]["account_currency"] == "KRW"
    assert stored.account_currency == "KRW"
    assert stored.allocations[0].notional_account is not None
    assert paper.account_currency == "KRW"


def test_stale_fx_creates_warning_not_critical(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    repository.save_fx_rates([{
        "base_currency": "USD", "quote_currency": "KRW", "date": date(2025, 12, 1),
        "rate": 1380, "source_name": "old",
    }])
    context = build_portfolio_currency_context(
        FXService(repository), "KRW", "USD", date(2026, 1, 20),
        account_equity=10_000_000, cash_available=5_000_000,
    )

    execution = OperationalPipeline(repository).run_paper_basket_pipeline(
        date(2026, 1, 20), context.account_equity_trading, context.cash_available_trading, 10,
        tickers=[], currency_context=context,
    )

    fx_alerts = [item for item in execution.alerts if item.alert_type.value == "FX_WARNING"]
    assert fx_alerts[0].severity.value == "WARNING"


def _context():
    return PortfolioCurrencyContext(
        account_currency="KRW", trading_currency="USD", as_of_date=date(2026, 6, 13),
        fx_rate=1380, fx_date=date(2026, 6, 13), account_equity_input=10_000_000,
        cash_available_input=5_000_000, account_equity_trading=7246.38, cash_available_trading=3623.19,
    )
