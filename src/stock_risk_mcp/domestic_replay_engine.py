from __future__ import annotations

from stock_risk_mcp.domestic_candidate_evaluation_engine import build_candidate_evaluation_report
from stock_risk_mcp.domestic_realtime_engine import build_domestic_realtime_quality_report, normalize_domestic_realtime_events
from stock_risk_mcp.domestic_replay_models import (
    DOMESTIC_REPLAY_METADATA,
    DomesticReplayFixture,
    ReplayCandidateTrace,
    ReplayEvaluationMetrics,
    ReplayEvaluationReport,
    ReplayPromotionReadinessReport,
    ReplayPromotionReadinessStatus,
    ReplayQualityGate,
    ReplayStepResult,
    ReplayValidationReport,
    ReplayWindow,
)
from stock_risk_mcp.domestic_scanner_models import ScannerCandidateState
from stock_risk_mcp.strategy_track_models import StrategyTrack


def build_domestic_replay_validation_report(fixture: DomesticReplayFixture) -> ReplayValidationReport:
    market_id = fixture.domestic_candidate_evaluation_fixture.domestic_scanner_fixture.domestic_realtime_fixture.strategy_request.market_profile.market_id
    return ReplayValidationReport(
        config_id=fixture.replay_config.config_id,
        strategy_track=fixture.replay_config.strategy_track,
        market_id=market_id,
        sequence_id=fixture.replay_event_sequence.sequence_id,
        event_count=len(fixture.replay_event_sequence.ordered_event_ids),
        ordering_policy=fixture.replay_config.replay_ordering_mode.value,
    )


def _event_sort_key(ordering_mode, event) -> tuple:
    if ordering_mode.value == "RECEIVED_TIMESTAMP_THEN_PROVIDER":
        return (event.received_timestamp, event.provider_timestamp, event.source_fixture_id)
    return (event.provider_timestamp, event.received_timestamp, event.source_fixture_id)


def _sorted_events(fixture: DomesticReplayFixture):
    events = list(fixture.domestic_candidate_evaluation_fixture.domestic_scanner_fixture.domestic_realtime_fixture.events)
    if fixture.replay_config.duplicate_event_policy.value == "REJECT_EXACT_DUPLICATE_EVENT_ID":
        source_ids = [event.source_fixture_id for event in events]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("duplicate source_fixture_id is not allowed under replay duplicate policy")
    return sorted(events, key=lambda event: _event_sort_key(fixture.replay_config.replay_ordering_mode, event))


def _single_event_fixture(fixture: DomesticReplayFixture, event):
    payload = fixture.domestic_candidate_evaluation_fixture.model_dump(mode="python")
    payload["domestic_scanner_fixture"]["domestic_realtime_fixture"]["events"] = [event.model_dump(mode="python")]
    payload["domestic_scanner_fixture"]["domestic_realtime_fixture"]["run_id"] = (
        f"{payload['domestic_scanner_fixture']['domestic_realtime_fixture']['run_id']}-{event.source_fixture_id}"
    )
    payload["domestic_scanner_fixture"]["run_id"] = f"{payload['domestic_scanner_fixture']['run_id']}-{event.source_fixture_id}"
    payload["run_id"] = f"{payload['run_id']}-{event.source_fixture_id}"
    return fixture.domestic_candidate_evaluation_fixture.__class__.model_validate(payload)


def _report_only_reasons(decision) -> list[str]:
    reasons = []
    if decision.evaluation_state.value == "REPORT_ONLY":
        reasons.append("STALE_REPORT_ONLY")
    return reasons


def _blocked_reasons(decision) -> list[str]:
    return list(decision.block_reasons)


def _non_actionable_reasons(decision) -> list[str]:
    reasons = ["REPLAY_DIAGNOSTIC_ONLY", "ORDER_CREATION_DISABLED"]
    reasons.extend(_report_only_reasons(decision))
    reasons.extend(_blocked_reasons(decision))
    return sorted(set(reasons))


def _quality_gate(scanner_candidate) -> ReplayQualityGate:
    return ReplayQualityGate(
        freshness_gate=scanner_candidate.quality_gate.freshness_gate,
        completeness_gate=scanner_candidate.quality_gate.completeness_gate,
        safety_gate=scanner_candidate.quality_gate.unsafe_trigger_gate,
        report_only_gate=scanner_candidate.quality_gate.report_only_downgrade_gate,
        preserved_quality_flags=list(scanner_candidate.quality_gate.preserved_quality_flags),
    )


def _step_result(fixture: DomesticReplayFixture, index: int, event) -> ReplayStepResult:
    scoped_fixture = _single_event_fixture(fixture, event)
    normalized_event = normalize_domestic_realtime_events(
        scoped_fixture.domestic_scanner_fixture.domestic_realtime_fixture
    )[0]
    quality = build_domestic_realtime_quality_report(
        scoped_fixture.domestic_scanner_fixture.domestic_realtime_fixture
    )
    evaluation = build_candidate_evaluation_report(scoped_fixture)
    decision = evaluation.decisions[0]
    scanner_snapshot = quality.scanner_input_snapshots[0]
    from stock_risk_mcp.domestic_scanner_engine import build_domestic_scanner_candidates

    scanner_report_full = build_domestic_scanner_candidates(scoped_fixture.domestic_scanner_fixture)
    scanner_candidate_model = scanner_report_full.candidates[0]
    trace = ReplayCandidateTrace(
        source_event_ids=[event.source_fixture_id],
        scanner_input_snapshot_id=scanner_candidate_model.snapshot_id,
        scanner_candidate_id=scanner_candidate_model.candidate_id,
        scanner_state=scanner_candidate_model.internal_state,
        scanner_compatibility_status=scanner_candidate_model.compatibility_discovery_status,
        evaluation_state=decision.evaluation_state,
        evaluation_compatibility_status=decision.evaluation_compatibility_status,
        blocked_reasons=_blocked_reasons(decision),
        report_only_reasons=_report_only_reasons(decision),
        non_actionable_reasons=_non_actionable_reasons(decision),
        data_quality_flags=list(scanner_candidate_model.preserved_quality_flags),
        non_actionable=True,
    )
    return ReplayStepResult(
        replay_step_id=f"{fixture.run_id}-step-{index}",
        source_event_id=event.source_fixture_id,
        replay_clock_timestamp=max(event.provider_timestamp, event.received_timestamp),
        normalized_event_state=normalized_event,
        scanner_input_snapshot=scanner_snapshot.model_dump(mode="json"),
        scanner_candidate_trace=trace,
        candidate_evaluation_trace={
            "candidate_id": decision.candidate_id,
            "ticker": decision.ticker,
            "scanner_state": decision.scanner_state.value,
            "scanner_compatibility_status": decision.scanner_compatibility_status.value,
            "evaluation_state": decision.evaluation_state.value,
            "evaluation_compatibility_status": decision.evaluation_compatibility_status.value,
            "quality_gate": _quality_gate(scanner_candidate_model).model_dump(mode="json"),
        },
        blocked_reasons=trace.blocked_reasons,
        report_only_reasons=trace.report_only_reasons,
        non_actionable_reasons=trace.non_actionable_reasons,
        data_quality_flags=trace.data_quality_flags,
    )


def _window_metrics(step_results: list[ReplayStepResult]) -> dict:
    scanner_counts: dict[str, int] = {}
    evaluation_counts: dict[str, int] = {}
    for step in step_results:
        scanner_state = step.scanner_candidate_trace.scanner_state.value
        evaluation_state = step.scanner_candidate_trace.evaluation_state.value
        scanner_counts[scanner_state] = scanner_counts.get(scanner_state, 0) + 1
        evaluation_counts[evaluation_state] = evaluation_counts.get(evaluation_state, 0) + 1
    return {
        "events_processed": len(step_results),
        "valid_events": sum(1 for step in step_results if "STALE_EVENT" not in step.data_quality_flags and "IMPOSSIBLE_TIMESTAMP" not in step.data_quality_flags and "TIMESTAMP_MISMATCH" not in step.data_quality_flags),
        "stale_events": sum(1 for step in step_results if "STALE_EVENT" in step.data_quality_flags),
        "invalid_events": sum(1 for step in step_results if "IMPOSSIBLE_TIMESTAMP" in step.data_quality_flags or "TIMESTAMP_MISMATCH" in step.data_quality_flags),
        "candidates_generated": len(step_results),
        "candidates_by_scanner_state": scanner_counts,
        "candidates_by_evaluation_state": evaluation_counts,
        "blocked_candidates": sum(1 for step in step_results if step.blocked_reasons),
        "report_only_candidates": sum(1 for step in step_results if step.report_only_reasons),
        "watchlist_add_remove_counts": {
            "add": sum(1 for step in step_results if step.scanner_candidate_trace.scanner_state.value == "WATCHLIST_ADD"),
            "remove": sum(1 for step in step_results if step.scanner_candidate_trace.scanner_state.value == "WATCHLIST_REMOVE"),
        },
        "unsafe_trigger_rejections": sum(1 for step in step_results if step.scanner_candidate_trace.scanner_state.value == "REJECTED_UNSAFE_TRIGGER"),
        "profitability_blocked_count": sum(1 for step in step_results if step.scanner_candidate_trace.evaluation_state.value == "BLOCKED_PROFITABILITY"),
        "technical_evidence_blocked_count": sum(1 for step in step_results if step.scanner_candidate_trace.evaluation_state.value == "BLOCKED_TECHNICAL_EVIDENCE"),
        "non_actionable_candidate_count": len(step_results),
    }


def _build_windows(fixture: DomesticReplayFixture, step_results: list[ReplayStepResult]) -> list[ReplayWindow]:
    size = fixture.replay_config.replay_window_size
    windows: list[ReplayWindow] = []
    for start in range(0, len(step_results), size):
        chunk = step_results[start:start + size]
        if not chunk:
            continue
        windows.append(
            ReplayWindow(
                window_id=f"{fixture.run_id}-window-{len(windows) + 1}",
                window_start=chunk[0].replay_clock_timestamp,
                window_end=chunk[-1].replay_clock_timestamp,
                included_event_ids=[item.source_event_id for item in chunk],
                aggregated_summary_metrics=_window_metrics(chunk),
                warnings=sorted({reason for item in chunk for reason in item.report_only_reasons}),
                block_reasons=sorted({reason for item in chunk for reason in item.blocked_reasons}),
            )
        )
    return windows


def build_domestic_replay_metrics(step_results: list[ReplayStepResult]) -> ReplayEvaluationMetrics:
    scanner_counts: dict[str, int] = {}
    evaluation_counts: dict[str, int] = {}
    for step in step_results:
        scanner_state = step.scanner_candidate_trace.scanner_state.value
        evaluation_state = step.scanner_candidate_trace.evaluation_state.value
        scanner_counts[scanner_state] = scanner_counts.get(scanner_state, 0) + 1
        evaluation_counts[evaluation_state] = evaluation_counts.get(evaluation_state, 0) + 1
    return ReplayEvaluationMetrics(
        total_events_processed=len(step_results),
        valid_events=sum(1 for step in step_results if "STALE_EVENT" not in step.data_quality_flags and "IMPOSSIBLE_TIMESTAMP" not in step.data_quality_flags and "TIMESTAMP_MISMATCH" not in step.data_quality_flags),
        stale_events=sum(1 for step in step_results if "STALE_EVENT" in step.data_quality_flags),
        invalid_events=sum(1 for step in step_results if "IMPOSSIBLE_TIMESTAMP" in step.data_quality_flags or "TIMESTAMP_MISMATCH" in step.data_quality_flags),
        generated_scanner_candidates=len(step_results),
        candidates_by_scanner_state=scanner_counts,
        candidates_by_evaluation_state=evaluation_counts,
        blocked_candidate_count=sum(1 for step in step_results if step.blocked_reasons),
        report_only_candidate_count=sum(1 for step in step_results if step.report_only_reasons),
        watchlist_add_count=scanner_counts.get("WATCHLIST_ADD", 0),
        watchlist_remove_count=scanner_counts.get("WATCHLIST_REMOVE", 0),
        domestic_only_rejection_count=scanner_counts.get("REJECTED_NON_DOMESTIC", 0),
        unsafe_trigger_rejection_count=scanner_counts.get("REJECTED_UNSAFE_TRIGGER", 0),
        quality_failure_count=scanner_counts.get("BLOCKED_QUALITY", 0),
        profitability_blocked_count=evaluation_counts.get("BLOCKED_PROFITABILITY", 0),
        technical_evidence_blocked_count=evaluation_counts.get("BLOCKED_TECHNICAL_EVIDENCE", 0),
        non_actionable_candidate_count=len(step_results),
    )


def build_domestic_replay_report(fixture: DomesticReplayFixture) -> ReplayEvaluationReport:
    if fixture.replay_config.strategy_track != StrategyTrack.DOMESTIC_KR:
        raise ValueError("domestic replay requires StrategyTrack DOMESTIC_KR")
    events = _sorted_events(fixture)
    step_results = [_step_result(fixture, index, event) for index, event in enumerate(events, start=1)]
    windows = _build_windows(fixture, step_results)
    metrics = build_domestic_replay_metrics(step_results)
    warnings = sorted({reason for step in step_results for reason in step.report_only_reasons})
    block_reasons = sorted({reason for step in step_results for reason in step.blocked_reasons})
    market_profile = fixture.domestic_candidate_evaluation_fixture.domestic_scanner_fixture.domestic_realtime_fixture.strategy_request.market_profile
    return ReplayEvaluationReport(
        report_id=f"{fixture.run_id}-report",
        strategy_track=fixture.replay_config.strategy_track,
        market_profile_summary=market_profile.model_dump(mode="json"),
        event_sequence_summary={
            "sequence_id": fixture.replay_event_sequence.sequence_id,
            "ordered_event_ids": [event.source_fixture_id for event in events],
            "event_count": len(events),
        },
        step_results=step_results,
        windows=windows,
        metrics=metrics,
        warnings=warnings,
        block_reasons=block_reasons,
        metadata_json=dict(DOMESTIC_REPLAY_METADATA),
    )


def build_domestic_replay_promotion_readiness_report(
    fixture: DomesticReplayFixture,
) -> ReplayPromotionReadinessReport:
    report = build_domestic_replay_report(fixture)
    metrics = report.metrics
    warnings = list(report.warnings)
    block_reasons = list(report.block_reasons)
    status = ReplayPromotionReadinessStatus.REPLAY_PASS
    if metrics.total_events_processed < fixture.replay_config.replay_window_size:
        status = ReplayPromotionReadinessStatus.REPLAY_INSUFFICIENT_COVERAGE
        block_reasons.append("INSUFFICIENT_EVENT_COVERAGE")
    elif metrics.unsafe_trigger_rejection_count or metrics.domestic_only_rejection_count:
        status = ReplayPromotionReadinessStatus.REPLAY_BLOCKED_SAFETY
    elif metrics.quality_failure_count or metrics.invalid_events:
        status = ReplayPromotionReadinessStatus.REPLAY_BLOCKED_QUALITY
    elif metrics.report_only_candidate_count:
        status = ReplayPromotionReadinessStatus.REPLAY_REPORT_ONLY
    elif warnings:
        status = ReplayPromotionReadinessStatus.REPLAY_PASS_WITH_WARNINGS
    return ReplayPromotionReadinessReport(
        report_id=f"{report.report_id}-promotion-readiness",
        strategy_track=report.strategy_track,
        readiness_status=status,
        coverage_event_count=metrics.total_events_processed,
        warnings=sorted(set(warnings)),
        block_reasons=sorted(set(block_reasons)),
        metadata_json=dict(DOMESTIC_REPLAY_METADATA),
    )
