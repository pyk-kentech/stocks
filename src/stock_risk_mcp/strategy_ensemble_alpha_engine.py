from __future__ import annotations

from collections import Counter, defaultdict

from stock_risk_mcp.strategy_ensemble_alpha_guard import (
    validate_strategy_ensemble_alpha_metadata_safety,
)
from stock_risk_mcp.strategy_ensemble_alpha_models import (
    AlphaCandidateReport,
    AlphaCorrelationRiskReport,
    AlphaPortfolioConcentrationReport,
    DrawdownCoMovementReport,
    EnsemblePromotionDecision,
    EnsemblePromotionReadinessReport,
    RegimeOverlapReport,
    StrategyEnsembleAlphaGapCategory,
    StrategyEnsembleAlphaGapEntry,
    StrategyEnsembleAlphaGapReport,
    StrategyEnsembleAlphaInput,
    StrategyEnsembleAlphaSafetyReport,
    StrategyFamilyDiversificationReport,
)


def build_strategy_ensemble_alpha_gate(
    ensemble_input: StrategyEnsembleAlphaInput,
) -> StrategyEnsembleAlphaInput:
    gap_entries: list[StrategyEnsembleAlphaGapEntry] = []
    for audit in ensemble_input.audit_records:
        validate_strategy_ensemble_alpha_metadata_safety(
            {
                "operator_context": audit.operator_context,
                "source_path": audit.source_path,
            },
            context="strategy ensemble alpha",
        )

    allocations = {allocation.alpha_id: allocation.proposed_weight for allocation in ensemble_input.portfolio.allocations}
    family_weights: dict[str, float] = defaultdict(float)
    family_counts: Counter[str] = Counter()
    blocked_dependency_count = 0
    promotion_refs_complete = True
    any_paper_candidate_dependency = False
    for candidate in ensemble_input.alpha_candidates:
        family = candidate.strategy_family.value
        family_counts[family] += 1
        family_weights[family] += allocations[candidate.alpha_id]
        if not candidate.training_promotion_ref:
            promotion_refs_complete = False
            gap_entries.append(
                _gap(
                    ensemble_input,
                    f"{candidate.alpha_id}-MISSING-V73-PROMOTION-REF",
                    StrategyEnsembleAlphaGapCategory.MISSING_V73_PROMOTION_REF,
                    "WARNING",
                    f"{candidate.alpha_id} is missing v7.3 promotion reference",
                )
            )
        if candidate.training_promotion_decision in {"BLOCKED", "REJECTED"} or candidate.robustness_decision in {"BLOCKED", "REJECTED"}:
            blocked_dependency_count += 1
            gap_entries.append(
                _gap(
                    ensemble_input,
                    f"{candidate.alpha_id}-BLOCKED-DEPENDENCY",
                    StrategyEnsembleAlphaGapCategory.BLOCKED_ALPHA_DEPENDENCY,
                    "BLOCKING",
                    f"{candidate.alpha_id} has blocked training or robustness dependency",
                )
            )
        if candidate.training_promotion_decision == "PAPER_CANDIDATE" and candidate.paper_candidate_eligibility_ref:
            any_paper_candidate_dependency = True

    alpha_candidate_report = AlphaCandidateReport(
        report_id=f"{ensemble_input.input_id}-ALPHA-CANDIDATE-REPORT",
        alpha_count=len(ensemble_input.alpha_candidates),
        strategy_family_count=len(family_counts),
        promotion_refs_complete=promotion_refs_complete,
        blocked_dependency_count=blocked_dependency_count,
    )

    minimum_alpha_count_met = len(ensemble_input.alpha_candidates) >= ensemble_input.portfolio.min_alpha_count
    minimum_family_count_met = len(family_counts) >= ensemble_input.portfolio.min_strategy_family_count
    if not minimum_alpha_count_met:
        gap_entries.append(
            _gap(
                ensemble_input,
                "MIN-ALPHA-COUNT-NOT-MET",
                StrategyEnsembleAlphaGapCategory.MIN_ALPHA_COUNT_NOT_MET,
                "WARNING",
                "minimum alpha count is not met",
            )
        )
    if not minimum_family_count_met:
        gap_entries.append(
            _gap(
                ensemble_input,
                "MIN-STRATEGY-FAMILY-COUNT-NOT-MET",
                StrategyEnsembleAlphaGapCategory.MIN_STRATEGY_FAMILY_COUNT_NOT_MET,
                "WARNING",
                "minimum strategy family count is not met",
            )
        )
    if ensemble_input.duplicate_signal_detected:
        gap_entries.append(
            _gap(
                ensemble_input,
                "DUPLICATE-SIGNAL-DETECTED",
                StrategyEnsembleAlphaGapCategory.DUPLICATE_SIGNAL_DETECTED,
                "BLOCKING",
                "duplicate signal detection triggered",
            )
        )
    family_report = StrategyFamilyDiversificationReport(
        report_id=f"{ensemble_input.input_id}-STRATEGY-FAMILY-DIVERSIFICATION-REPORT",
        alpha_count=len(ensemble_input.alpha_candidates),
        strategy_family_count=len(family_counts),
        minimum_alpha_count_met=minimum_alpha_count_met,
        minimum_family_count_met=minimum_family_count_met,
        duplicate_signal_detected=ensemble_input.duplicate_signal_detected,
    )

    high_correlation = ensemble_input.correlation_matrix_summary.max_pair_correlation >= 0.90
    if high_correlation:
        gap_entries.append(
            _gap(
                ensemble_input,
                "HIGH-ALPHA-CORRELATION",
                StrategyEnsembleAlphaGapCategory.HIGH_ALPHA_CORRELATION,
                "BLOCKING",
                "alpha correlation is too high",
            )
        )
    correlation_report = AlphaCorrelationRiskReport(
        report_id=f"{ensemble_input.input_id}-ALPHA-CORRELATION-RISK-REPORT",
        max_pair_correlation=ensemble_input.correlation_matrix_summary.max_pair_correlation,
        high_alpha_correlation_flagged=high_correlation,
    )

    high_drawdown = ensemble_input.drawdown_summary.max_drawdown_co_movement >= 0.85
    if high_drawdown:
        gap_entries.append(
            _gap(
                ensemble_input,
                "HIGH-DRAWDOWN-CO-MOVEMENT",
                StrategyEnsembleAlphaGapCategory.HIGH_DRAWDOWN_CO_MOVEMENT,
                "BLOCKING",
                "drawdown co-movement is too high",
            )
        )
    drawdown_report = DrawdownCoMovementReport(
        report_id=f"{ensemble_input.input_id}-DRAWDOWN-CO-MOVEMENT-REPORT",
        max_drawdown_co_movement=ensemble_input.drawdown_summary.max_drawdown_co_movement,
        high_drawdown_co_movement_flagged=high_drawdown,
    )

    if not ensemble_input.regime_overlap_summary.regime_coverage_complete:
        gap_entries.append(
            _gap(
                ensemble_input,
                "MISSING-REGIME-COVERAGE",
                StrategyEnsembleAlphaGapCategory.MISSING_REGIME_COVERAGE,
                "WARNING",
                "regime coverage is incomplete",
            )
        )
    regime_report = RegimeOverlapReport(
        report_id=f"{ensemble_input.input_id}-REGIME-OVERLAP-REPORT",
        regime_coverage_complete=ensemble_input.regime_overlap_summary.regime_coverage_complete,
        overlap_ratio=ensemble_input.regime_overlap_summary.overlap_ratio,
        covered_regime_count=len(ensemble_input.regime_overlap_summary.covered_regimes),
    )

    max_family_weight = max(family_weights.values()) if family_weights else 0
    max_single_alpha_weight = max(allocations.values()) if allocations else 0
    family_concentration_blocked = max_family_weight > ensemble_input.portfolio.max_family_concentration
    single_alpha_concentration_blocked = max_single_alpha_weight > ensemble_input.portfolio.max_single_alpha_concentration
    if family_concentration_blocked:
        gap_entries.append(
            _gap(
                ensemble_input,
                "EXCESSIVE-FAMILY-CONCENTRATION",
                StrategyEnsembleAlphaGapCategory.EXCESSIVE_FAMILY_CONCENTRATION,
                "BLOCKING",
                "family concentration exceeds configured limit",
            )
        )
    if single_alpha_concentration_blocked:
        gap_entries.append(
            _gap(
                ensemble_input,
                "EXCESSIVE-SINGLE-ALPHA-CONCENTRATION",
                StrategyEnsembleAlphaGapCategory.EXCESSIVE_SINGLE_ALPHA_CONCENTRATION,
                "BLOCKING",
                "single alpha concentration exceeds configured limit",
            )
        )
    concentration_report = AlphaPortfolioConcentrationReport(
        report_id=f"{ensemble_input.input_id}-ALPHA-PORTFOLIO-CONCENTRATION-REPORT",
        max_family_weight=max_family_weight,
        max_single_alpha_weight=max_single_alpha_weight,
        family_concentration_blocked=family_concentration_blocked,
        single_alpha_concentration_blocked=single_alpha_concentration_blocked,
    )

    safety_report = StrategyEnsembleAlphaSafetyReport(
        safety_report_id=f"{ensemble_input.input_id}-SAFETY-REPORT",
        blocked_capabilities=[
            "LIVE_TRADING_BLOCKED",
            "REAL_ORDER_BLOCKED",
            "ACCOUNT_MUTATION_BLOCKED",
            "BROKER_API_BLOCKED",
            "NETWORK_BLOCKED",
            "AUTONOMOUS_TRADING_BLOCKED",
        ],
        findings=["local_offline_report_only=true"],
    )

    decision, reason = _decide(
        ensemble_input=ensemble_input,
        promotion_refs_complete=promotion_refs_complete,
        any_paper_candidate_dependency=any_paper_candidate_dependency,
        minimum_alpha_count_met=minimum_alpha_count_met,
        minimum_family_count_met=minimum_family_count_met,
        gap_entries=gap_entries,
    )
    promotion_report = EnsemblePromotionReadinessReport(
        report_id=f"{ensemble_input.input_id}-ENSEMBLE-PROMOTION-READINESS-REPORT",
        decision=decision,
        decision_reason=reason,
    )
    gap_entries.append(
        _gap(
            ensemble_input,
            "ENSEMBLE-REPORT-GENERATED",
            StrategyEnsembleAlphaGapCategory.ENSEMBLE_REPORT_GENERATED,
            "REPORT_ONLY",
            "strategy ensemble alpha report generated",
        )
    )
    gap_report = StrategyEnsembleAlphaGapReport(
        gap_report_id=f"{ensemble_input.input_id}-GAP-REPORT",
        decision=decision,
        gap_entries=gap_entries,
        blocking_gap_count=sum(1 for entry in gap_entries if entry.severity == "BLOCKING"),
        warning_gap_count=sum(1 for entry in gap_entries if entry.severity == "WARNING"),
    )
    return ensemble_input.model_copy(
        update={
            "alpha_candidate_report": alpha_candidate_report,
            "strategy_family_diversification_report": family_report,
            "alpha_correlation_risk_report": correlation_report,
            "drawdown_co_movement_report": drawdown_report,
            "regime_overlap_report": regime_report,
            "alpha_portfolio_concentration_report": concentration_report,
            "ensemble_promotion_readiness_report": promotion_report,
            "gap_report": gap_report,
            "safety_report": safety_report,
        }
    )


