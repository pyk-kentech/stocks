from __future__ import annotations

from stock_risk_mcp.domestic_candidate_evaluation_models import (
    DOMESTIC_CANDIDATE_EVALUATION_METADATA,
    CandidateEvaluationCompatibility,
    CandidateEvaluationDecision,
    CandidateEvaluationGapReport,
    CandidateEvaluationReport,
    CandidateEvaluationSafetyBoundary,
    CandidateEvaluationSafetyReport,
    CandidateEvaluationState,
    CandidateEvaluationValidationReport,
    CandidateProfitabilityScore,
    CandidateRiskSignal,
    CandidateTechnicalScore,
    DomesticCandidateEvaluationFixture,
)
from stock_risk_mcp.domestic_scanner_engine import build_domestic_scanner_candidates
from stock_risk_mcp.domestic_scanner_models import ScannerCandidateState


def build_candidate_evaluation_validation_report(
    fixture: DomesticCandidateEvaluationFixture,
) -> CandidateEvaluationValidationReport:
    return CandidateEvaluationValidationReport(
        config_id=fixture.evaluation_config.config_id,
        strategy_track=fixture.evaluation_config.strategy_track,
        market_id=fixture.domestic_scanner_fixture.domestic_realtime_fixture.strategy_request.market_profile.market_id,
        provider_id=fixture.domestic_scanner_fixture.domestic_realtime_fixture.provider_profile.provider_id,
    )


def _technical_score(fixture: DomesticCandidateEvaluationFixture) -> CandidateTechnicalScore:
    context = fixture.technical_evidence_context
    score = 100
    warnings: list[str] = []
    if context.setup_grade == "B":
        score = 75
    elif context.setup_grade in {"C", "D", None}:
        score = 40
    if context.evidence_freshness == "STALE_FIXTURE":
        score = min(score, 35)
        warnings.append("STALE_TECHNICAL_EVIDENCE")
    if context.missing_evidence_flags:
        score = min(score, 30)
        warnings.append("MISSING_TECHNICAL_EVIDENCE")
    contributing = [
        name for name, value in {
            "MACD": context.macd_evidence_summary,
            "RSI": context.rsi_evidence_summary,
            "MA": context.moving_average_evidence_summary,
            "HMA": context.hma_evidence_summary,
            "ATR": context.atr_risk_evidence_summary,
            "VOLUME": context.volume_evidence_summary,
            "DIVERGENCE": context.divergence_evidence_summary,
        }.items() if value
    ]
    return CandidateTechnicalScore(
        ticker=context.ticker,
        score=score,
        contributing_indicators=contributing,
        missing_indicators=list(context.missing_evidence_flags),
        setup_grade=context.setup_grade,
        evidence_freshness=context.evidence_freshness,
        evaluation_warnings=warnings,
    )


def _profitability_score(fixture: DomesticCandidateEvaluationFixture) -> CandidateProfitabilityScore:
    context = fixture.profitability_context
    score = 100
    blocked_reason = None
    if context.profitability_context_status != "ACTIONABLE":
        score = 20
        blocked_reason = "NON_ACTIONABLE_PROFITABILITY_CONTEXT"
    if (context.expected_net_profit or 0) <= 0 or (context.expected_net_return_percentage or 0) <= 0:
        score = min(score, 10)
        blocked_reason = "INSUFFICIENT_EXPECTED_NET_PROFIT"
    elif (context.expected_net_return_percentage or 0) <= 0.01:
        score = min(score, 65)
    return CandidateProfitabilityScore(
        ticker=fixture.technical_evidence_context.ticker,
        profitability_context_status=context.profitability_context_status,
        expected_net_profit=context.expected_net_profit,
        expected_net_return_percentage=context.expected_net_return_percentage,
        break_even_move=context.break_even_move,
        cost_aware_minimum_target_move=context.cost_aware_minimum_target_move,
        score=score,
        blocked_reason=blocked_reason,
    )


def _risk_signal(scanner_state: ScannerCandidateState, technical: CandidateTechnicalScore, profitability: CandidateProfitabilityScore) -> CandidateRiskSignal:
    stale_risk = "HIGH" if scanner_state == ScannerCandidateState.REPORT_ONLY_STALE else "LOW"
    scanner_quality_risk = "HIGH" if scanner_state in {
        ScannerCandidateState.BLOCKED_QUALITY,
        ScannerCandidateState.INSUFFICIENT_DATA,
    } else "LOW"
    profitability_risk = "HIGH" if profitability.blocked_reason else "LOW"
    technical_risk = "HIGH" if technical.score < 60 else "LOW"
    unsafe_trigger_risk = "HIGH" if scanner_state == ScannerCandidateState.REJECTED_UNSAFE_TRIGGER else "LOW"
    overall = "LOW"
    if "HIGH" in {stale_risk, scanner_quality_risk, profitability_risk, technical_risk, unsafe_trigger_risk}:
        overall = "HIGH"
    elif scanner_state == ScannerCandidateState.WATCHLIST_REMOVE:
        overall = "MEDIUM"
    return CandidateRiskSignal(
        ticker=technical.ticker,
        stale_risk=stale_risk,
        scanner_quality_risk=scanner_quality_risk,
        profitability_risk=profitability_risk,
        technical_evidence_risk=technical_risk,
        unsafe_trigger_risk=unsafe_trigger_risk,
        overall_risk_classification=overall,
    )


def _map_state(
    scanner_state: ScannerCandidateState,
    technical: CandidateTechnicalScore,
    profitability: CandidateProfitabilityScore,
    risk: CandidateRiskSignal,
) -> tuple[CandidateEvaluationState, CandidateEvaluationCompatibility, list[str], list[str]]:
    warnings: list[str] = []
    blocks: list[str] = []
    if scanner_state == ScannerCandidateState.REJECTED_NON_DOMESTIC:
        return CandidateEvaluationState.REJECTED_NON_DOMESTIC, CandidateEvaluationCompatibility.EXCLUDE, warnings, ["NON_DOMESTIC_TRACK"]
    if scanner_state == ScannerCandidateState.REJECTED_UNSAFE_TRIGGER:
        return CandidateEvaluationState.REJECTED_UNSAFE_TRIGGER, CandidateEvaluationCompatibility.EXCLUDE, warnings, ["ORDER_TRIGGER_ATTEMPT"]
    if scanner_state == ScannerCandidateState.BLOCKED_QUALITY:
        return CandidateEvaluationState.BLOCKED_SCANNER_QUALITY, CandidateEvaluationCompatibility.EXCLUDE, warnings, ["SCANNER_QUALITY_BLOCK"]
    if scanner_state == ScannerCandidateState.REPORT_ONLY_STALE:
        return CandidateEvaluationState.REPORT_ONLY, CandidateEvaluationCompatibility.WATCH, ["STALE_REPORT_ONLY"], blocks
    if scanner_state == ScannerCandidateState.INSUFFICIENT_DATA:
        return CandidateEvaluationState.INSUFFICIENT_CONTEXT, CandidateEvaluationCompatibility.WATCH, warnings, ["INSUFFICIENT_SCANNER_CONTEXT"]
    if profitability.blocked_reason:
        return CandidateEvaluationState.BLOCKED_PROFITABILITY, CandidateEvaluationCompatibility.EXCLUDE, warnings, [profitability.blocked_reason]
    if technical.score < 60:
        return CandidateEvaluationState.BLOCKED_TECHNICAL_EVIDENCE, CandidateEvaluationCompatibility.WATCH, list(technical.evaluation_warnings), ["TECHNICAL_EVIDENCE_BELOW_THRESHOLD"]
    if scanner_state == ScannerCandidateState.WATCHLIST_REMOVE or risk.overall_risk_classification == "HIGH":
        return CandidateEvaluationState.BLOCKED_RISK, CandidateEvaluationCompatibility.EXCLUDE, warnings, ["RISK_GATE_BLOCK"]
    if scanner_state == ScannerCandidateState.WATCHLIST_ADD or profitability.score <= 65 or technical.score <= 75:
        return CandidateEvaluationState.WATCH_ONLY, CandidateEvaluationCompatibility.WATCH, warnings, blocks
    return CandidateEvaluationState.EVALUATION_READY, CandidateEvaluationCompatibility.DISCOVER, warnings, blocks


