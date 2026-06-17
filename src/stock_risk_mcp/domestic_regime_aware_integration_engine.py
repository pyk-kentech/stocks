from __future__ import annotations

from stock_risk_mcp.domestic_regime_aware_integration_models import (
    DOMESTIC_REGIME_AWARE_INTEGRATION_METADATA,
    UNSAFE_EXECUTION_PATTERNS,
    DomesticRegimeAwareIntegrationFixture,
    RegimeAwareContextReference,
    RegimeAwareGapCategory,
    RegimeAwareGapReport,
    RegimeAwareIntegrationReport,
    RegimeAwareSafetyBoundary,
    RegimeAwareSafetyReport,
)
from stock_risk_mcp.domestic_market_regime_models import (
    MarketRegimeEvidenceStrengthBucket,
    MarketRegimeLabel,
)


def _integration_report_id(fixture: DomesticRegimeAwareIntegrationFixture) -> str:
    return f"{fixture.fixture_id}-regime-aware-integration-report"


def _gap_report_id(fixture: DomesticRegimeAwareIntegrationFixture) -> str:
    return f"{fixture.fixture_id}-regime-aware-gap-report"


def _safety_report_id(fixture: DomesticRegimeAwareIntegrationFixture) -> str:
    return f"{fixture.fixture_id}-regime-aware-safety-report"


def _contains_unsafe_pattern(value: str) -> bool:
    upper_value = value.upper()
    return any(pattern in upper_value for pattern in UNSAFE_EXECUTION_PATTERNS)


def _subcontexts(fixture: DomesticRegimeAwareIntegrationFixture):
    input_set = fixture.regime_aware_input_set
    return (
        input_set.candidate_evaluation_context,
        input_set.replay_context,
        input_set.calibration_context,
        input_set.paper_shadow_context,
        input_set.outcome_review_context,
        input_set.advisory_context,
        input_set.distillation_context,
    )


def _validation_categories(fixture: DomesticRegimeAwareIntegrationFixture) -> list[str]:
    config = fixture.regime_aware_integration_config
    input_set = fixture.regime_aware_input_set
    categories: list[str] = []
    if input_set.strategy_track != config.strategy_track:
        categories.append(RegimeAwareGapCategory.UNSUPPORTED_TRACK.value)
    if str(input_set.market_profile_summary.get("market_id", "")).upper() != "KRX":
        categories.append(RegimeAwareGapCategory.REGIME_CONTEXT_MARKET_PROFILE_MISMATCH.value)
    if input_set.market_regime_report is None:
        categories.append(RegimeAwareGapCategory.MISSING_MARKET_REGIME_REPORT.value)
    if input_set.market_regime_classification is None:
        categories.append(RegimeAwareGapCategory.MISSING_REGIME_CLASSIFICATION.value)
    if input_set.primary_regime_label is None:
        categories.append(RegimeAwareGapCategory.MISSING_PRIMARY_REGIME_LABEL.value)
    if input_set.market_regime_report is not None:
        if input_set.market_regime_report.strategy_track != input_set.strategy_track:
            categories.append(RegimeAwareGapCategory.REGIME_CONTEXT_TRACK_MISMATCH.value)
        if input_set.market_regime_report.market_profile_id != config.market_profile_id:
            categories.append(RegimeAwareGapCategory.REGIME_CONTEXT_MARKET_PROFILE_MISMATCH.value)
        if input_set.market_regime_report.stale_evidence_summary.get("core_evidence_stale"):
            categories.append(RegimeAwareGapCategory.STALE_REGIME_CONTEXT.value)
        if input_set.market_regime_report.report_only:
            categories.append(RegimeAwareGapCategory.REPORT_ONLY_REGIME_CONTEXT.value)
    if any(not section.has_regime_attachment for section in _subcontexts(fixture)):
        categories.append(RegimeAwareGapCategory.INSUFFICIENT_REGIME_COVERAGE.value)
    if any(_contains_unsafe_pattern(value) for value in input_set.source_trace_references):
        categories.append(RegimeAwareGapCategory.EXECUTABLE_WORDING_DETECTED.value)
    if {"UNSAFE_TRIGGER_ATTEMPT", "ORDER_TRIGGER_ATTEMPT"} & set(input_set.data_quality_flags):
        categories.append(RegimeAwareGapCategory.UNSAFE_TRIGGER_DETECTED.value)
    return sorted(set(categories))


