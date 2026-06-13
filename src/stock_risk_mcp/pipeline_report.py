from stock_risk_mcp.pipeline_run import AlertSeverity, PipelineAlert, PipelineRun, PipelineSummary


def build_pipeline_summary(
    run: PipelineRun,
    alerts: list[PipelineAlert],
    *,
    basket_decision: str | None = None,
    paper_outcome: str | None = None,
    realized_return_pct: float | None = None,
    policy_recommendation: str | None = None,
) -> PipelineSummary:
    severity_rank = {
        AlertSeverity.CRITICAL: 4,
        AlertSeverity.HIGH: 3,
        AlertSeverity.WARNING: 2,
        AlertSeverity.INFO: 1,
    }
    return PipelineSummary(
        pipeline_run_id=run.pipeline_run_id,
        status=run.status,
        as_of_date=run.as_of_date,
        candidate_count=run.candidate_count,
        included_count=run.included_count,
        watch_count=run.watch_count,
        basket_decision=basket_decision,
        basket_allocation_count=run.basket_allocation_count,
        paper_outcome=paper_outcome,
        realized_return_pct=realized_return_pct,
        policy_recommendation=policy_recommendation,
        alert_count=len(alerts),
        top_alerts=sorted(alerts, key=lambda item: severity_rank[item.severity], reverse=True)[:10],
        notes=run.notes,
    )
