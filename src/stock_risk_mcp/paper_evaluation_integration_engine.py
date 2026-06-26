from __future__ import annotations

from stock_risk_mcp.paper_evaluation_fill_engine import build_paper_evaluation_fills
from stock_risk_mcp.paper_evaluation_guard import validate_paper_evaluation_input_gate
from stock_risk_mcp.paper_evaluation_ledger_engine import build_paper_evaluation_ledger
from stock_risk_mcp.paper_evaluation_metrics_engine import build_paper_evaluation_metrics
from stock_risk_mcp.paper_evaluation_models import (
    PaperEvaluationGapReport,
    PaperEvaluationIntegrationReport,
    PaperEvaluationPipelineInput,
    PaperEvaluationPipelineResult,
    PaperEvaluationPlan,
    PaperEvaluationReadinessStatus,
    PaperEvaluationSafetyReport,
)
from stock_risk_mcp.paper_evaluation_portfolio_engine import build_paper_evaluation_portfolio
from stock_risk_mcp.paper_evaluation_signal_engine import build_paper_evaluation_signals


def _has_feature(feature_rows, prefix: str) -> bool:
    return any(row.source_kind.value.startswith(prefix) for row in feature_rows)


def build_paper_evaluation_pipeline(
    pipeline_input: PaperEvaluationPipelineInput,
) -> PaperEvaluationPipelineResult:
    readiness, findings, gaps = validate_paper_evaluation_input_gate(pipeline_input)
    plan = PaperEvaluationPlan(
        plan_id=f"{pipeline_input.dataset_id}-PLAN",
        dataset_id=pipeline_input.dataset_id,
        readiness_status=readiness,
        dataset_profile=pipeline_input.training_dataset_manifest.dataset_profile,
        labeled_dataset=pipeline_input.training_dataset_manifest.labeled_row_count > 0,
        fill_policy=pipeline_input.config.fill_policy,
        split_count=len(pipeline_input.walk_forward_plan.splits),
        gating_findings=findings,
    )
    signals, intents = build_paper_evaluation_signals(pipeline_input)
    fills = build_paper_evaluation_fills(pipeline_input, intents)
    ledger_entries, positions, trades = build_paper_evaluation_ledger(pipeline_input, intents, fills)
    positions, trades, snapshots, equity_curve = build_paper_evaluation_portfolio(pipeline_input, ledger_entries, positions, trades)
    metrics_report, risk_report, split_report, regime_report, event_window_report = build_paper_evaluation_metrics(
        pipeline_input,
        trades,
        fills,
        signals,
        snapshots,
    )
    integration_report = PaperEvaluationIntegrationReport(
        report_id=f"{pipeline_input.dataset_id}-INTEGRATION-REPORT",
        dataset_id=pipeline_input.dataset_id,
        readiness_status=PaperEvaluationReadinessStatus.INTEGRATION_READY,
        v10_manifest_integration_ready=True,
        v10_split_integration_ready=bool(pipeline_input.walk_forward_plan.splits),
        v10_leakage_gate_passed=pipeline_input.leakage_report.readiness_status.value != "BLOCKED_LEAKAGE",
        v8_feature_context_ready=_has_feature(pipeline_input.feature_rows, "V8_"),
        v9_macro_context_ready=_has_feature(pipeline_input.feature_rows, "V9_"),
        v710_position_sizing_context_ready=any(row.source_kind.value == "V7_POSITION_SIZING_CONTEXT" for row in pipeline_input.feature_rows),
        v711_event_risk_context_ready=any(row.source_kind.value == "V7_EVENT_RISK_CONTEXT" for row in pipeline_input.feature_rows),
        v712_outlier_context_ready=any(row.source_kind.value == "V7_OUTLIER_ROUTING_CONTEXT" for row in pipeline_input.feature_rows),
        v713_mock_rehearsal_context_ready=True,
    )
    safety_report = PaperEvaluationSafetyReport(
        report_id=f"{pipeline_input.dataset_id}-SAFETY-REPORT",
        dataset_id=pipeline_input.dataset_id,
        findings=[
            "REPORT_ONLY",
            "LOCAL_ONLY",
            "NO_PROVIDER_CALLS",
            "NO_ENV_READ",
            "NO_ACCOUNT_ORDER_API",
            "NO_EXECUTABLE_OUTPUT",
            "NO_MODEL_TRAINING",
            "NO_BROKER_PAPER_API",
        ],
    )
    gap_report = PaperEvaluationGapReport(
        report_id=f"{pipeline_input.dataset_id}-GAP-REPORT",
        dataset_id=pipeline_input.dataset_id,
        readiness_status=readiness if gaps else PaperEvaluationReadinessStatus.PAPER_EVALUATION_READY,
        gap_entries=gaps,
    )
    return PaperEvaluationPipelineResult(
        plan=plan,
        signals=signals,
        intents=intents,
        fills=fills,
        ledger_entries=ledger_entries,
        positions=positions,
        portfolio_snapshots=snapshots,
        trades=trades,
        equity_curve=equity_curve,
        metrics_report=metrics_report,
        risk_report=risk_report,
        split_report=split_report,
        regime_report=regime_report,
        event_window_report=event_window_report,
        integration_report=integration_report,
        safety_report=safety_report,
        gap_report=gap_report,
    )