def _decide(
    *,
    ensemble_input: StrategyEnsembleAlphaInput,
    promotion_refs_complete: bool,
    any_paper_candidate_dependency: bool,
    minimum_alpha_count_met: bool,
    minimum_family_count_met: bool,
    gap_entries: list[StrategyEnsembleAlphaGapEntry],
):
    blocking = [entry for entry in gap_entries if entry.severity == "BLOCKING"]
    warnings = [entry for entry in gap_entries if entry.severity == "WARNING"]
    if blocking:
        return EnsemblePromotionDecision.BLOCKED, blocking[0].message
    if not minimum_alpha_count_met or not minimum_family_count_met:
        return EnsemblePromotionDecision.RESEARCH_ONLY, "ensemble is not yet diversified enough"
    if not promotion_refs_complete:
        return EnsemblePromotionDecision.GAP, "required v7.3 promotion evidence is missing"
    if warnings:
        return EnsemblePromotionDecision.GAP, warnings[0].message
    if any_paper_candidate_dependency:
        return EnsemblePromotionDecision.PAPER_CANDIDATE, "diversified alpha portfolio is eligible for paper candidate evaluation"
    return EnsemblePromotionDecision.ENSEMBLE_READY, "diversified ensemble is ready for controlled offline validation"


def _gap(ensemble_input, suffix, category, severity, message):
    return StrategyEnsembleAlphaGapEntry(
        gap_id=f"{ensemble_input.input_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )
