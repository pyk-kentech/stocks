from __future__ import annotations

from collections import defaultdict

from stock_risk_mcp.offline_strategy_artifact_manifest import build_offline_strategy_artifact_manifest
from stock_risk_mcp.offline_strategy_backtest_engine import build_offline_strategy_backtest
from stock_risk_mcp.offline_strategy_dataset_compatibility_engine import (
    build_offline_strategy_dataset_compatibility,
    resolve_offline_strategy_rows,
)
from stock_risk_mcp.offline_strategy_guard import validate_offline_strategy_input_gate
from stock_risk_mcp.offline_strategy_metric_engine import build_offline_strategy_metric_summary
from stock_risk_mcp.offline_strategy_models import (
    OfflineStrategyGapEntry,
    OfflineStrategyGapReport,
    OfflineStrategyPipelineInput,
    OfflineStrategyPipelineResult,
    OfflineStrategyReadinessStatus,
    OfflineStrategySafetyReport,
)
from stock_risk_mcp.offline_strategy_parameter_space import expand_offline_strategy_candidates
from stock_risk_mcp.offline_strategy_promotion_gate import build_offline_strategy_promotion_decision
from stock_risk_mcp.offline_strategy_signal_engine import build_offline_strategy_signals
from stock_risk_mcp.offline_strategy_template_catalog import build_offline_strategy_template_catalog
from stock_risk_mcp.offline_strategy_training_plan_engine import build_offline_strategy_training_plan
from stock_risk_mcp.offline_strategy_walk_forward_engine import build_offline_strategy_walk_forward_result


def _gap(dataset_id: str, suffix: str, category: str, severity: str, message: str) -> OfflineStrategyGapEntry:
    return OfflineStrategyGapEntry(
        gap_id=f"{dataset_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def _candidate_diagnostics(
    pipeline_input: OfflineStrategyPipelineInput,
    candidate,
    rows_by_instrument: dict[str, list],
    candidate_signals,
    backtest_result,
) -> dict[str, int | float | str | bool | None]:
    all_rows = [row for rows in rows_by_instrument.values() for row in rows]
    signal_dates = sorted(signal.observed_at for signal in candidate_signals)
    indicator_columns = sorted(
        {
            key.upper()
            for signal in candidate_signals
            for key, value in signal.signal_features.items()
            if value is not None
        }
    )
    action_counts = defaultdict(int)
    for signal in candidate_signals:
        action_counts[signal.action.value] += 1
    return {
        "input_row_count": len(all_rows),
        "date_range_start": min((row.observed_at.isoformat() for row in all_rows), default=None),
        "date_range_end": max((row.observed_at.isoformat() for row in all_rows), default=None),
        "indicator_columns_available": ",".join(indicator_columns),
        "signal_count_before_filters": len(candidate_signals),
        "entry_signal_count": action_counts.get("ENTER_LONG", 0),
        "exit_signal_count": action_counts.get("EXIT_LONG", 0),
        "blocked_by_hold_count": action_counts.get("HOLD", 0),
        "blocked_by_avoid_long_count": action_counts.get("AVOID_LONG", 0),
        "blocked_by_risk_warning_count": action_counts.get("RISK_WARNING", 0),
        "min_trade_count_threshold": pipeline_input.promotion_gate_config.min_trade_count,
        "actual_trade_count": backtest_result.trade_count,
        "first_signal_date": signal_dates[0].isoformat() if signal_dates else None,
        "last_signal_date": signal_dates[-1].isoformat() if signal_dates else None,
    }


