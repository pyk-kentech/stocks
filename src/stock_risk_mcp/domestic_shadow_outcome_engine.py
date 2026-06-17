from __future__ import annotations

from statistics import mean

from stock_risk_mcp.domestic_paper_shadow_models import PaperShadowDecisionType
from stock_risk_mcp.domestic_shadow_outcome_models import (
    DOMESTIC_SHADOW_OUTCOME_METADATA,
    DomesticShadowOutcomeFixture,
    PaperShadowOutcomeLabel,
    PaperShadowOutcomeLabelBatch,
    PaperShadowOutcomeLabelType,
    PaperShadowOutcomeReviewReport,
    PaperShadowOutcomeSafetyBoundary,
    PaperShadowOutcomeSafetyReport,
    ShadowOutcomeValidationReport,
    decision_lookup,
)


def build_domestic_shadow_outcome_validation_report(
    fixture: DomesticShadowOutcomeFixture,
) -> ShadowOutcomeValidationReport:
    journal = fixture.shadow_outcome_input_set.paper_shadow_journal
    return ShadowOutcomeValidationReport(
        config_id=fixture.shadow_outcome_config.config_id,
        strategy_track=fixture.shadow_outcome_config.strategy_track,
        market_id=str(fixture.shadow_outcome_input_set.market_profile_summary["market_id"]).upper(),
        paper_shadow_journal_id=journal.journal_id,
        journal_entry_count=journal.entry_count,
        outcome_fixture_count=len(fixture.outcome_fixtures),
    )


def _compute_metrics(reference_price: float, future_points) -> dict[str, object]:
    valid_prices = [point.price for point in future_points if point.price is not None]
    missing_data = len(valid_prices) != len(future_points) or not valid_prices
    if not valid_prices:
        return {
            "maximum_favorable_observation_move": 0.0,
            "maximum_adverse_observation_move": 0.0,
            "final_observation_move": 0.0,
            "observation_volatility_proxy": 0.0,
            "observation_volume_confirmation": False,
            "threshold_touched": False,
            "adverse_threshold_touched": False,
            "neutral_range_marker": False,
            "missing_data_marker": True,
        }
    signed_moves = [(price - reference_price) / reference_price for price in valid_prices]
    adverse_moves = [abs(move) for move in signed_moves if move < 0]
    return {
        "maximum_favorable_observation_move": max(0.0, max(signed_moves)),
        "maximum_adverse_observation_move": max(adverse_moves, default=0.0),
        "final_observation_move": signed_moves[-1],
        "observation_volatility_proxy": max(signed_moves) - min(signed_moves),
        "observation_volume_confirmation": any((point.volume or 0) > 0 for point in future_points),
        "threshold_touched": False,
        "adverse_threshold_touched": False,
        "neutral_range_marker": False,
        "missing_data_marker": missing_data,
    }


