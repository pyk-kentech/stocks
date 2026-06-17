from __future__ import annotations

from stock_risk_mcp.domestic_market_regime_models import (
    DOMESTIC_MARKET_REGIME_METADATA,
    UNSAFE_EXECUTION_PATTERNS,
    MarketRegimeClassification,
    MarketRegimeEvidenceSnapshot,
    MarketRegimeEvidenceStrengthBucket,
    MarketRegimeFixture,
    MarketRegimeGapCategory,
    MarketRegimeGapReport,
    MarketRegimeLabel,
    MarketRegimeReport,
    MarketRegimeSafetyBoundary,
    MarketRegimeSafetyReport,
    RegimeAwareContextReference,
)


def _snapshot_id(fixture: MarketRegimeFixture) -> str:
    return f"{fixture.fixture_id}-evidence-snapshot"


def _classification_id(fixture: MarketRegimeFixture) -> str:
    return f"{fixture.fixture_id}-classification"


def _report_id(fixture: MarketRegimeFixture) -> str:
    return f"{fixture.fixture_id}-market-regime-report"


def _contains_unsafe_pattern(value: str) -> bool:
    upper_value = value.upper()
    return any(pattern in upper_value for pattern in UNSAFE_EXECUTION_PATTERNS)


def _has_missing_core_values(fixture: MarketRegimeFixture) -> bool:
    input_set = fixture.market_regime_input_set
    return any(
        value is None
        for value in (
            input_set.index_evidence.short_return_pct,
            input_set.index_evidence.medium_return_pct,
            input_set.breadth_evidence.breadth_proxy_pct,
            input_set.liquidity_evidence.turnover_proxy_ratio,
            input_set.liquidity_evidence.volume_expansion_proxy_ratio,
            input_set.volatility_evidence.volatility_expansion_proxy_ratio,
            input_set.risk_evidence.risk_off_warning_score,
            input_set.risk_evidence.stress_marker_count,
        )
    ) or not input_set.sector_evidence.sector_return_distribution


def _validation_categories(fixture: MarketRegimeFixture) -> list[str]:
    categories: list[str] = []
    input_set = fixture.market_regime_input_set
    if input_set.strategy_track != fixture.market_regime_config.strategy_track:
        categories.append(MarketRegimeGapCategory.UNSUPPORTED_TRACK.value)
    if str(input_set.market_profile_summary.get("market_id", "")).upper() != "KRX":
        categories.append(MarketRegimeGapCategory.MISSING_MARKET_PROFILE.value)
    if input_set.index_evidence.stale or input_set.sector_evidence.stale or input_set.breadth_evidence.stale or input_set.liquidity_evidence.stale or input_set.volatility_evidence.stale or input_set.risk_evidence.stale:
        categories.append(MarketRegimeGapCategory.STALE_REGIME_EVIDENCE.value)
    if _has_missing_core_values(fixture):
        categories.append(MarketRegimeGapCategory.INSUFFICIENT_REGIME_EVIDENCE.value)
    if not input_set.index_evidence.index_id:
        categories.append(MarketRegimeGapCategory.MISSING_INDEX_EVIDENCE.value)
    if not input_set.sector_evidence.sector_universe_id:
        categories.append(MarketRegimeGapCategory.MISSING_SECTOR_EVIDENCE.value)
    if any(_contains_unsafe_pattern(value) for value in input_set.source_trace_references):
        categories.append(MarketRegimeGapCategory.EXECUTABLE_WORDING_DETECTED.value)
    if {"UNSAFE_TRIGGER_ATTEMPT", "ORDER_TRIGGER_ATTEMPT"} & set(input_set.data_quality_flags):
        categories.append(MarketRegimeGapCategory.UNSAFE_TRIGGER_DETECTED.value)
    return sorted(set(categories))


def build_market_regime_evidence_snapshot(
    fixture: MarketRegimeFixture,
) -> MarketRegimeEvidenceSnapshot:
    input_set = fixture.market_regime_input_set
    stale_summary = {
        "core_evidence_stale": any(
            item
            for item in (
                input_set.index_evidence.stale,
                input_set.sector_evidence.stale,
                input_set.breadth_evidence.stale,
                input_set.liquidity_evidence.stale,
                input_set.volatility_evidence.stale,
                input_set.risk_evidence.stale,
            )
        ),
        "top_level_flags": list(input_set.data_quality_flags),
    }
    missing_summary = {
        "missing_core_values": _has_missing_core_values(fixture),
        "sector_distribution_empty": not input_set.sector_evidence.sector_return_distribution,
    }
    return MarketRegimeEvidenceSnapshot(
        snapshot_id=_snapshot_id(fixture),
        fixture_id=fixture.fixture_id,
        strategy_track=input_set.strategy_track,
        market_profile_id=fixture.market_regime_config.market_profile_id,
        observation_window_metadata=input_set.observation_window_metadata,
        index_evidence=input_set.index_evidence,
        sector_evidence=input_set.sector_evidence,
        breadth_evidence=input_set.breadth_evidence,
        liquidity_evidence=input_set.liquidity_evidence,
        volatility_evidence=input_set.volatility_evidence,
        risk_evidence=input_set.risk_evidence,
        data_quality_flags=list(input_set.data_quality_flags),
        stale_evidence_summary=stale_summary,
        missing_evidence_summary=missing_summary,
        source_trace_references=list(input_set.source_trace_references),
    )


def _evidence_strength_bucket(fixture: MarketRegimeFixture) -> MarketRegimeEvidenceStrengthBucket:
    input_set = fixture.market_regime_input_set
    if _has_missing_core_values(fixture):
        return MarketRegimeEvidenceStrengthBucket.EVIDENCE_INSUFFICIENT
    stale_count = sum(
        1
        for value in (
            input_set.index_evidence.stale,
            input_set.sector_evidence.stale,
            input_set.breadth_evidence.stale,
            input_set.liquidity_evidence.stale,
            input_set.volatility_evidence.stale,
            input_set.risk_evidence.stale,
        )
        if value
    )
    if stale_count == 0 and not input_set.data_quality_flags:
        return MarketRegimeEvidenceStrengthBucket.EVIDENCE_STRONG
    if stale_count == 0:
        return MarketRegimeEvidenceStrengthBucket.EVIDENCE_MODERATE
    return MarketRegimeEvidenceStrengthBucket.EVIDENCE_WEAK


def build_market_regime_classification(
    fixture: MarketRegimeFixture,
) -> MarketRegimeClassification:
    categories = _validation_categories(fixture)
    input_set = fixture.market_regime_input_set
    snapshot = build_market_regime_evidence_snapshot(fixture)
    if any(
        category in categories
        for category in (
            MarketRegimeGapCategory.UNSUPPORTED_TRACK.value,
            MarketRegimeGapCategory.MISSING_MARKET_PROFILE.value,
            MarketRegimeGapCategory.EXECUTABLE_WORDING_DETECTED.value,
            MarketRegimeGapCategory.UNSAFE_TRIGGER_DETECTED.value,
        )
    ):
        raise ValueError(f"market regime classification blocked: {', '.join(categories)}")

    if input_set.explicit_report_only and "AUXILIARY_METADATA_STALE" in input_set.data_quality_flags and not any(
        item
        for item in (
            input_set.index_evidence.stale,
            input_set.sector_evidence.stale,
            input_set.breadth_evidence.stale,
            input_set.liquidity_evidence.stale,
            input_set.volatility_evidence.stale,
            input_set.risk_evidence.stale,
        )
    ):
        return MarketRegimeClassification(
            classification_id=_classification_id(fixture),
            evidence_snapshot_id=snapshot.snapshot_id,
            primary_regime_label=MarketRegimeLabel.REGIME_REPORT_ONLY,
            secondary_regime_labels=[],
            evidence_strength_bucket=_evidence_strength_bucket(fixture),
            report_only=True,
            stale_evidence_summary=snapshot.stale_evidence_summary,
            missing_evidence_summary=snapshot.missing_evidence_summary,
            source_trace_references=list(snapshot.source_trace_references),
            integration_context_placeholders=_integration_context_placeholders(snapshot.snapshot_id),
        )

    if _has_missing_core_values(fixture):
        return MarketRegimeClassification(
            classification_id=_classification_id(fixture),
            evidence_snapshot_id=snapshot.snapshot_id,
            primary_regime_label=MarketRegimeLabel.REGIME_INSUFFICIENT_DATA,
            secondary_regime_labels=[],
            evidence_strength_bucket=MarketRegimeEvidenceStrengthBucket.EVIDENCE_INSUFFICIENT,
            stale_evidence_summary=snapshot.stale_evidence_summary,
            missing_evidence_summary=snapshot.missing_evidence_summary,
            source_trace_references=list(snapshot.source_trace_references),
            integration_context_placeholders=_integration_context_placeholders(snapshot.snapshot_id),
        )

    risk_score = input_set.risk_evidence.risk_off_warning_score or 0.0
    stress_count = input_set.risk_evidence.stress_marker_count or 0
    short_return = input_set.index_evidence.short_return_pct or 0.0
    medium_return = input_set.index_evidence.medium_return_pct or 0.0
    breadth = input_set.breadth_evidence.breadth_proxy_pct or 0.0
    volatility_expansion = input_set.volatility_evidence.volatility_expansion_proxy_ratio or 0.0
    turnover = input_set.liquidity_evidence.turnover_proxy_ratio or 0.0
    volume_expansion = input_set.liquidity_evidence.volume_expansion_proxy_ratio or 0.0
    leadership = input_set.sector_evidence.leadership_concentration_pct or 0.0
    rotation = input_set.sector_evidence.rotation_proxy or 0.0
    sector_max_return = max(input_set.sector_evidence.sector_return_distribution.values())

    primary = MarketRegimeLabel.REGIME_CHOPPY_MARKET
    if risk_score >= 0.75 or stress_count >= 3:
        primary = MarketRegimeLabel.REGIME_RISK_OFF
    elif short_return <= -1.0 and medium_return <= -1.5:
        primary = MarketRegimeLabel.REGIME_INDEX_DOWNTREND
    elif rotation >= 0.7 and leadership <= 0.45:
        primary = MarketRegimeLabel.REGIME_SECTOR_ROTATION
    elif breadth <= 0.35:
        primary = MarketRegimeLabel.REGIME_BREADTH_WEAK
    elif volatility_expansion >= 1.4:
        primary = MarketRegimeLabel.REGIME_VOLATILITY_SPIKE
    elif turnover <= 0.55 or volume_expansion <= 0.7:
        primary = MarketRegimeLabel.REGIME_LIQUIDITY_THIN
    elif risk_score <= 0.25 and short_return > 0.8 and medium_return > 1.5 and breadth >= 0.6:
        primary = MarketRegimeLabel.REGIME_RISK_ON

    secondary: list[MarketRegimeLabel] = []
    if short_return > 0.8 and medium_return > 1.5:
        secondary.append(MarketRegimeLabel.REGIME_INDEX_UPTREND)
    if short_return <= -1.0 and medium_return <= -1.5 and primary != MarketRegimeLabel.REGIME_INDEX_DOWNTREND:
        secondary.append(MarketRegimeLabel.REGIME_INDEX_DOWNTREND)
    if leadership >= 0.6 and sector_max_return >= 1.5:
        secondary.append(MarketRegimeLabel.REGIME_SECTOR_MOMENTUM)
    if rotation >= 0.7 and leadership <= 0.45 and primary != MarketRegimeLabel.REGIME_SECTOR_ROTATION:
        secondary.append(MarketRegimeLabel.REGIME_SECTOR_ROTATION)
    if breadth >= 0.6:
        secondary.append(MarketRegimeLabel.REGIME_BREADTH_STRONG)
    if breadth <= 0.35 and primary != MarketRegimeLabel.REGIME_BREADTH_WEAK:
        secondary.append(MarketRegimeLabel.REGIME_BREADTH_WEAK)
    if volatility_expansion >= 1.4 and primary != MarketRegimeLabel.REGIME_VOLATILITY_SPIKE:
        secondary.append(MarketRegimeLabel.REGIME_VOLATILITY_SPIKE)
    if (turnover <= 0.55 or volume_expansion <= 0.7) and primary != MarketRegimeLabel.REGIME_LIQUIDITY_THIN:
        secondary.append(MarketRegimeLabel.REGIME_LIQUIDITY_THIN)
    if risk_score >= 0.75 or stress_count >= 3:
        secondary.append(MarketRegimeLabel.REGIME_RISK_OFF)

    secondary = [label for label in secondary if label != primary]
    deduped_secondary: list[MarketRegimeLabel] = []
    for label in secondary:
        if label not in deduped_secondary:
            deduped_secondary.append(label)

    return MarketRegimeClassification(
        classification_id=_classification_id(fixture),
        evidence_snapshot_id=snapshot.snapshot_id,
        primary_regime_label=primary,
        secondary_regime_labels=deduped_secondary,
        evidence_strength_bucket=_evidence_strength_bucket(fixture),
        stale_evidence_summary=snapshot.stale_evidence_summary,
        missing_evidence_summary=snapshot.missing_evidence_summary,
        source_trace_references=list(snapshot.source_trace_references),
        integration_context_placeholders=_integration_context_placeholders(snapshot.snapshot_id),
    )


