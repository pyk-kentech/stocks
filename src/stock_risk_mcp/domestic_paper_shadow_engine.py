from __future__ import annotations

from stock_risk_mcp.domestic_calibration_models import PromotionGateStatus
from stock_risk_mcp.domestic_candidate_evaluation_models import CandidateEvaluationState
from stock_risk_mcp.domestic_paper_shadow_models import (
    DOMESTIC_PAPER_SHADOW_METADATA,
    DomesticPaperShadowFixture,
    PaperShadowDecision,
    PaperShadowDecisionJournal,
    PaperShadowDecisionReason,
    PaperShadowDecisionType,
    PaperShadowGapReport,
    PaperShadowReviewReport,
    PaperShadowSafetyBoundary,
    PaperShadowSafetyReport,
    PaperShadowValidationReport,
)


def build_domestic_paper_shadow_validation_report(
    fixture: DomesticPaperShadowFixture,
) -> PaperShadowValidationReport:
    return PaperShadowValidationReport(
        config_id=fixture.paper_shadow_config.config_id,
        strategy_track=fixture.paper_shadow_config.strategy_track,
        market_id=str(fixture.paper_shadow_input_set.market_profile_summary["market_id"]).upper(),
        candidate_evaluation_report_count=len(fixture.paper_shadow_input_set.candidate_evaluation_reports),
    )


def _gate_block_reasons(fixture: DomesticPaperShadowFixture) -> list[str]:
    gate = fixture.paper_shadow_input_set.promotion_gate_report
    block_reasons: list[str] = []
    if gate.gate_status != PromotionGateStatus.PROMOTION_READY_FOR_PAPER_SHADOW:
        block_reasons.append(gate.gate_status.value)
    if "SINGLE_RUN_ONLY_EVIDENCE" in gate.block_reasons:
        block_reasons.append("SINGLE_RUN_ONLY_EVIDENCE")
    return sorted(set(block_reasons))


def _decision_type(decision) -> PaperShadowDecisionType:
    state = decision.evaluation_state
    if state == CandidateEvaluationState.EVALUATION_READY:
        return PaperShadowDecisionType.SHADOW_WATCH
    if state == CandidateEvaluationState.WATCH_ONLY:
        return PaperShadowDecisionType.SHADOW_WATCH
    if state == CandidateEvaluationState.REPORT_ONLY:
        return PaperShadowDecisionType.SHADOW_REPORT_ONLY
    if state == CandidateEvaluationState.BLOCKED_SCANNER_QUALITY or state == CandidateEvaluationState.BLOCKED_STALE_DATA:
        return PaperShadowDecisionType.SHADOW_BLOCKED_QUALITY
    if state == CandidateEvaluationState.BLOCKED_PROFITABILITY:
        return PaperShadowDecisionType.SHADOW_BLOCKED_PROFITABILITY
    if state == CandidateEvaluationState.BLOCKED_TECHNICAL_EVIDENCE:
        return PaperShadowDecisionType.SHADOW_BLOCKED_TECHNICAL_EVIDENCE
    if state == CandidateEvaluationState.BLOCKED_RISK:
        return PaperShadowDecisionType.SHADOW_BLOCKED_RISK
    if state in {CandidateEvaluationState.REJECTED_UNSAFE_TRIGGER, CandidateEvaluationState.REJECTED_NON_DOMESTIC}:
        return PaperShadowDecisionType.SHADOW_BLOCKED_SAFETY
    if state == CandidateEvaluationState.INSUFFICIENT_CONTEXT:
        return PaperShadowDecisionType.SHADOW_INSUFFICIENT_CONTEXT
    return PaperShadowDecisionType.SHADOW_REJECT


def _decision_reasons(source_report_id: str, decision_type: PaperShadowDecisionType, decision) -> list[PaperShadowDecisionReason]:
    reasons = [
        PaperShadowDecisionReason(
            reason_code=decision_type.value,
            reason_category="CANDIDATE_EVALUATION",
            source_layer="V4.4",
            explanatory_summary=f"Mapped from {decision.evaluation_state.value}",
        )
    ]
    if decision.profitability_score.blocked_reason:
        reasons.append(
            PaperShadowDecisionReason(
                reason_code=decision.profitability_score.blocked_reason,
                reason_category="PROFITABILITY",
                source_layer="V4.1",
                explanatory_summary="Non-actionable profitability context preserved",
            )
        )
    return reasons


