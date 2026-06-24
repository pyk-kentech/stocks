from __future__ import annotations

from datetime import timedelta

from stock_risk_mcp.market_regime_guard import validate_market_regime_metadata_safety
from stock_risk_mcp.market_regime_models import (
    CrossAssetConflictReport,
    CrossAssetInputSnapshotReport,
    DirectionRegimeReport,
    DownstreamConstraintReport,
    FXRateDollarStressReport,
    MarketDirection,
    MarketRegimeDecision,
    MarketRegimeGapCategory,
    MarketRegimeGapEntry,
    MarketRegimeGapReport,
    MarketRegimeInput,
    MarketRegimeSummaryReport,
    MarketRiskAppetite,
    MarketStressState,
    MarketVolatilityState,
    RiskAppetiteReport,
    TrainingFeatureIntegrationReport,
    VolatilityRegimeReport,
)


def _gap(input_id: str, suffix: str, category, severity: str, message: str) -> MarketRegimeGapEntry:
    return MarketRegimeGapEntry(
        gap_id=f"{input_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def _trend(value: float, *, up: float = 0.25, down: float = -0.25) -> str:
    if value >= up:
        return "UP"
    if value <= down:
        return "DOWN"
    return "FLAT"


def _vix_level_bucket(vix: float) -> str:
    if vix >= 28:
        return "HIGH_VOL"
    if vix <= 15:
        return "LOW_VOL"
    return "NORMAL_VOL"


def _vix_change_bucket(change: float) -> str:
    if change >= 10:
        return "VOL_EXPANSION"
    if change <= -10:
        return "VOL_COMPRESSION"
    return "VOL_STABLE"


def build_market_regime(regime_input: MarketRegimeInput) -> MarketRegimeInput:
    for audit in regime_input.audit_records:
        validate_market_regime_metadata_safety(
            {"source_path": audit.source_path, "operator_context": audit.operator_context},
            context="market regime",
        )

    snapshot = regime_input.snapshot
    gaps: list[MarketRegimeGapEntry] = []
    missing_evidence: list[str] = []
    stale_evidence: list[str] = []
    supporting_evidence: list[str] = []
    conflicting_evidence: list[str] = []

    if snapshot.available_at is None:
        missing_evidence.append("AVAILABLE_AT")
        gaps.append(_gap(regime_input.regime_id, "MISSING-AVAILABLE-AT", MarketRegimeGapCategory.MISSING_AVAILABLE_AT, "WARNING", "available_at is missing"))
        age_minutes = None
    else:
        age = snapshot.anchor_at - snapshot.available_at
        age_minutes = int(age.total_seconds() // 60)
        if snapshot.available_at > snapshot.anchor_at:
            gaps.append(_gap(regime_input.regime_id, "FUTURE-LEAKAGE", MarketRegimeGapCategory.FUTURE_FEATURE_LEAKAGE, "BLOCKING", "available_at exceeds anchor_at"))
        if age > timedelta(minutes=snapshot.data_freshness_policy.max_age_minutes):
            stale_evidence.extend(snapshot.data_freshness_policy.critical_inputs)
            gaps.append(_gap(regime_input.regime_id, "STALE-CRITICAL-DATA", MarketRegimeGapCategory.STALE_CRITICAL_DATA, "WARNING", "critical snapshot evidence is stale"))

    for required_name, asset in (
        ("NQ", snapshot.nq),
        ("ES", snapshot.es),
        ("VIX", snapshot.vix),
        ("DXY", snapshot.dxy),
        ("US10Y", snapshot.us10y),
        ("USDKRW", snapshot.usdkrw),
    ):
        if not asset.source_ref:
            missing_evidence.append(required_name)
            gaps.append(_gap(regime_input.regime_id, f"MISSING-{required_name}-SOURCE", MarketRegimeGapCategory.MISSING_SOURCE_REF, "WARNING", f"{required_name} source ref is missing"))
        validate_market_regime_metadata_safety({"source_ref": asset.source_ref}, context=f"{required_name} source ref")

    if snapshot.cnn_fear_greed_feature_ref:
        supporting_evidence.append("CNN_FEAR_GREED_OPTIONAL_PRESENT")
    else:
        missing_evidence.append("CNN_FEAR_GREED_OPTIONAL")
        gaps.append(_gap(regime_input.regime_id, "OPTIONAL-CNN-FEATURE-MISSING", MarketRegimeGapCategory.OPTIONAL_CNN_FEATURE_MISSING, "REPORT_ONLY", "optional cnn fear and greed feature ref is missing"))

    nq_trend = _trend(snapshot.nq.pct_change_1d)
    es_trend = _trend(snapshot.es.pct_change_1d)
    dxy_trend = _trend(snapshot.dxy.pct_change_1d, up=0.2, down=-0.2)
    us10y_trend = _trend(snapshot.us10y.pct_change_1d, up=0.3, down=-0.3)
    divergence = nq_trend != es_trend and {nq_trend, es_trend} == {"UP", "DOWN"}
    if divergence or abs(snapshot.nq.pct_change_1d - snapshot.es.pct_change_1d) >= 1.5:
        conflicting_evidence.append("NQ_ES_DIVERGENCE")
        gaps.append(_gap(regime_input.regime_id, "CONFLICT-DIVERGENCE", MarketRegimeGapCategory.CONFLICTING_EVIDENCE, "REPORT_ONLY", "NQ and ES are diverging"))

    vix_level_bucket = _vix_level_bucket(snapshot.vix.last_value)
    vix_change_bucket = _vix_change_bucket(snapshot.vix.pct_change_1d)
    usdkrw_stress_bucket = "FX_STRESS" if snapshot.usdkrw.pct_change_1d >= 1.0 or snapshot.usdkrw.last_value >= 1400 else "NORMAL"

    confirmation_score = 0
    conflict_score = 0
    if nq_trend == "UP":
        confirmation_score += 1
        supporting_evidence.append("NQ_UP")
    elif nq_trend == "DOWN":
        conflict_score += 1
        conflicting_evidence.append("NQ_DOWN")
    if es_trend == "UP":
        confirmation_score += 1
        supporting_evidence.append("ES_UP")
    elif es_trend == "DOWN":
        conflict_score += 1
        conflicting_evidence.append("ES_DOWN")
    if vix_level_bucket in {"LOW_VOL", "NORMAL_VOL"} and vix_change_bucket != "VOL_EXPANSION":
        confirmation_score += 1
        supporting_evidence.append("VOL_NOT_STRESSED")
    else:
        conflict_score += 1
        conflicting_evidence.append("VOL_STRESS")
    if dxy_trend != "UP":
        confirmation_score += 1
        supporting_evidence.append("DXY_NOT_SURGING")
    else:
        conflict_score += 1
        conflicting_evidence.append("DXY_SURGING")
    if us10y_trend != "UP":
        confirmation_score += 1
        supporting_evidence.append("RATES_NOT_SURGING")
    else:
        conflict_score += 1
        conflicting_evidence.append("RATE_SURGE")
    if usdkrw_stress_bucket == "NORMAL":
        confirmation_score += 1
        supporting_evidence.append("FX_CALM")
    else:
        conflict_score += 1
        conflicting_evidence.append("FX_STRESS")
    if divergence:
        conflict_score += 2

    if (snapshot.usdkrw.pct_change_1d >= 1.0 and snapshot.dxy.pct_change_1d >= 0.5) or (snapshot.us10y.pct_change_1d >= 0.8 and snapshot.vix.pct_change_1d >= 10):
        stress_state = MarketStressState.CROSS_ASSET_STRESS
    elif snapshot.usdkrw.pct_change_1d >= 1.0:
        stress_state = MarketStressState.FX_STRESS
    elif snapshot.us10y.pct_change_1d >= 0.8:
        stress_state = MarketStressState.RATE_STRESS
    elif snapshot.dxy.pct_change_1d >= 0.5:
        stress_state = MarketStressState.DOLLAR_STRESS
    else:
        stress_state = MarketStressState.NORMAL

    if vix_change_bucket == "VOL_EXPANSION":
        volatility_state = MarketVolatilityState.VOL_EXPANSION
    elif vix_level_bucket == "HIGH_VOL":
        volatility_state = MarketVolatilityState.HIGH_VOL
    elif vix_level_bucket == "LOW_VOL":
        volatility_state = MarketVolatilityState.LOW_VOL
    else:
        volatility_state = MarketVolatilityState.NORMAL_VOL

    if nq_trend == "UP" and es_trend == "UP" and abs(snapshot.nq.pct_change_1d) < 0.15 and abs(snapshot.es.pct_change_1d) < 0.15:
        market_direction = MarketDirection.SIDEWAYS
    elif nq_trend == "DOWN" and es_trend == "DOWN":
        market_direction = MarketDirection.BEAR
    elif nq_trend == "UP" and es_trend == "UP":
        market_direction = MarketDirection.BULL
    elif divergence:
        market_direction = MarketDirection.TRANSITION
    else:
        market_direction = MarketDirection.SIDEWAYS

    if market_direction == MarketDirection.BULL and volatility_state in {MarketVolatilityState.LOW_VOL, MarketVolatilityState.NORMAL_VOL} and stress_state == MarketStressState.NORMAL:
        risk_appetite = MarketRiskAppetite.RISK_ON
    elif market_direction == MarketDirection.BEAR or volatility_state in {MarketVolatilityState.HIGH_VOL, MarketVolatilityState.VOL_EXPANSION} or stress_state != MarketStressState.NORMAL:
        risk_appetite = MarketRiskAppetite.RISK_OFF
    elif divergence or conflict_score > confirmation_score:
        risk_appetite = MarketRiskAppetite.MIXED
    else:
        risk_appetite = MarketRiskAppetite.UNKNOWN

    if snapshot.available_at is None:
        data_staleness_score = 100
    else:
        data_staleness_score = max(0, min(100, int((age_minutes or 0) / snapshot.data_freshness_policy.max_age_minutes * 100)))

    if any(entry.severity == "BLOCKING" for entry in gaps):
        decision = MarketRegimeDecision.BLOCKED
    elif snapshot.available_at is None or any(entry.gap_category in {MarketRegimeGapCategory.STALE_CRITICAL_DATA, MarketRegimeGapCategory.MISSING_SOURCE_REF} for entry in gaps):
        decision = MarketRegimeDecision.GAP
    elif conflict_score >= confirmation_score + 2:
        decision = MarketRegimeDecision.RESEARCH_ONLY
    else:
        decision = MarketRegimeDecision.TRAINING_FEATURE_READY

    confidence_bucket = "HIGH" if confirmation_score >= 5 and conflict_score <= 1 else "MEDIUM" if confirmation_score >= 3 else "LOW"
    if decision == MarketRegimeDecision.RESEARCH_ONLY:
        confidence_bucket = "LOW"

    constraints: list[str] = []
    if decision in {MarketRegimeDecision.BLOCKED, MarketRegimeDecision.GAP}:
        constraints.extend(["WATCH_ONLY", "BLOCK_PROMOTION_IF_EVIDENCE_IS_INSUFFICIENT"])
    elif risk_appetite == MarketRiskAppetite.RISK_OFF:
        constraints.extend(["REDUCE_NEW_ENTRIES", "REQUIRE_SMALLER_POSITION_SIZING", "PREFER_CASH_CONTROL", "REQUIRE_EVENT_RISK_CHECK"])
    elif risk_appetite == MarketRiskAppetite.MIXED or market_direction == MarketDirection.TRANSITION:
        constraints.extend(["REQUIRE_BREADTH_CONFIRMATION", "REQUIRE_EVENT_RISK_CHECK", "WATCH_ONLY"])
    else:
        constraints.append("ALLOW_NORMAL_RISK")
    if confidence_bucket == "LOW" and "BLOCK_PROMOTION_IF_EVIDENCE_IS_INSUFFICIENT" not in constraints:
        constraints.append("BLOCK_PROMOTION_IF_EVIDENCE_IS_INSUFFICIENT")

    risk_state = f"{risk_appetite.value}|{market_direction.value}|{volatility_state.value}|{stress_state.value}"
    final_regime_label = risk_state
    if decision == MarketRegimeDecision.TRAINING_FEATURE_READY and snapshot.cnn_fear_greed_feature_ref:
        decision = MarketRegimeDecision.REGIME_READY if conflict_score > confirmation_score else MarketRegimeDecision.TRAINING_FEATURE_READY

    summary_report = MarketRegimeSummaryReport(
        report_id=f"{regime_input.regime_id}-SUMMARY-REPORT",
        decision=decision,
        final_regime_label=final_regime_label,
        risk_appetite=risk_appetite,
        market_direction=market_direction,
        volatility_state=volatility_state,
        stress_state=stress_state,
        confidence_bucket=confidence_bucket,
        supporting_evidence=supporting_evidence,
        conflicting_evidence=conflicting_evidence,
        missing_evidence=missing_evidence,
        stale_evidence=stale_evidence,
    )
    input_snapshot_report = CrossAssetInputSnapshotReport(
        report_id=f"{regime_input.regime_id}-INPUT-SNAPSHOT-REPORT",
        snapshot=snapshot,
    )
    risk_appetite_report = RiskAppetiteReport(
        report_id=f"{regime_input.regime_id}-RISK-APPETITE-REPORT",
        risk_appetite=risk_appetite,
        evidence=supporting_evidence,
    )
    direction_regime_report = DirectionRegimeReport(
        report_id=f"{regime_input.regime_id}-DIRECTION-REPORT",
        market_direction=market_direction,
        nq_trend=nq_trend,
        es_trend=es_trend,
    )
    volatility_regime_report = VolatilityRegimeReport(
        report_id=f"{regime_input.regime_id}-VOLATILITY-REPORT",
        volatility_state=volatility_state,
        vix_level_bucket=vix_level_bucket,
        vix_change_bucket=vix_change_bucket,
    )
    stress_report = FXRateDollarStressReport(
        report_id=f"{regime_input.regime_id}-STRESS-REPORT",
        stress_state=stress_state,
        dxy_trend=dxy_trend,
        us10y_trend=us10y_trend,
        usdkrw_stress_bucket=usdkrw_stress_bucket,
    )
    cross_asset_conflict_report = CrossAssetConflictReport(
        report_id=f"{regime_input.regime_id}-CONFLICT-REPORT",
        conflict_count=len(conflicting_evidence),
        confirmation_score=confirmation_score,
        conflict_score=conflict_score,
        conflicts=conflicting_evidence,
    )
    downstream_constraint_report = DownstreamConstraintReport(
        report_id=f"{regime_input.regime_id}-DOWNSTREAM-CONSTRAINT-REPORT",
        constraints=constraints,
        block_promotion_if_insufficient_evidence="BLOCK_PROMOTION_IF_EVIDENCE_IS_INSUFFICIENT" in constraints,
    )
    training_feature_integration_report = TrainingFeatureIntegrationReport(
        report_id=f"{regime_input.regime_id}-TRAINING-FEATURE-REPORT",
        regime_feature_snapshot_id=snapshot.snapshot_id,
        risk_state=risk_state,
        risk_appetite_label=risk_appetite.value,
        market_direction_label=market_direction.value,
        volatility_state_label=volatility_state.value,
        stress_state_label=stress_state.value,
        cross_asset_confirmation_score=confirmation_score,
        cross_asset_conflict_score=conflict_score,
        data_staleness_score=data_staleness_score,
        available_at_present=snapshot.available_at is not None,
        cnn_fear_greed_feature_present=bool(snapshot.cnn_fear_greed_feature_ref),
        cnn_fear_greed_source_ref=snapshot.cnn_fear_greed_feature_ref,
        training_feature_ready=decision in {MarketRegimeDecision.TRAINING_FEATURE_READY, MarketRegimeDecision.REGIME_READY},
    )
    gaps.append(_gap(regime_input.regime_id, "REPORT-GENERATED", MarketRegimeGapCategory.REPORT_GENERATED, "REPORT_ONLY", "market regime report generated"))
    gap_report = MarketRegimeGapReport(
        gap_report_id=f"{regime_input.regime_id}-GAP-REPORT",
        decision=decision,
        gap_entries=gaps,
        blocking_gap_count=sum(1 for item in gaps if item.severity == "BLOCKING"),
        warning_gap_count=sum(1 for item in gaps if item.severity == "WARNING"),
    )
    return regime_input.model_copy(
        update={
            "summary_report": summary_report,
            "input_snapshot_report": input_snapshot_report,
            "risk_appetite_report": risk_appetite_report,
            "direction_regime_report": direction_regime_report,
            "volatility_regime_report": volatility_regime_report,
            "stress_report": stress_report,
            "cross_asset_conflict_report": cross_asset_conflict_report,
            "downstream_constraint_report": downstream_constraint_report,
            "training_feature_integration_report": training_feature_integration_report,
            "gap_report": gap_report,
        }
    )