def _integration_context_placeholders(snapshot_id: str) -> dict:
    return {
        "candidate_evaluation_context_reference": f"v4.4://{snapshot_id}",
        "replay_window_context_reference": f"v4.5://{snapshot_id}",
        "calibration_context_reference": f"v4.6://{snapshot_id}",
        "paper_shadow_context_reference": f"v4.7://{snapshot_id}",
        "outcome_review_context_reference": f"v4.8://{snapshot_id}",
        "advisory_bundle_context_reference": f"v4.9://{snapshot_id}",
        "distillation_feature_context_reference": f"v4.10://{snapshot_id}",
    }


def build_market_regime_context_reference(
    fixture: MarketRegimeFixture,
) -> RegimeAwareContextReference:
    classification = build_market_regime_classification(fixture)
    snapshot = build_market_regime_evidence_snapshot(fixture)
    return RegimeAwareContextReference(
        context_reference_id=f"{fixture.fixture_id}-regime-context-reference",
        source_report_id=_report_id(fixture),
        source_evidence_snapshot_id=snapshot.snapshot_id,
        evidence_category_references={
            "index": snapshot.index_evidence.index_id,
            "sector": snapshot.sector_evidence.sector_universe_id,
            "breadth": snapshot.observation_window_metadata.window_id,
            "liquidity": snapshot.observation_window_metadata.window_id,
            "volatility": snapshot.observation_window_metadata.window_id,
            "risk": snapshot.observation_window_metadata.window_id,
        },
        strategy_track=snapshot.strategy_track,
        market_profile_id=snapshot.market_profile_id,
        primary_regime_label=classification.primary_regime_label,
        secondary_regime_labels=classification.secondary_regime_labels,
        report_only=classification.report_only,
        stale=bool(snapshot.stale_evidence_summary.get("core_evidence_stale")),
        missing_evidence=bool(snapshot.missing_evidence_summary.get("missing_core_values")),
    )