def _label_for_decision(decision, outcome_fixture, policy) -> tuple[PaperShadowOutcomeLabelType, str, dict[str, object]]:
    metrics = _compute_metrics(outcome_fixture.reference_price, outcome_fixture.future_points)
    stale_data_marker = "STALE_DATA" in outcome_fixture.data_quality_flags
    threshold_touched = metrics["maximum_favorable_observation_move"] >= policy.favorable_threshold_pct
    adverse_threshold_touched = metrics["maximum_adverse_observation_move"] >= policy.adverse_threshold_pct
    neutral_range_marker = (
        metrics["maximum_favorable_observation_move"] <= policy.neutral_band_pct
        and metrics["maximum_adverse_observation_move"] <= policy.neutral_band_pct
    )
    metrics["threshold_touched"] = threshold_touched
    metrics["adverse_threshold_touched"] = adverse_threshold_touched
    metrics["neutral_range_marker"] = neutral_range_marker

    if metrics["missing_data_marker"] or len(outcome_fixture.future_points) < policy.minimum_point_count:
        return PaperShadowOutcomeLabelType.OUTCOME_INSUFFICIENT_DATA, "INSUFFICIENT_OBSERVATION_DATA", metrics
    if decision.decision_type == PaperShadowDecisionType.SHADOW_BLOCKED_SAFETY:
        return PaperShadowOutcomeLabelType.OUTCOME_REJECTED_SAFETY, "SOURCE_DECISION_BLOCKED_SAFETY", metrics
    if decision.decision_type == PaperShadowDecisionType.SHADOW_REPORT_ONLY and not policy.allow_report_only_observation_label:
        return PaperShadowOutcomeLabelType.OUTCOME_REPORT_ONLY, "REPORT_ONLY_PRESERVED", metrics
    if decision.decision_type in {
        PaperShadowDecisionType.SHADOW_BLOCKED_QUALITY,
        PaperShadowDecisionType.SHADOW_BLOCKED_PROFITABILITY,
        PaperShadowDecisionType.SHADOW_BLOCKED_TECHNICAL_EVIDENCE,
        PaperShadowDecisionType.SHADOW_BLOCKED_RISK,
        PaperShadowDecisionType.SHADOW_REJECT,
    }:
        return PaperShadowOutcomeLabelType.OUTCOME_BLOCKED_CONFIRMED, "BLOCKED_CONTEXT_PRESERVED", metrics
    if decision.decision_type == PaperShadowDecisionType.SHADOW_INSUFFICIENT_CONTEXT:
        return PaperShadowOutcomeLabelType.OUTCOME_INSUFFICIENT_DATA, "INSUFFICIENT_CONTEXT_PRESERVED", metrics
    if stale_data_marker and decision.decision_type == PaperShadowDecisionType.SHADOW_REPORT_ONLY:
        return PaperShadowOutcomeLabelType.OUTCOME_REPORT_ONLY, "STALE_REPORT_ONLY_PRESERVED", metrics
    if threshold_touched and adverse_threshold_touched:
        return PaperShadowOutcomeLabelType.OUTCOME_INCONCLUSIVE, "FAVORABLE_AND_ADVERSE_THRESHOLDS_TOUCHED", metrics
    if threshold_touched and metrics["final_observation_move"] >= 0:
        return PaperShadowOutcomeLabelType.OUTCOME_FAVORABLE, "FAVORABLE_THRESHOLD_AND_FINAL_STATE", metrics
    if adverse_threshold_touched and metrics["final_observation_move"] <= 0:
        return PaperShadowOutcomeLabelType.OUTCOME_ADVERSE, "ADVERSE_THRESHOLD_AND_FINAL_STATE", metrics
    if neutral_range_marker:
        return PaperShadowOutcomeLabelType.OUTCOME_NEUTRAL, "NEUTRAL_OBSERVATION_RANGE", metrics
    return PaperShadowOutcomeLabelType.OUTCOME_INCONCLUSIVE, "NO_DECISIVE_OUTCOME_LABEL", metrics


