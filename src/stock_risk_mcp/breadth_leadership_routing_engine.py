from __future__ import annotations

from datetime import timedelta

from stock_risk_mcp.breadth_leadership_routing_guard import validate_breadth_leadership_routing_metadata_safety
from stock_risk_mcp.breadth_leadership_routing_models import (
    AdvanceDeclineReport,
    BreadthInputSnapshotReport,
    BreadthLeadershipRoutingDecision,
    BreadthLeadershipRoutingInput,
    BreadthRoutingGapEntry,
    BreadthRoutingGapReport,
    BreadthRoutingLeakageReport,
    BreadthRoutingProviderReadinessReport,
    BreadthRoutingSummaryReport,
    BreadthRoutingTrainingFeatureIntegrationReport,
    BreadthState,
    DownstreamRoutingConstraintReport,
    EqualWeightDivergenceReport,
    IndexDistortionReport,
    InternalRiskState,
    LeadershipConcentrationReport,
    LeadershipState,
    NewHighLowReport,
    OutlierMomentumCandidate,
    OutlierMomentumCandidateReport,
    OutlierMomentumState,
    OutlierSleeveRiskReport,
    SectorLeadershipReport,
    UpDownVolumeParticipationReport,
)


def _gap(input_id: str, suffix: str, category: str, severity: str, message: str) -> BreadthRoutingGapEntry:
    return BreadthRoutingGapEntry(
        gap_id=f"{input_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def _provider_ready(level: str | None) -> bool:
    return bool(level and level not in {"GAP", "REJECTED", "BLOCKED", "UNKNOWN"})


def _safe_ref(value: str | None) -> bool:
    return bool(value and str(value).strip())


def _ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _matching_outlier(routing_input: BreadthLeadershipRoutingInput) -> OutlierMomentumCandidate | None:
    for candidate in routing_input.outlier_momentum_candidates:
        if candidate.symbol == routing_input.candidate_symbol:
            return candidate
    return None


def build_breadth_leadership_routing_review(routing_input: BreadthLeadershipRoutingInput) -> BreadthLeadershipRoutingInput:
    for audit in routing_input.audit_records:
        validate_breadth_leadership_routing_metadata_safety(
            {"source_path": audit.source_path, "operator_context": audit.operator_context},
            context="breadth leadership routing audit",
        )

    for ref in routing_input.source_refs:
        validate_breadth_leadership_routing_metadata_safety({"source_ref": ref}, context="breadth leadership routing ref")

    snapshot = routing_input.breadth_snapshot
    gaps: list[BreadthRoutingGapEntry] = []
    constraints: list[str] = []
    warnings: list[str] = []

    missing_available_at = snapshot.available_at is None or any(
        sector.available_at is None for sector in routing_input.sector_leadership_snapshots
    ) or any(candidate.available_at is None for candidate in routing_input.outlier_momentum_candidates)
    future_breadth_leakage = snapshot.available_at is not None and snapshot.available_at > routing_input.decision_timestamp
    future_sector_leadership_leakage = any(
        sector.available_at is not None and sector.available_at > routing_input.decision_timestamp
        for sector in routing_input.sector_leadership_snapshots
    )
    future_outlier_catalyst_leakage = any(
        candidate.available_at is not None and candidate.available_at > routing_input.decision_timestamp
        for candidate in routing_input.outlier_momentum_candidates
    )

    if missing_available_at:
        gaps.append(_gap(routing_input.routing_review_id, "MISSING-AVAILABLE-AT", "MISSING_AVAILABLE_AT", "WARNING", "available_at is missing"))
    if future_breadth_leakage:
        gaps.append(_gap(routing_input.routing_review_id, "FUTURE-BREADTH", "FUTURE_BREADTH_LEAKAGE", "BLOCKING", "breadth data was not available at decision time"))
    if future_sector_leadership_leakage:
        gaps.append(_gap(routing_input.routing_review_id, "FUTURE-SECTOR", "FUTURE_SECTOR_LEADERSHIP_LEAKAGE", "BLOCKING", "sector leadership data was not available at decision time"))
    if future_outlier_catalyst_leakage:
        gaps.append(_gap(routing_input.routing_review_id, "FUTURE-OUTLIER", "FUTURE_OUTLIER_CATALYST_LEAKAGE", "BLOCKING", "outlier catalyst data was not available at decision time"))

    missing_refs: list[str] = []
    missing_levels: list[str] = []
    provider_pairs = (
        ("BREADTH_PROVIDER_REF", routing_input.breadth_provider_readiness_ref, routing_input.breadth_provider_readiness_level),
        ("SECTOR_MAPPING_PROVIDER_REF", routing_input.sector_mapping_provider_readiness_ref, routing_input.sector_mapping_provider_readiness_level),
        ("MARKET_INTERNALS_PROVIDER_REF", routing_input.market_internals_provider_readiness_ref, routing_input.market_internals_provider_readiness_level),
        ("RELATIVE_VOLUME_PROVIDER_REF", routing_input.relative_volume_provider_readiness_ref, routing_input.relative_volume_provider_readiness_level),
    )
    provider_ready = True
    for ref_name, ref_value, level_value in provider_pairs:
        if not _safe_ref(ref_value):
            provider_ready = False
            missing_refs.append(ref_name)
        if not _provider_ready(level_value):
            provider_ready = False
            missing_levels.append(ref_name.replace("_REF", "_LEVEL"))
    if not _safe_ref(routing_input.canonical_data_contract_ref):
        provider_ready = False
        missing_refs.append("CANONICAL_DATA_CONTRACT_REF")
    if not provider_ready:
        gaps.append(_gap(routing_input.routing_review_id, "PROVIDER-READINESS", "PROVIDER_READINESS_GAP", "WARNING", "provider readiness evidence is incomplete"))

    stale_data_detected = False
    if snapshot.available_at is not None:
        age = routing_input.decision_timestamp - snapshot.available_at
        stale_data_detected = age > timedelta(minutes=120)
    if stale_data_detected:
        gaps.append(_gap(routing_input.routing_review_id, "STALE-BREADTH", "STALE_BREADTH_DATA", "WARNING", "breadth snapshot is stale"))

    impossible_counts = (
        snapshot.advancing_count + snapshot.declining_count + snapshot.unchanged_count > snapshot.tradable_universe_count
        or snapshot.new_highs_count > snapshot.tradable_universe_count
        or snapshot.new_lows_count > snapshot.tradable_universe_count
        or snapshot.tradable_universe_count > snapshot.total_listed_universe_count
    )
    if impossible_counts:
        gaps.append(_gap(routing_input.routing_review_id, "IMPOSSIBLE-COUNTS", "IMPOSSIBLE_COUNTS", "BLOCKING", "breadth counts exceed the universe"))

    event_risk_blocked = routing_input.event_risk_decision in {"BLOCK_NEW_ENTRY", "REDUCE_ONLY", "BLOCKED", "EVENT_ACTIVE", "COOLDOWN", "REJECTED"}
    risk_budget_blocked = routing_input.position_sizing_decision in {"BLOCKED", "RISK_BUDGET_LIMITED", "CASH_LIMITED", "REJECTED"}
    position_gap = routing_input.position_sizing_decision in {"DATA_GAP", "GAP", "WATCH_ONLY"}
    event_gap = routing_input.event_risk_decision in {"DATA_GAP", "WATCH_ONLY"}

    tradable = max(snapshot.tradable_universe_count, 1)
    advance_decline_ratio = _ratio(snapshot.advancing_count, snapshot.declining_count or 1)
    advance_decline_spread = snapshot.advancing_count - snapshot.declining_count
    percent_advancing = _ratio(snapshot.advancing_count, tradable)
    percent_declining = _ratio(snapshot.declining_count, tradable)
    new_high_low_ratio = _ratio(snapshot.new_highs_count, snapshot.new_lows_count or 1)
    new_high_low_spread = snapshot.new_highs_count - snapshot.new_lows_count
    up_volume_ratio = _ratio(snapshot.up_volume, snapshot.total_volume)
    down_volume_ratio = _ratio(snapshot.down_volume, snapshot.total_volume)
    breadth_thrust_proxy = round((percent_advancing + up_volume_ratio + max(new_high_low_spread, 0) / tradable) / 3, 4)
    participation_score = max(0, min(100, int(round((percent_advancing * 0.45 + up_volume_ratio * 0.35 + min(new_high_low_ratio, 3) / 3 * 0.20) * 100))))
    breadth_deterioration_score = max(0, min(100, int(round((percent_declining * 0.55 + max(snapshot.new_lows_count - snapshot.new_highs_count, 0) / tradable * 0.45) * 100))))
    equal_weight_divergence = snapshot.equal_weight_proxy_return_percent
    small_mid = snapshot.small_mid_cap_proxy_return_percent
    large_cap = snapshot.large_cap_proxy_return_percent
    breadth_divergence_score = round(
        abs((snapshot.index_return_percent or 0.0) - (equal_weight_divergence or snapshot.index_return_percent))
        + abs((large_cap or snapshot.index_return_percent) - (small_mid or large_cap or snapshot.index_return_percent)),
        4,
    )
    market_health_score = max(0, min(100, int(round(participation_score - breadth_divergence_score * 12 + max(new_high_low_spread, 0) * 0.2))))

    if percent_advancing >= 0.62 and up_volume_ratio >= 0.58 and new_high_low_spread > 0:
        breadth_state = BreadthState.BROAD_STRENGTH
    elif percent_advancing >= 0.55 and up_volume_ratio >= 0.52:
        breadth_state = BreadthState.HEALTHY
    elif percent_advancing <= 0.40 and up_volume_ratio <= 0.45:
        breadth_state = BreadthState.BROAD_WEAKNESS
    elif percent_advancing <= 0.46 or breadth_divergence_score >= 1.2:
        breadth_state = BreadthState.NARROW_LEADERSHIP
    else:
        breadth_state = BreadthState.MIXED

    approved_sector_ids: list[str] = []
    crowded_sector_ids: list[str] = []
    anomaly_detected = False
    for sector in routing_input.sector_leadership_snapshots:
        if (
            sector.sector_internal_breadth_score >= 0.60
            and sector.sector_relative_strength > 0.50
            and sector.leadership_concentration_score <= 0.65
        ):
            approved_sector_ids.append(sector.sector_id)
        if sector.leadership_concentration_score >= 0.75:
            crowded_sector_ids.append(sector.sector_id)
        if sector.leadership_concentration_score >= 0.90:
            anomaly_detected = True

    distortion = routing_input.index_distortion_snapshot
    distortion_warning = bool(
        distortion.distorted_index_warning
        or distortion.index_distortion_score >= 0.80
        or (distortion.equal_weight_divergence_percent or 0.0) >= 1.5
        or (distortion.large_cap_vs_small_mid_divergence_percent or 0.0) >= 1.5
        or distortion.top_2_contribution_share >= 0.40
        or distortion.top_5_contribution_share >= 0.70
    )

    if distortion_warning:
        leadership_state = LeadershipState.INDEX_DISTORTION
    elif anomaly_detected:
        leadership_state = LeadershipState.LEADERSHIP_ANOMALY
    elif crowded_sector_ids:
        leadership_state = LeadershipState.CROWDED_LEADERSHIP
    elif approved_sector_ids:
        leadership_state = LeadershipState.HEALTHY_SECTOR_LEADERSHIP
    elif routing_input.sector_leadership_snapshots:
        leadership_state = LeadershipState.NO_CLEAR_LEADERSHIP
    else:
        leadership_state = LeadershipState.UNKNOWN

    if any(entry.severity == "BLOCKING" for entry in gaps):
        internal_risk_state = InternalRiskState.INTERNAL_STRESS
    elif distortion_warning or breadth_divergence_score >= 1.5:
        internal_risk_state = InternalRiskState.HIGH_INTERNAL_RISK
    elif breadth_state in {BreadthState.MIXED, BreadthState.NARROW_LEADERSHIP}:
        internal_risk_state = InternalRiskState.MODERATE_INTERNAL_RISK
    else:
        internal_risk_state = InternalRiskState.LOW_INTERNAL_RISK

    matched_outlier = _matching_outlier(routing_input)
    eligible_candidate_ids: list[str] = []
    restricted_candidate_ids: list[str] = []
    outlier_state = OutlierMomentumState.NO_OUTLIER
    if routing_input.candidate_is_outlier_momentum and matched_outlier is not None:
        evidence_present = bool(
            matched_outlier.liquidity_evidence_ref
            and matched_outlier.required_stop_discipline
            and matched_outlier.slippage_risk_note
            and matched_outlier.no_execution_flag
        )
        catalyst_present = bool(
            matched_outlier.news_catalyst_ref
            or matched_outlier.disclosure_theme_catalyst_ref
            or matched_outlier.ipo_new_listing_flag
            or (matched_outlier.low_float_scarcity_proxy or 0) > 0
        )
        if matched_outlier.price_change_percent >= 15 and not catalyst_present:
            gaps.append(_gap(routing_input.routing_review_id, "OUTLIER-SOURCE-GAP", "OUTLIER_PRICE_CHANGE_WITHOUT_SOURCE_REF", "BLOCKING", "outlier price change lacks catalyst evidence"))
            outlier_state = OutlierMomentumState.OUTLIER_BLOCKED
        elif not evidence_present:
            restricted_candidate_ids.append(matched_outlier.candidate_id)
            outlier_state = OutlierMomentumState.OUTLIER_MOMENTUM_RESTRICTED
        elif (
            matched_outlier.price_change_percent >= 10
            and matched_outlier.relative_volume >= 3
            and matched_outlier.trading_value_surge >= 2
            and catalyst_present
        ):
            eligible_candidate_ids.append(matched_outlier.candidate_id)
            outlier_state = OutlierMomentumState.OUTLIER_MOMENTUM_ALLOWED
        else:
            restricted_candidate_ids.append(matched_outlier.candidate_id)
            outlier_state = OutlierMomentumState.OUTLIER_WATCH

        if matched_outlier.max_outlier_sleeve_allocation > routing_input.outlier_sleeve_policy.max_portfolio_allocation:
            restricted_candidate_ids.append(matched_outlier.candidate_id)
            outlier_state = OutlierMomentumState.OUTLIER_MOMENTUM_RESTRICTED
            gaps.append(_gap(routing_input.routing_review_id, "OUTLIER-ALLOCATION-CAP", "OUTLIER_SLEEVE_MAX_ALLOCATION_EXCEEDED", "WARNING", "outlier sleeve allocation exceeds policy"))
        if matched_outlier.max_per_name_risk > routing_input.outlier_sleeve_policy.max_per_name_risk:
            restricted_candidate_ids.append(matched_outlier.candidate_id)
            outlier_state = OutlierMomentumState.OUTLIER_MOMENTUM_RESTRICTED
            gaps.append(_gap(routing_input.routing_review_id, "OUTLIER-RISK-CAP", "OUTLIER_PER_NAME_RISK_EXCEEDED", "WARNING", "outlier per-name risk exceeds policy"))

    primary_decision = BreadthLeadershipRoutingDecision.BROAD_MARKET_OK
    decision_reason = "broad participation supports normal routing"

    if any(entry.severity == "BLOCKING" for entry in gaps) or impossible_counts:
        primary_decision = BreadthLeadershipRoutingDecision.BLOCKED
        decision_reason = "blocking leakage or impossible breadth data detected"
    elif event_risk_blocked:
        primary_decision = BreadthLeadershipRoutingDecision.BLOCKED
        decision_reason = "event risk hard gate blocks promotion"
        constraints.append("EVENT_RISK_HARD_GATE")
    elif risk_budget_blocked:
        primary_decision = BreadthLeadershipRoutingDecision.BLOCKED
        decision_reason = "position sizing hard gate blocks promotion"
        constraints.append("RISK_BUDGET_HARD_GATE")
    elif not provider_ready or missing_available_at or stale_data_detected or position_gap or event_gap:
        primary_decision = BreadthLeadershipRoutingDecision.DATA_GAP
        decision_reason = "breadth routing evidence is incomplete or stale"
    elif routing_input.candidate_is_outlier_momentum and matched_outlier is not None:
        if outlier_state == OutlierMomentumState.OUTLIER_MOMENTUM_ALLOWED:
            primary_decision = BreadthLeadershipRoutingDecision.OUTLIER_MOMENTUM_ALLOWED
            decision_reason = "candidate is eligible for restricted outlier sleeve only"
            constraints.extend(["SEPARATE_OUTLIER_SLEEVE_ONLY", "NO_NORMAL_BROAD_MARKET_PERMISSION"])
        else:
            primary_decision = BreadthLeadershipRoutingDecision.OUTLIER_MOMENTUM_RESTRICTED
            decision_reason = "outlier candidate exists but sleeve evidence is restricted"
            constraints.extend(["SEPARATE_OUTLIER_SLEEVE_ONLY", "REQUIRE_STRICT_STOP_DISCIPLINE"])
    elif breadth_state in {BreadthState.BROAD_STRENGTH, BreadthState.HEALTHY} and leadership_state not in {LeadershipState.CROWDED_LEADERSHIP, LeadershipState.LEADERSHIP_ANOMALY, LeadershipState.INDEX_DISTORTION} and internal_risk_state == InternalRiskState.LOW_INTERNAL_RISK:
        primary_decision = BreadthLeadershipRoutingDecision.BROAD_MARKET_OK
        decision_reason = "broad participation and low internal risk support normal routing"
    elif leadership_state == LeadershipState.HEALTHY_SECTOR_LEADERSHIP and routing_input.candidate_is_leadership_sector:
        if routing_input.candidate_is_large_cap and (distortion.large_cap_vs_small_mid_divergence_percent or 0.0) >= 0.75:
            primary_decision = BreadthLeadershipRoutingDecision.LARGE_CAP_ONLY
            decision_reason = "leadership is concentrated in large-cap strength"
        elif len(approved_sector_ids) == 1:
            primary_decision = BreadthLeadershipRoutingDecision.SECTOR_ONLY
            decision_reason = "weak breadth but confirmed sector leadership supports sector-only routing"
        else:
            primary_decision = BreadthLeadershipRoutingDecision.LEADERSHIP_ONLY
            decision_reason = "weak breadth but confirmed leadership sectors remain eligible"
    elif leadership_state in {LeadershipState.CROWDED_LEADERSHIP, LeadershipState.LEADERSHIP_ANOMALY, LeadershipState.INDEX_DISTORTION}:
        if routing_input.candidate_is_large_cap and routing_input.candidate_is_leadership_sector:
            primary_decision = BreadthLeadershipRoutingDecision.REDUCE_SIZE
            decision_reason = "leadership is crowded or distorted and size must be reduced"
        elif routing_input.candidate_is_leadership_sector:
            primary_decision = BreadthLeadershipRoutingDecision.BLOCK_CHASING
            decision_reason = "crowded leadership blocks chasing behavior"
        else:
            primary_decision = BreadthLeadershipRoutingDecision.WATCH_NON_LEADERS
            decision_reason = "non-leaders are watch-only under weak participation"
    else:
        primary_decision = BreadthLeadershipRoutingDecision.WATCH_NON_LEADERS
        decision_reason = "weak participation supports watch-only routing for non-leaders"

    if breadth_state in {BreadthState.NARROW_LEADERSHIP, BreadthState.BROAD_WEAKNESS, BreadthState.MIXED}:
        warnings.append("WEAK_BREADTH")
        constraints.append("WATCH_NON_LEADERS")
    if leadership_state == LeadershipState.CROWDED_LEADERSHIP:
        constraints.extend(["CROWDED_LEADERSHIP", "REDUCE_SIZE", "BLOCK_CHASING"])
    if leadership_state == LeadershipState.INDEX_DISTORTION:
        constraints.extend(["INDEX_DISTORTION", "REDUCE_SIZE", "BLOCK_CHASING"])
    if leadership_state == LeadershipState.LEADERSHIP_ANOMALY:
        constraints.extend(["LEADERSHIP_ANOMALY", "BLOCK_CHASING"])
    if routing_input.market_regime_risk_appetite == "RISK_OFF":
        constraints.append("RISK_OFF_RESTRICTED")
    if routing_input.position_sizing_decision == "REDUCE_SIZE":
        constraints.append("REDUCE_SIZE")
    if event_gap:
        constraints.append("EVENT_RISK_DATA_GAP")
    if position_gap:
        constraints.append("POSITION_SIZING_DATA_GAP")

    constraints = list(dict.fromkeys(constraints))
    warnings = list(dict.fromkeys(warnings))

    summary_report = BreadthRoutingSummaryReport(
        report_id=f"{routing_input.routing_review_id}-SUMMARY-REPORT",
        primary_decision=primary_decision,
        breadth_state=breadth_state,
        leadership_state=leadership_state,
        outlier_momentum_state=outlier_state,
        internal_risk_state=internal_risk_state,
        decision_reason=decision_reason,
        downstream_constraints=constraints,
        approved_sector_ids=approved_sector_ids,
    )
    breadth_input_snapshot_report = BreadthInputSnapshotReport(
        report_id=f"{routing_input.routing_review_id}-INPUT-SNAPSHOT-REPORT",
        snapshot=snapshot,
    )
    advance_decline_report = AdvanceDeclineReport(
        report_id=f"{routing_input.routing_review_id}-ADVANCE-DECLINE-REPORT",
        advance_decline_ratio=round(advance_decline_ratio, 4),
        advance_decline_spread=advance_decline_spread,
        percent_advancing=round(percent_advancing, 4),
        percent_declining=round(percent_declining, 4),
        participation_score=participation_score,
        breadth_state=breadth_state,
    )
    new_high_low_report = NewHighLowReport(
        report_id=f"{routing_input.routing_review_id}-NEW-HIGH-LOW-REPORT",
        new_high_low_ratio=round(new_high_low_ratio, 4),
        new_high_low_spread=new_high_low_spread,
        breadth_deterioration_score=breadth_deterioration_score,
    )
    up_down_volume_participation_report = UpDownVolumeParticipationReport(
        report_id=f"{routing_input.routing_review_id}-UP-DOWN-VOLUME-REPORT",
        up_volume_ratio=round(up_volume_ratio, 4),
        down_volume_ratio=round(down_volume_ratio, 4),
        breadth_thrust_proxy=breadth_thrust_proxy,
        relative_volume=snapshot.relative_volume,
        market_health_score=market_health_score,
    )
    sector_leadership_report = SectorLeadershipReport(
        report_id=f"{routing_input.routing_review_id}-SECTOR-LEADERSHIP-REPORT",
        approved_sector_ids=approved_sector_ids,
        sector_count=len(routing_input.sector_leadership_snapshots),
        healthy_sector_count=len(approved_sector_ids),
        crowded_sector_count=len(crowded_sector_ids),
        leadership_state=leadership_state,
    )
    leadership_concentration_report = LeadershipConcentrationReport(
        report_id=f"{routing_input.routing_review_id}-LEADERSHIP-CONCENTRATION-REPORT",
        leadership_state=leadership_state,
        crowded_sector_ids=crowded_sector_ids,
        maximum_concentration_score=max([sector.leadership_concentration_score for sector in routing_input.sector_leadership_snapshots] or [0.0]),
        concentration_warning=bool(crowded_sector_ids),
    )
    index_distortion_report = IndexDistortionReport(
        report_id=f"{routing_input.routing_review_id}-INDEX-DISTORTION-REPORT",
        distortion_snapshot=distortion,
        leadership_state=leadership_state,
        distortion_warning=distortion_warning,
    )
    equal_weight_divergence_report = EqualWeightDivergenceReport(
        report_id=f"{routing_input.routing_review_id}-EQUAL-WEIGHT-DIVERGENCE-REPORT",
        equal_weight_divergence_percent=distortion.equal_weight_divergence_percent,
        large_cap_vs_small_mid_divergence_percent=distortion.large_cap_vs_small_mid_divergence_percent,
        breadth_divergence_score=breadth_divergence_score,
        divergence_warning=breadth_divergence_score >= 1.0,
    )
    outlier_momentum_candidate_report = OutlierMomentumCandidateReport(
        report_id=f"{routing_input.routing_review_id}-OUTLIER-MOMENTUM-CANDIDATE-REPORT",
        selected_candidate_id=matched_outlier.candidate_id if matched_outlier else None,
        selected_symbol=matched_outlier.symbol if matched_outlier else None,
        outlier_momentum_state=outlier_state,
        eligible_candidate_ids=eligible_candidate_ids,
        restricted_candidate_ids=restricted_candidate_ids,
    )
    outlier_sleeve_risk_report = OutlierSleeveRiskReport(
        report_id=f"{routing_input.routing_review_id}-OUTLIER-SLEEVE-RISK-REPORT",
        policy_id=routing_input.outlier_sleeve_policy.policy_id,
        max_portfolio_allocation=routing_input.outlier_sleeve_policy.max_portfolio_allocation,
        max_per_name_risk=routing_input.outlier_sleeve_policy.max_per_name_risk,
        max_daily_loss=routing_input.outlier_sleeve_policy.max_daily_loss,
        max_outlier_names=routing_input.outlier_sleeve_policy.max_outlier_names,
        liquidity_evidence_required=routing_input.outlier_sleeve_policy.mandatory_liquidity_evidence,
        stop_discipline_required=routing_input.outlier_sleeve_policy.mandatory_stop_discipline,
        slippage_note_required=routing_input.outlier_sleeve_policy.mandatory_slippage_note,
        no_execution_required=routing_input.outlier_sleeve_policy.mandatory_no_execution_flag,
        event_risk_compatibility_required=routing_input.outlier_sleeve_policy.event_risk_compatibility_required,
    )
    downstream_constraint_report = DownstreamRoutingConstraintReport(
        report_id=f"{routing_input.routing_review_id}-DOWNSTREAM-CONSTRAINT-REPORT",
        constraints=constraints,
        warnings=warnings,
        block_promotion=primary_decision in {BreadthLeadershipRoutingDecision.BLOCKED, BreadthLeadershipRoutingDecision.DATA_GAP},
    )
    provider_readiness_report = BreadthRoutingProviderReadinessReport(
        report_id=f"{routing_input.routing_review_id}-PROVIDER-READINESS-REPORT",
        provider_ready=provider_ready,
        missing_refs=missing_refs,
        missing_levels=missing_levels,
        canonical_contract_present=_safe_ref(routing_input.canonical_data_contract_ref),
    )
    leakage_findings = [
        finding for finding, active in (
            ("FUTURE_BREADTH_LEAKAGE", future_breadth_leakage),
            ("FUTURE_SECTOR_LEADERSHIP_LEAKAGE", future_sector_leadership_leakage),
            ("FUTURE_OUTLIER_CATALYST_LEAKAGE", future_outlier_catalyst_leakage),
            ("MISSING_AVAILABLE_AT", missing_available_at),
            ("STALE_DATA_DETECTED", stale_data_detected),
        ) if active
    ]
    leakage_report = BreadthRoutingLeakageReport(
        report_id=f"{routing_input.routing_review_id}-LEAKAGE-REPORT",
        future_breadth_leakage=future_breadth_leakage,
        future_sector_leadership_leakage=future_sector_leadership_leakage,
        future_outlier_catalyst_leakage=future_outlier_catalyst_leakage,
        missing_available_at=missing_available_at,
        stale_data_detected=stale_data_detected,
        findings=leakage_findings,
    )
    gaps.append(_gap(routing_input.routing_review_id, "REPORT-GENERATED", "BREADTH_ROUTING_REPORT_GENERATED", "REPORT_ONLY", "breadth routing report generated"))
    gap_report = BreadthRoutingGapReport(
        gap_report_id=f"{routing_input.routing_review_id}-GAP-REPORT",
        primary_decision=primary_decision,
        gap_entries=gaps,
        blocking_gap_count=sum(1 for entry in gaps if entry.severity == "BLOCKING"),
        warning_gap_count=sum(1 for entry in gaps if entry.severity == "WARNING"),
        gap_categories=[entry.gap_category for entry in gaps],
    )
    training_feature_integration_report = BreadthRoutingTrainingFeatureIntegrationReport(
        report_id=f"{routing_input.routing_review_id}-TRAINING-FEATURE-REPORT",
        routing_feature_snapshot_id=snapshot.snapshot_id,
        breadth_state_label=breadth_state.value,
        leadership_state_label=leadership_state.value,
        outlier_momentum_state_label=outlier_state.value,
        internal_risk_state_label=internal_risk_state.value,
        primary_routing_decision=primary_decision.value,
        participation_score=participation_score,
        breadth_deterioration_score=breadth_deterioration_score,
        breadth_divergence_score=breadth_divergence_score,
        market_health_score=market_health_score,
        outlier_eligible_flag=outlier_state == OutlierMomentumState.OUTLIER_MOMENTUM_ALLOWED,
        event_risk_blocked_flag=event_risk_blocked,
        risk_budget_blocked_flag=risk_budget_blocked,
        available_at_present=not missing_available_at,
        training_feature_ready=primary_decision not in {BreadthLeadershipRoutingDecision.BLOCKED, BreadthLeadershipRoutingDecision.DATA_GAP, BreadthLeadershipRoutingDecision.REJECTED},
    )

    return routing_input.model_copy(
        update={
            "summary_report": summary_report,
            "breadth_input_snapshot_report": breadth_input_snapshot_report,
            "advance_decline_report": advance_decline_report,
            "new_high_low_report": new_high_low_report,
            "up_down_volume_participation_report": up_down_volume_participation_report,
            "sector_leadership_report": sector_leadership_report,
            "leadership_concentration_report": leadership_concentration_report,
            "index_distortion_report": index_distortion_report,
            "equal_weight_divergence_report": equal_weight_divergence_report,
            "outlier_momentum_candidate_report": outlier_momentum_candidate_report,
            "outlier_sleeve_risk_report": outlier_sleeve_risk_report,
            "downstream_constraint_report": downstream_constraint_report,
            "provider_readiness_report": provider_readiness_report,
            "leakage_report": leakage_report,
            "gap_report": gap_report,
            "training_feature_integration_report": training_feature_integration_report,
        }
    )