def build_paper_shadow_journal(fixture: DomesticPaperShadowFixture) -> PaperShadowDecisionJournal:
    gate_block_reasons = _gate_block_reasons(fixture)
    if gate_block_reasons:
        raise ValueError(f"paper shadow journaling blocked: {', '.join(gate_block_reasons)}")
    entries: list[PaperShadowDecision] = []
    for report in fixture.paper_shadow_input_set.candidate_evaluation_reports:
        for index, decision in enumerate(report.decisions, start=1):
            decision_type = _decision_type(decision)
            entries.append(
                PaperShadowDecision(
                    journal_entry_id=f"{fixture.run_id}-entry-{len(entries) + 1}",
                    fixture_id=fixture.run_id,
                    strategy_track=fixture.paper_shadow_config.strategy_track,
                    market_profile_id=str(report.market_profile_summary.get("market_id", "KRX")).upper(),
                    candidate_id=decision.candidate_id,
                    source_scanner_candidate_id=decision.candidate_id,
                    source_evaluation_report_id=report.report_id,
                    source_promotion_gate_id=fixture.paper_shadow_input_set.promotion_gate_report.report_id,
                    decision_type=decision_type,
                    reasons=_decision_reasons(report.report_id, decision_type, decision),
                    blocked_reasons=list(decision.block_reasons),
                    report_only_reasons=[warning for warning in decision.warnings if "REPORT_ONLY" in warning],
                    non_actionable_reasons=["NON_EXECUTABLE_JOURNAL", *list(decision.block_reasons)],
                    non_actionable=True,
                    data_quality_flags=list(decision.warnings),
                    decision_timestamp=fixture.created_at,
                    technical_evidence_context_summary=decision.technical_score.model_dump(mode="json"),
                    profitability_context_summary=decision.profitability_score.model_dump(mode="json"),
                    risk_safety_context_summary=decision.risk_signal.model_dump(mode="json"),
                )
            )
    return PaperShadowDecisionJournal(
        journal_id=f"{fixture.run_id}-journal",
        strategy_track=fixture.paper_shadow_config.strategy_track,
        market_profile_summary=fixture.paper_shadow_input_set.market_profile_summary,
        promotion_gate_status=fixture.paper_shadow_input_set.promotion_gate_report.gate_status,
        source_candidate_evaluation_report_ids=[report.report_id for report in fixture.paper_shadow_input_set.candidate_evaluation_reports],
        source_replay_calibration_provenance_markers=list(fixture.paper_shadow_input_set.replay_provenance_markers),
        entries=entries,
        entry_count=len(entries),
        warnings=sorted({warning for entry in entries for warning in entry.report_only_reasons}),
        block_reasons=[],
        safety_boundary=PaperShadowSafetyBoundary(),
        metadata_json=dict(DOMESTIC_PAPER_SHADOW_METADATA),
    )