def build_paper_shadow_outcome_labels(
    fixture: DomesticShadowOutcomeFixture,
) -> list[PaperShadowOutcomeLabel]:
    journal_entries = decision_lookup(fixture.shadow_outcome_input_set.paper_shadow_journal)
    labels: list[PaperShadowOutcomeLabel] = []
    for index, outcome_fixture in enumerate(fixture.outcome_fixtures, start=1):
        decision = journal_entries[outcome_fixture.source_paper_shadow_decision_id]
        outcome_label, rationale, metrics = _label_for_decision(decision, outcome_fixture, fixture.outcome_label_policy)
        labels.append(
            PaperShadowOutcomeLabel(
                label_id=f"{fixture.run_id}-label-{index}",
                source_paper_shadow_journal_id=outcome_fixture.source_paper_shadow_journal_id,
                source_paper_shadow_decision_id=outcome_fixture.source_paper_shadow_decision_id,
                candidate_id=outcome_fixture.candidate_id,
                symbol=outcome_fixture.symbol,
                strategy_track=fixture.shadow_outcome_config.strategy_track,
                market_profile_id=outcome_fixture.market_profile_id,
                decision_type=decision.decision_type,
                outcome_label=outcome_label,
                label_rationale=rationale,
                scenario_family=outcome_fixture.scenario_family,
                replay_window_id=outcome_fixture.replay_window_id,
                promotion_gate_status=outcome_fixture.promotion_gate_status,
                observation_horizon=outcome_fixture.observation_window.horizon_label,
                maximum_favorable_observation_move=metrics["maximum_favorable_observation_move"],
                maximum_adverse_observation_move=metrics["maximum_adverse_observation_move"],
                final_observation_move=metrics["final_observation_move"],
                observation_volatility_proxy=metrics["observation_volatility_proxy"],
                observation_volume_confirmation=metrics["observation_volume_confirmation"],
                threshold_touched=metrics["threshold_touched"],
                adverse_threshold_touched=metrics["adverse_threshold_touched"],
                neutral_range_marker=metrics["neutral_range_marker"],
                missing_data_marker=metrics["missing_data_marker"],
                stale_data_marker="STALE_DATA" in outcome_fixture.data_quality_flags,
                blocked_reasons=list(decision.blocked_reasons),
                report_only_reasons=list(decision.report_only_reasons),
                non_actionable_reasons=list(decision.non_actionable_reasons),
                data_quality_flags=list(outcome_fixture.data_quality_flags),
                non_executable=True,
            )
        )
    return labels


def build_paper_shadow_outcome_label_batch(
    fixture: DomesticShadowOutcomeFixture,
) -> PaperShadowOutcomeLabelBatch:
    labels = build_paper_shadow_outcome_labels(fixture)
    return PaperShadowOutcomeLabelBatch(
        label_batch_id=f"{fixture.run_id}-label-batch",
        journal_reference=fixture.shadow_outcome_input_set.paper_shadow_journal.journal_id,
        label_count=len(labels),
        labels=labels,
        metadata_json=dict(DOMESTIC_SHADOW_OUTCOME_METADATA),
    )