def build_candidate_evaluation_report(
    fixture: DomesticCandidateEvaluationFixture,
) -> CandidateEvaluationReport:
    scanner_report = build_domestic_scanner_candidates(fixture.domestic_scanner_fixture)
    decisions: list[CandidateEvaluationDecision] = []
    warnings: list[str] = []
    blocks: list[str] = []
    technical = _technical_score(fixture)
    profitability = _profitability_score(fixture)
    for candidate in scanner_report.candidates:
        risk = _risk_signal(candidate.internal_state, technical, profitability)
        state, compatibility, item_warnings, item_blocks = _map_state(
            candidate.internal_state,
            technical,
            profitability,
            risk,
        )
        warnings.extend(item_warnings)
        blocks.extend(item_blocks)
        decisions.append(
            CandidateEvaluationDecision(
                candidate_id=candidate.candidate_id,
                ticker=candidate.symbol,
                scanner_state=candidate.internal_state,
                scanner_compatibility_status=candidate.compatibility_discovery_status,
                evaluation_state=state,
                evaluation_compatibility_status=compatibility,
                technical_score=technical,
                profitability_score=profitability,
                risk_signal=risk,
                warnings=item_warnings,
                block_reasons=item_blocks,
                supported_tracks=list(fixture.advisory_context.supported_tracks),
                prompt_pack_context_marker=fixture.advisory_context.prompt_pack_context_marker,
                actionable_approval=False,
            )
        )
    return CandidateEvaluationReport(
        report_id=f"{fixture.run_id}-report",
        strategy_track=fixture.evaluation_config.strategy_track,
        market_profile_summary=fixture.domestic_scanner_fixture.domestic_realtime_fixture.strategy_request.market_profile.model_dump(mode="json"),
        candidate_count=len(decisions),
        evaluation_ready_count=sum(item.evaluation_state == CandidateEvaluationState.EVALUATION_READY for item in decisions),
        watch_only_count=sum(item.evaluation_state == CandidateEvaluationState.WATCH_ONLY for item in decisions),
        report_only_count=sum(item.evaluation_state == CandidateEvaluationState.REPORT_ONLY for item in decisions),
        blocked_count=sum(item.evaluation_state in {
            CandidateEvaluationState.BLOCKED_SCANNER_QUALITY,
            CandidateEvaluationState.BLOCKED_STALE_DATA,
            CandidateEvaluationState.BLOCKED_PROFITABILITY,
            CandidateEvaluationState.BLOCKED_TECHNICAL_EVIDENCE,
            CandidateEvaluationState.BLOCKED_RISK,
        } for item in decisions),
        rejected_count=sum(item.evaluation_state in {
            CandidateEvaluationState.REJECTED_NON_DOMESTIC,
            CandidateEvaluationState.REJECTED_UNSAFE_TRIGGER,
        } for item in decisions),
        gap_count=sum(item.evaluation_state == CandidateEvaluationState.INSUFFICIENT_CONTEXT for item in decisions),
        decisions=decisions,
        warnings=sorted(set(warnings)),
        block_reasons=sorted(set(blocks)),
        metadata_json=dict(DOMESTIC_CANDIDATE_EVALUATION_METADATA),
    )


def build_candidate_evaluation_gap_report(
    fixture: DomesticCandidateEvaluationFixture,
) -> CandidateEvaluationGapReport:
    report = build_candidate_evaluation_report(fixture)
    missing_technical = len(fixture.technical_evidence_context.missing_evidence_flags)
    gap_reasons = list(fixture.technical_evidence_context.missing_evidence_flags)
    if fixture.profitability_context.profitability_context_status != "ACTIONABLE":
        gap_reasons.append("NON_ACTIONABLE_PROFITABILITY_CONTEXT")
    return CandidateEvaluationGapReport(
        report_id=report.report_id,
        missing_technical_evidence_count=missing_technical,
        missing_profitability_context_count=0 if fixture.profitability_context.profitability_context_status else 1,
        stale_candidate_count=sum(item.scanner_state == ScannerCandidateState.REPORT_ONLY_STALE for item in report.decisions),
        blocked_candidate_count=report.blocked_count,
        unsupported_track_count=sum(item.evaluation_state == CandidateEvaluationState.REJECTED_NON_DOMESTIC for item in report.decisions),
        unsafe_trigger_count=sum(item.evaluation_state == CandidateEvaluationState.REJECTED_UNSAFE_TRIGGER for item in report.decisions),
        unresolved_market_profile_count=0 if report.market_profile_summary else 1,
        gap_reasons=gap_reasons,
        metadata_json=dict(DOMESTIC_CANDIDATE_EVALUATION_METADATA),
    )


def build_candidate_evaluation_safety_report(
    fixture: DomesticCandidateEvaluationFixture,
) -> CandidateEvaluationSafetyReport:
    report = build_candidate_evaluation_report(fixture)
    return CandidateEvaluationSafetyReport(
        report_id=report.report_id,
        strategy_track=report.strategy_track,
        safety_boundary=CandidateEvaluationSafetyBoundary(),
        decisions=report.decisions,
        metadata_json=dict(DOMESTIC_CANDIDATE_EVALUATION_METADATA),
    )