def _require_normal_mode_readiness(fixture: DomesticRegimeAwareIntegrationFixture, categories: list[str]) -> None:
    report_only_mode = fixture.regime_aware_integration_config.report_only_integration_mode
    if RegimeAwareGapCategory.MISSING_MARKET_REGIME_REPORT.value in categories and not report_only_mode:
        raise ValueError(RegimeAwareGapCategory.MISSING_MARKET_REGIME_REPORT.value)
    if RegimeAwareGapCategory.STALE_REGIME_CONTEXT.value in categories and not report_only_mode:
        raise ValueError(RegimeAwareGapCategory.STALE_REGIME_CONTEXT.value)
    fatal = {
        RegimeAwareGapCategory.UNSUPPORTED_TRACK.value,
        RegimeAwareGapCategory.REGIME_CONTEXT_TRACK_MISMATCH.value,
        RegimeAwareGapCategory.REGIME_CONTEXT_MARKET_PROFILE_MISMATCH.value,
        RegimeAwareGapCategory.EXECUTABLE_WORDING_DETECTED.value,
        RegimeAwareGapCategory.UNSAFE_TRIGGER_DETECTED.value,
        RegimeAwareGapCategory.MISSING_PRIMARY_REGIME_LABEL.value,
    }
    matched = [category for category in categories if category in fatal]
    if matched:
        raise ValueError(", ".join(matched))


def _report_only_output(fixture: DomesticRegimeAwareIntegrationFixture, categories: list[str]) -> bool:
    report_only_mode = fixture.regime_aware_integration_config.report_only_integration_mode
    return report_only_mode and any(
        category in categories
        for category in (
            RegimeAwareGapCategory.MISSING_MARKET_REGIME_REPORT.value,
            RegimeAwareGapCategory.STALE_REGIME_CONTEXT.value,
            RegimeAwareGapCategory.REPORT_ONLY_REGIME_CONTEXT.value,
        )
    )


def _context_reference(fixture: DomesticRegimeAwareIntegrationFixture, report_only: bool) -> RegimeAwareContextReference:
    input_set = fixture.regime_aware_input_set
    return RegimeAwareContextReference(
        context_reference_id=f"{fixture.fixture_id}-regime-aware-context-reference",
        source_market_regime_report_id=input_set.market_regime_report.report_id if input_set.market_regime_report else None,
        source_market_regime_classification_id=(
            input_set.market_regime_classification.classification_id if input_set.market_regime_classification else None
        ),
        primary_regime_label=input_set.primary_regime_label,
        secondary_regime_labels=input_set.secondary_regime_labels,
        evidence_strength_bucket=input_set.evidence_strength_bucket,
        data_quality_flags=input_set.data_quality_flags,
        stale_evidence_summary=input_set.stale_evidence_summary,
        missing_evidence_summary=input_set.missing_evidence_summary,
        report_only=report_only,
        strategy_track=input_set.strategy_track,
        market_profile_id=fixture.regime_aware_integration_config.market_profile_id,
        source_trace_references=input_set.source_trace_references,
    )


def _candidate_context(fixture: DomesticRegimeAwareIntegrationFixture, report_only: bool):
    section = fixture.regime_aware_input_set.candidate_evaluation_context.model_copy(deep=True)
    section.primary_regime_label = fixture.regime_aware_input_set.primary_regime_label
    section.secondary_regime_labels = fixture.regime_aware_input_set.secondary_regime_labels
    section.evidence_strength_bucket = fixture.regime_aware_input_set.evidence_strength_bucket
    section.data_quality_flags = fixture.regime_aware_input_set.data_quality_flags
    section.report_only = report_only
    return section


def _replay_context(fixture: DomesticRegimeAwareIntegrationFixture, report_only: bool):
    section = fixture.regime_aware_input_set.replay_context.model_copy(deep=True)
    section.regime_report_id = (
        fixture.regime_aware_input_set.market_regime_report.report_id
        if fixture.regime_aware_input_set.market_regime_report
        else None
    )
    section.primary_regime_label = fixture.regime_aware_input_set.primary_regime_label
    section.secondary_regime_labels = fixture.regime_aware_input_set.secondary_regime_labels
    section.evidence_strength_bucket = fixture.regime_aware_input_set.evidence_strength_bucket
    section.stale_regime_context = bool(fixture.regime_aware_input_set.stale_evidence_summary.get("core_evidence_stale"))
    section.report_only = report_only
    return section


def build_domestic_regime_aware_gap_report(
    fixture: DomesticRegimeAwareIntegrationFixture,
) -> RegimeAwareGapReport:
    categories = _validation_categories(fixture)
    return RegimeAwareGapReport(
        report_id=_gap_report_id(fixture),
        fixture_id=fixture.fixture_id,
        strategy_track=fixture.regime_aware_input_set.strategy_track,
        market_profile_id=fixture.regime_aware_integration_config.market_profile_id,
        gap_categories=categories,
        missing_regime_context_count=sum(
            category
            in {
                RegimeAwareGapCategory.MISSING_MARKET_REGIME_REPORT.value,
                RegimeAwareGapCategory.MISSING_REGIME_CLASSIFICATION.value,
                RegimeAwareGapCategory.MISSING_PRIMARY_REGIME_LABEL.value,
            }
            for category in categories
        ),
        stale_regime_context_count=sum(category == RegimeAwareGapCategory.STALE_REGIME_CONTEXT.value for category in categories),
        coverage_failure_count=sum(category == RegimeAwareGapCategory.INSUFFICIENT_REGIME_COVERAGE.value for category in categories),
        wording_violation_count=sum(category == RegimeAwareGapCategory.EXECUTABLE_WORDING_DETECTED.value for category in categories),
        unsupported_track_count=sum(category == RegimeAwareGapCategory.UNSUPPORTED_TRACK.value for category in categories),
        metadata_json=dict(DOMESTIC_REGIME_AWARE_INTEGRATION_METADATA),
    )


def build_domestic_regime_aware_safety_report(
    fixture: DomesticRegimeAwareIntegrationFixture,
) -> RegimeAwareSafetyReport:
    return RegimeAwareSafetyReport(
        report_id=_safety_report_id(fixture),
        strategy_track=fixture.regime_aware_input_set.strategy_track,
        safety_boundary=RegimeAwareSafetyBoundary(
            cloud_llm_allowed=fixture.regime_aware_integration_config.cloud_llm_called,
            model_runtime_allowed=fixture.regime_aware_integration_config.model_runtime_called,
            ml_training_allowed=fixture.regime_aware_integration_config.ml_training_run,
            live_or_prod_allowed=False,
        ),
        metadata_json=dict(DOMESTIC_REGIME_AWARE_INTEGRATION_METADATA),
    )


def build_domestic_regime_aware_integration_report(
    fixture: DomesticRegimeAwareIntegrationFixture,
) -> RegimeAwareIntegrationReport:
    categories = _validation_categories(fixture)
    _require_normal_mode_readiness(fixture, categories)
    report_only = _report_only_output(fixture, categories)
    input_set = fixture.regime_aware_input_set
    return RegimeAwareIntegrationReport(
        integration_report_id=_integration_report_id(fixture),
        fixture_id=fixture.fixture_id,
        strategy_track=input_set.strategy_track,
        market_profile_id=fixture.regime_aware_integration_config.market_profile_id,
        source_market_regime_report_id=input_set.market_regime_report.report_id if input_set.market_regime_report else None,
        source_market_regime_classification_id=(
            input_set.market_regime_classification.classification_id if input_set.market_regime_classification else None
        ),
        primary_regime_label=input_set.primary_regime_label,
        secondary_regime_labels=input_set.secondary_regime_labels,
        evidence_strength_bucket=input_set.evidence_strength_bucket,
        data_quality_flags=input_set.data_quality_flags,
        report_only=report_only,
        candidate_evaluation_context=_candidate_context(fixture, report_only),
        replay_context=_replay_context(fixture, report_only),
        calibration_context=fixture.regime_aware_input_set.calibration_context,
        paper_shadow_context=fixture.regime_aware_input_set.paper_shadow_context,
        outcome_review_context=fixture.regime_aware_input_set.outcome_review_context,
        advisory_context=fixture.regime_aware_input_set.advisory_context,
        distillation_context=fixture.regime_aware_input_set.distillation_context,
        gap_report_id=_gap_report_id(fixture),
        safety_report_id=_safety_report_id(fixture),
        source_trace_references=input_set.source_trace_references,
        context_reference=_context_reference(fixture, report_only),
        metadata_json=dict(DOMESTIC_REGIME_AWARE_INTEGRATION_METADATA),
    )