def build_paper_shadow_outcome_review_report(
    fixture: DomesticShadowOutcomeFixture,
) -> PaperShadowOutcomeReviewReport:
    labels = build_paper_shadow_outcome_labels(fixture)
    outcome_label_counts: dict[str, int] = {}
    scenario_family_counts: dict[str, int] = {}
    replay_window_counts: dict[str, int] = {}
    symbol_counts: dict[str, int] = {}
    decision_type_counts: dict[str, int] = {}
    blocked_reason_counts: dict[str, int] = {}
    report_only_reason_counts: dict[str, int] = {}
    promotion_gate_status_counts: dict[str, int] = {}
    observation_horizon_counts: dict[str, int] = {}
    for label in labels:
        outcome_label_counts[label.outcome_label.value] = outcome_label_counts.get(label.outcome_label.value, 0) + 1
        scenario_family_counts[label.scenario_family] = scenario_family_counts.get(label.scenario_family, 0) + 1
        replay_window_counts[label.replay_window_id] = replay_window_counts.get(label.replay_window_id, 0) + 1
        symbol_counts[label.symbol] = symbol_counts.get(label.symbol, 0) + 1
        decision_type_counts[label.decision_type.value] = decision_type_counts.get(label.decision_type.value, 0) + 1
        promotion_gate_status_counts[label.promotion_gate_status] = promotion_gate_status_counts.get(label.promotion_gate_status, 0) + 1
        observation_horizon_counts[label.observation_horizon] = observation_horizon_counts.get(label.observation_horizon, 0) + 1
        for reason in label.blocked_reasons:
            blocked_reason_counts[reason] = blocked_reason_counts.get(reason, 0) + 1
        for reason in label.report_only_reasons:
            report_only_reason_counts[reason] = report_only_reason_counts.get(reason, 0) + 1
    shadow_watch_total = sum(1 for label in labels if label.decision_type == PaperShadowDecisionType.SHADOW_WATCH)
    favorable_count = outcome_label_counts.get(PaperShadowOutcomeLabelType.OUTCOME_FAVORABLE.value, 0)
    adverse_count = outcome_label_counts.get(PaperShadowOutcomeLabelType.OUTCOME_ADVERSE.value, 0)
    inconclusive_count = outcome_label_counts.get(PaperShadowOutcomeLabelType.OUTCOME_INCONCLUSIVE.value, 0)
    return PaperShadowOutcomeReviewReport(
        review_report_id=f"{fixture.run_id}-outcome-review",
        journal_reference=fixture.shadow_outcome_input_set.paper_shadow_journal.journal_id,
        total_outcome_labels=len(labels),
        favorable_count=favorable_count,
        adverse_count=adverse_count,
        neutral_count=outcome_label_counts.get(PaperShadowOutcomeLabelType.OUTCOME_NEUTRAL.value, 0),
        inconclusive_count=inconclusive_count,
        report_only_count=outcome_label_counts.get(PaperShadowOutcomeLabelType.OUTCOME_REPORT_ONLY.value, 0),
        insufficient_data_count=outcome_label_counts.get(PaperShadowOutcomeLabelType.OUTCOME_INSUFFICIENT_DATA.value, 0),
        safety_rejected_count=outcome_label_counts.get(PaperShadowOutcomeLabelType.OUTCOME_REJECTED_SAFETY.value, 0),
        blocked_confirmed_count=outcome_label_counts.get(PaperShadowOutcomeLabelType.OUTCOME_BLOCKED_CONFIRMED.value, 0),
        favorable_rate_among_shadow_watch_entries=(favorable_count / shadow_watch_total) if shadow_watch_total else 0.0,
        adverse_rate_among_shadow_watch_entries=(adverse_count / shadow_watch_total) if shadow_watch_total else 0.0,
        inconclusive_rate=(inconclusive_count / len(labels)) if labels else 0.0,
        average_maximum_favorable_observation_move=mean(label.maximum_favorable_observation_move for label in labels) if labels else 0.0,
        average_maximum_adverse_observation_move=mean(label.maximum_adverse_observation_move for label in labels) if labels else 0.0,
        scenario_family_coverage_count=len(scenario_family_counts),
        symbol_coverage_count=len(symbol_counts),
        observation_window_coverage_count=len(observation_horizon_counts),
        outcome_label_counts=outcome_label_counts,
        scenario_family_counts=scenario_family_counts,
        replay_window_counts=replay_window_counts,
        symbol_counts=symbol_counts,
        decision_type_counts=decision_type_counts,
        blocked_reason_counts=blocked_reason_counts,
        report_only_reason_counts=report_only_reason_counts,
        promotion_gate_status_counts=promotion_gate_status_counts,
        observation_horizon_counts=observation_horizon_counts,
        advisory_context_placeholders={
            "supported_tracks_required": True,
            "non_executable_context_only": True,
            "trade_instruction_conversion_allowed": False,
        },
        metadata_json=dict(DOMESTIC_SHADOW_OUTCOME_METADATA),
    )


def build_paper_shadow_outcome_safety_report(
    fixture: DomesticShadowOutcomeFixture,
) -> PaperShadowOutcomeSafetyReport:
    warnings = []
    if any("STALE_DATA" in item.data_quality_flags for item in fixture.outcome_fixtures):
        warnings.append("STALE_DATA_PRESENT")
    return PaperShadowOutcomeSafetyReport(
        report_id=f"{fixture.run_id}-outcome-safety",
        strategy_track=fixture.shadow_outcome_config.strategy_track,
        safety_boundary=PaperShadowOutcomeSafetyBoundary(),
        block_reasons=[],
        warnings=warnings,
        metadata_json=dict(DOMESTIC_SHADOW_OUTCOME_METADATA),
    )