def build_paper_shadow_review_report(fixture: DomesticPaperShadowFixture) -> PaperShadowReviewReport:
    journal = build_paper_shadow_journal(fixture)
    decision_type_counts: dict[str, int] = {}
    blocked_reason_counts: dict[str, int] = {}
    report_only_reason_counts: dict[str, int] = {}
    non_actionable_reason_counts: dict[str, int] = {}
    symbol_counts: dict[str, int] = {}
    replay_window_counts: dict[str, int] = {}
    for entry in journal.entries:
        decision_type_counts[entry.decision_type.value] = decision_type_counts.get(entry.decision_type.value, 0) + 1
        symbol_counts[entry.candidate_id] = symbol_counts.get(entry.candidate_id, 0) + 1
        replay_window_counts["FIXTURE_WINDOW"] = replay_window_counts.get("FIXTURE_WINDOW", 0) + 1
        for reason in entry.blocked_reasons:
            blocked_reason_counts[reason] = blocked_reason_counts.get(reason, 0) + 1
        for reason in entry.report_only_reasons:
            report_only_reason_counts[reason] = report_only_reason_counts.get(reason, 0) + 1
        for reason in entry.non_actionable_reasons:
            non_actionable_reason_counts[reason] = non_actionable_reason_counts.get(reason, 0) + 1
    return PaperShadowReviewReport(
        review_report_id=f"{journal.journal_id}-review",
        journal_reference=journal.journal_id,
        total_journal_entries=journal.entry_count,
        shadow_watch_count=decision_type_counts.get(PaperShadowDecisionType.SHADOW_WATCH.value, 0),
        rejected_count=decision_type_counts.get(PaperShadowDecisionType.SHADOW_REJECT.value, 0),
        report_only_count=decision_type_counts.get(PaperShadowDecisionType.SHADOW_REPORT_ONLY.value, 0),
        blocked_quality_count=decision_type_counts.get(PaperShadowDecisionType.SHADOW_BLOCKED_QUALITY.value, 0),
        blocked_profitability_count=decision_type_counts.get(PaperShadowDecisionType.SHADOW_BLOCKED_PROFITABILITY.value, 0),
        blocked_technical_evidence_count=decision_type_counts.get(PaperShadowDecisionType.SHADOW_BLOCKED_TECHNICAL_EVIDENCE.value, 0),
        blocked_risk_count=decision_type_counts.get(PaperShadowDecisionType.SHADOW_BLOCKED_RISK.value, 0),
        blocked_safety_count=decision_type_counts.get(PaperShadowDecisionType.SHADOW_BLOCKED_SAFETY.value, 0),
        insufficient_context_count=decision_type_counts.get(PaperShadowDecisionType.SHADOW_INSUFFICIENT_CONTEXT.value, 0),
        non_actionable_count=sum(1 for entry in journal.entries if entry.non_actionable),
        candidate_coverage_count=len({entry.candidate_id for entry in journal.entries}),
        scenario_family_coverage_count=len(set(fixture.paper_shadow_input_set.scenario_family_markers)),
        decision_type_counts=decision_type_counts,
        replay_window_counts=replay_window_counts,
        scenario_family_counts={marker: 1 for marker in fixture.paper_shadow_input_set.scenario_family_markers},
        symbol_counts=symbol_counts,
        blocked_reason_counts=blocked_reason_counts,
        report_only_reason_counts=report_only_reason_counts,
        non_actionable_reason_counts=non_actionable_reason_counts,
        promotion_gate_status_counts={fixture.paper_shadow_input_set.promotion_gate_report.gate_status.value: journal.entry_count},
        advisory_context_placeholders={
            "supported_tracks_required": True,
            "non_executable_context_only": True,
            "trade_instruction_conversion_allowed": False,
        },
        metadata_json=dict(DOMESTIC_PAPER_SHADOW_METADATA),
    )


def build_paper_shadow_safety_report(fixture: DomesticPaperShadowFixture) -> PaperShadowSafetyReport:
    return PaperShadowSafetyReport(
        report_id=f"{fixture.run_id}-paper-shadow-safety",
        strategy_track=fixture.paper_shadow_config.strategy_track,
        safety_boundary=PaperShadowSafetyBoundary(),
        block_reasons=_gate_block_reasons(fixture),
        warnings=[],
        metadata_json=dict(DOMESTIC_PAPER_SHADOW_METADATA),
    )


def build_paper_shadow_gap_report(fixture: DomesticPaperShadowFixture) -> PaperShadowGapReport:
    gate_block_reasons = _gate_block_reasons(fixture)
    reports = fixture.paper_shadow_input_set.candidate_evaluation_reports
    unsafe_attempts = sum(
        1
        for report in reports
        for decision in report.decisions
        if decision.evaluation_state.value == "REJECTED_UNSAFE_TRIGGER"
    )
    return PaperShadowGapReport(
        gap_report_id=f"{fixture.run_id}-paper-shadow-gap",
        missing_promotion_gate_evidence_count=0,
        missing_candidate_evaluation_count=0 if reports else 1,
        blocked_promotion_gate_count=1 if gate_block_reasons else 0,
        single_run_only_evidence_count=1 if "SINGLE_RUN_ONLY_EVIDENCE" in gate_block_reasons else 0,
        missing_market_profile_count=0,
        missing_strategy_track_count=0,
        unsafe_trigger_attempt_count=unsafe_attempts,
        gap_reasons=gate_block_reasons,
        metadata_json=dict(DOMESTIC_PAPER_SHADOW_METADATA),
    )