def build_market_regime_report(
    fixture: MarketRegimeFixture,
) -> MarketRegimeReport:
    classification = build_market_regime_classification(fixture)
    snapshot = build_market_regime_evidence_snapshot(fixture)
    return MarketRegimeReport(
        report_id=_report_id(fixture),
        fixture_id=fixture.fixture_id,
        strategy_track=fixture.market_regime_input_set.strategy_track,
        market_profile_id=fixture.market_regime_config.market_profile_id,
        evidence_snapshot_id=snapshot.snapshot_id,
        primary_regime_label=classification.primary_regime_label,
        secondary_regime_labels=classification.secondary_regime_labels,
        evidence_strength_bucket=classification.evidence_strength_bucket,
        data_quality_flags=list(snapshot.data_quality_flags),
        blocked_reasons=classification.blocked_reasons,
        missing_evidence_summary=snapshot.missing_evidence_summary,
        stale_evidence_summary=snapshot.stale_evidence_summary,
        report_only=classification.report_only,
        source_trace_references=list(snapshot.source_trace_references),
        integration_context_placeholders=classification.integration_context_placeholders,
        context_reference=build_market_regime_context_reference(fixture),
        metadata_json=dict(DOMESTIC_MARKET_REGIME_METADATA),
    )


def build_market_regime_gap_report(
    fixture: MarketRegimeFixture,
) -> MarketRegimeGapReport:
    categories = _validation_categories(fixture)
    return MarketRegimeGapReport(
        report_id=f"{fixture.fixture_id}-market-regime-gap-report",
        fixture_id=fixture.fixture_id,
        strategy_track=fixture.market_regime_input_set.strategy_track,
        market_profile_id=fixture.market_regime_config.market_profile_id,
        gap_categories=categories,
        missing_critical_evidence_count=sum(
            category
            in {
                MarketRegimeGapCategory.MISSING_MARKET_PROFILE.value,
                MarketRegimeGapCategory.MISSING_INDEX_EVIDENCE.value,
                MarketRegimeGapCategory.MISSING_SECTOR_EVIDENCE.value,
                MarketRegimeGapCategory.MISSING_BREADTH_EVIDENCE.value,
                MarketRegimeGapCategory.MISSING_LIQUIDITY_EVIDENCE.value,
                MarketRegimeGapCategory.MISSING_VOLATILITY_EVIDENCE.value,
                MarketRegimeGapCategory.INSUFFICIENT_REGIME_EVIDENCE.value,
            }
            for category in categories
        ),
        stale_evidence_count=sum(category == MarketRegimeGapCategory.STALE_REGIME_EVIDENCE.value for category in categories),
        wording_violation_count=sum(category == MarketRegimeGapCategory.EXECUTABLE_WORDING_DETECTED.value for category in categories),
        unsupported_track_count=sum(category == MarketRegimeGapCategory.UNSUPPORTED_TRACK.value for category in categories),
        metadata_json=dict(DOMESTIC_MARKET_REGIME_METADATA),
    )


def build_market_regime_safety_report(
    fixture: MarketRegimeFixture,
) -> MarketRegimeSafetyReport:
    return MarketRegimeSafetyReport(
        report_id=f"{fixture.fixture_id}-market-regime-safety-report",
        strategy_track=fixture.market_regime_input_set.strategy_track,
        safety_boundary=MarketRegimeSafetyBoundary(
            signal_generation_allowed=fixture.market_regime_config.signal_generation_allowed,
            cloud_llm_allowed=fixture.market_regime_config.cloud_llm_called,
            model_runtime_allowed=fixture.market_regime_config.model_runtime_called,
            live_or_prod_allowed=False,
        ),
        metadata_json=dict(DOMESTIC_MARKET_REGIME_METADATA),
    )