def build_offline_strategy_pipeline(pipeline_input: OfflineStrategyPipelineInput) -> OfflineStrategyPipelineResult:
    gate_status, findings, gaps = validate_offline_strategy_input_gate(pipeline_input)
    rows = resolve_offline_strategy_rows(pipeline_input)
    dataset_compatibility_report = build_offline_strategy_dataset_compatibility(pipeline_input, rows)
    template_catalog = build_offline_strategy_template_catalog()
    selected_templates = [
        template
        for template in template_catalog
        if not pipeline_input.requested_template_ids or template.template_id in set(pipeline_input.requested_template_ids)
    ]
    candidates = []
    for template in selected_templates:
        expanded = expand_offline_strategy_candidates(pipeline_input.dataset_id, template, pipeline_input.asset_liquidity_profile)
        if pipeline_input.search_mode == "SMOKE_SEARCH":
            expanded = expanded[:1]
        candidates.extend(expanded)
    training_plan = build_offline_strategy_training_plan(pipeline_input, len(candidates))
    walk_forward_result = build_offline_strategy_walk_forward_result(pipeline_input, rows)
    rows_by_instrument = defaultdict(list)
    for row in sorted(rows, key=lambda item: item.observed_at):
        rows_by_instrument[row.instrument_id].append(row)
    signals = []
    intents = []
    backtest_results = []
    metric_summaries = []
    promotion_decisions = []
    for candidate in candidates:
        candidate_signals = build_offline_strategy_signals(pipeline_input.dataset_id, rows_by_instrument, candidate)
        signals.extend(candidate_signals)
        candidate_intents, backtest_result = build_offline_strategy_backtest(
            pipeline_input.dataset_id,
            rows_by_instrument,
            candidate,
            candidate_signals,
            pipeline_input.fee_bps,
            pipeline_input.slippage_bps,
        )
        intents.extend(candidate_intents)
        backtest_results.append(backtest_result)
        metric_summary = build_offline_strategy_metric_summary(pipeline_input.dataset_id, backtest_result)
        metric_summaries.append(metric_summary)
        promotion_decisions.append(
            build_offline_strategy_promotion_decision(
                pipeline_input,
                candidate,
                backtest_result,
                metric_summary,
                diagnostics=_candidate_diagnostics(pipeline_input, candidate, rows_by_instrument, candidate_signals, backtest_result),
            )
        )
    artifact_manifest = build_offline_strategy_artifact_manifest(pipeline_input.dataset_id)
    safety_report = OfflineStrategySafetyReport(
        report_id=f"{pipeline_input.dataset_id}-OFFLINE-STRATEGY-SAFETY-REPORT",
        readiness_status=OfflineStrategyReadinessStatus.PROMOTION_GATE_READY,
        findings=[
            "offline strategy pipeline is manifest-first",
            "no network access",
            "no credential or env reads",
            "no account/order/broker path",
            "trade intents remain non-executable",
        ],
    )
    gap_entries = [_gap(pipeline_input.dataset_id, f"GAP-{index}", "DATA_GAP", "WARNING", gap) for index, gap in enumerate(gaps, start=1)]
    if gate_status != OfflineStrategyReadinessStatus.DATASET_COMPATIBILITY_READY:
        gap_entries.append(_gap(pipeline_input.dataset_id, "INPUT-GATE", "INPUT_GATE", "WARNING", gate_status.value))
    gap_report = OfflineStrategyGapReport(
        report_id=f"{pipeline_input.dataset_id}-OFFLINE-STRATEGY-GAP-REPORT",
        readiness_status=OfflineStrategyReadinessStatus.RESEARCH_ONLY if gap_entries else OfflineStrategyReadinessStatus.PROMOTION_GATE_READY,
        gap_entries=gap_entries,
    )
    return OfflineStrategyPipelineResult(
        template_catalog=selected_templates,
        dataset_compatibility_report=dataset_compatibility_report,
        training_plan=training_plan,
        candidates=candidates,
        walk_forward_result=walk_forward_result,
        signals=signals,
        intents=intents,
        backtest_results=backtest_results,
        metric_summaries=metric_summaries,
        promotion_decisions=promotion_decisions,
        artifact_manifest=artifact_manifest,
        safety_report=safety_report,
        gap_report=gap_report,
    )
