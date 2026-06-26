from __future__ import annotations

from collections import defaultdict
from statistics import mean, median

from stock_risk_mcp.paper_evaluation_models import (
    PaperEvaluationEventWindowReport,
    PaperEvaluationMetricsReport,
    PaperEvaluationPipelineInput,
    PaperEvaluationReadinessStatus,
    PaperEvaluationRegimeReport,
    PaperEvaluationRiskReport,
    PaperEvaluationSplitReport,
    PaperEvaluationTrade,
)


def _trade_returns(trades: list[PaperEvaluationTrade]) -> list[float]:
    returns = []
    for trade in trades:
        notional = trade.entry_price * trade.quantity
        if notional > 0 and trade.exit_price is not None:
            returns.append(trade.net_pnl / notional)
    return returns


def build_paper_evaluation_metrics(
    pipeline_input: PaperEvaluationPipelineInput,
    trades: list[PaperEvaluationTrade],
    fills,
    signals,
    snapshots,
) -> tuple[PaperEvaluationMetricsReport, PaperEvaluationRiskReport, PaperEvaluationSplitReport, PaperEvaluationRegimeReport, PaperEvaluationEventWindowReport]:
    completed_trades = [trade for trade in trades if trade.exit_price is not None]
    returns = _trade_returns(completed_trades)
    labeled = pipeline_input.training_dataset_manifest.labeled_row_count > 0
    readiness = PaperEvaluationReadinessStatus.METRICS_READY if labeled else PaperEvaluationReadinessStatus.LABEL_GAP
    win_rate = (sum(1 for trade in completed_trades if trade.net_pnl > 0) / len(completed_trades)) if completed_trades else None
    fill_rate = (sum(1 for fill in fills if getattr(fill.fill_status, "value", str(fill.fill_status)) == "FILLED") / len(fills)) if fills else None
    metrics_report = PaperEvaluationMetricsReport(
        report_id=f"{pipeline_input.dataset_id}-METRICS-REPORT",
        dataset_id=pipeline_input.dataset_id,
        readiness_status=readiness,
        trade_count=len(completed_trades),
        win_rate=win_rate if labeled else None,
        average_return=mean(returns) if returns and labeled else None,
        median_return=median(returns) if returns and labeled else None,
        gross_return=sum(trade.gross_pnl for trade in completed_trades) if labeled else None,
        net_return=sum(trade.net_pnl for trade in completed_trades) if labeled else None,
        profit_factor=(
            sum(trade.net_pnl for trade in completed_trades if trade.net_pnl > 0)
            / abs(sum(trade.net_pnl for trade in completed_trades if trade.net_pnl < 0))
            if labeled and any(trade.net_pnl < 0 for trade in completed_trades)
            else None
        ),
        fill_rate=fill_rate,
        blocked_signal_count=sum(1 for signal in signals if getattr(signal.signal_status, "value", str(signal.signal_status)) != "SIGNAL_READY"),
        gap_count=sum(1 for fill in fills if getattr(fill.fill_status, "value", str(fill.fill_status)) != "FILLED"),
        label_dependent_metrics_available=labeled,
    )
    equity_points = [snapshot.equity for snapshot in snapshots]
    max_equity = max(equity_points) if equity_points else pipeline_input.config.starting_cash
    min_equity = min(equity_points) if equity_points else pipeline_input.config.starting_cash
    risk_report = PaperEvaluationRiskReport(
        report_id=f"{pipeline_input.dataset_id}-RISK-REPORT",
        dataset_id=pipeline_input.dataset_id,
        readiness_status=PaperEvaluationReadinessStatus.RISK_REPORT_READY if labeled else PaperEvaluationReadinessStatus.RESEARCH_ONLY,
        max_drawdown=max(0.0, max_equity - min_equity),
        volatility=(max(returns) - min(returns)) if len(returns) > 1 else 0.0 if labeled else None,
        sharpe_like_ratio=(mean(returns) / ((max(returns) - min(returns)) or 1.0)) if len(returns) > 1 and labeled else None,
        exposure_time=float(sum(1 for snapshot in snapshots if snapshot.open_position_count > 0)),
        turnover=float(sum(fill.gross_notional for fill in fills)),
    )

    by_split: dict[str, list[PaperEvaluationTrade]] = defaultdict(list)
    by_regime: dict[str, list[PaperEvaluationTrade]] = defaultdict(list)
    by_event: dict[str, list[PaperEvaluationTrade]] = defaultdict(list)
    for trade in completed_trades:
        by_split[trade.split_role].append(trade)
        by_regime[trade.regime_label].append(trade)
        by_event[trade.event_window_label].append(trade)

    split_report = PaperEvaluationSplitReport(
        report_id=f"{pipeline_input.dataset_id}-SPLIT-REPORT",
        dataset_id=pipeline_input.dataset_id,
        readiness_status=PaperEvaluationReadinessStatus.SPLIT_REPORT_READY,
        split_metrics={
            key: {"trade_count": len(value), "net_pnl": sum(item.net_pnl for item in value)}
            for key, value in by_split.items()
        },
    )
    regime_report = PaperEvaluationRegimeReport(
        report_id=f"{pipeline_input.dataset_id}-REGIME-REPORT",
        dataset_id=pipeline_input.dataset_id,
        readiness_status=PaperEvaluationReadinessStatus.REGIME_REPORT_READY,
        regime_metrics={
            key: {"trade_count": len(value), "net_pnl": sum(item.net_pnl for item in value)}
            for key, value in by_regime.items()
        },
    )
    event_window_report = PaperEvaluationEventWindowReport(
        report_id=f"{pipeline_input.dataset_id}-EVENT-WINDOW-REPORT",
        dataset_id=pipeline_input.dataset_id,
        readiness_status=PaperEvaluationReadinessStatus.EVENT_WINDOW_REPORT_READY,
        event_window_metrics={
            key: {"trade_count": len(value), "net_pnl": sum(item.net_pnl for item in value)}
            for key, value in by_event.items()
        },
    )
    return metrics_report, risk_report, split_report, regime_report, event_window_report
