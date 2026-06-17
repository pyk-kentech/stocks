from __future__ import annotations

from collections import Counter

from stock_risk_mcp.domestic_shadow_advisory_context_models import (
    DOMESTIC_SHADOW_ADVISORY_CONTEXT_METADATA,
    SAFE_ADVISORY_TASK_NAMES,
    UNSAFE_EVIDENCE_ITEM_TYPES,
    UNSAFE_EXECUTION_PATTERNS,
    AdvisoryContextEvidenceItem,
    AdvisoryContextEvidenceItemType,
    AdvisoryContextGapCategory,
    AdvisoryContextGapReport,
    AdvisoryContextRiskSummary,
    AdvisoryContextSafetyBoundary,
    AdvisoryContextSafetyReport,
    AdvisoryContextValidationReport,
    DomesticShadowAdvisoryContextFixture,
    ShadowReviewAdvisoryContextBundle,
)
from stock_risk_mcp.domestic_paper_shadow_models import PaperShadowDecisionType


def _contains_executable_wording(text: str, forbidden_patterns: list[str]) -> bool:
    upper_text = text.upper()
    return any(pattern in upper_text for pattern in forbidden_patterns)


def _summary_text_cap(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."


def _bundle_id(fixture: DomesticShadowAdvisoryContextFixture) -> str:
    return f"{fixture.run_id}-advisory-context-bundle"


def _validation_categories(fixture: DomesticShadowAdvisoryContextFixture) -> list[str]:
    categories: list[str] = []
    input_set = fixture.shadow_review_advisory_input_set
    config = fixture.shadow_review_advisory_context_config
    policy = fixture.advisory_context_policy
    if len(input_set.scenario_family_coverage) < policy.minimum_scenario_coverage_count:
        categories.append(AdvisoryContextGapCategory.INSUFFICIENT_SCENARIO_COVERAGE.value)
    if len(input_set.symbol_coverage) < policy.minimum_symbol_coverage_count:
        categories.append(AdvisoryContextGapCategory.INSUFFICIENT_SYMBOL_COVERAGE.value)
    if len(input_set.observation_window_coverage) < policy.minimum_observation_window_coverage_count:
        categories.append(AdvisoryContextGapCategory.INSUFFICIENT_OBSERVATION_WINDOW_COVERAGE.value)
    if any(task not in SAFE_ADVISORY_TASK_NAMES for task in input_set.supported_advisory_task_names):
        categories.append(AdvisoryContextGapCategory.ADVISORY_TASK_UNSUPPORTED.value)
    if any(item in UNSAFE_EVIDENCE_ITEM_TYPES for item in policy.allowed_evidence_item_types):
        categories.append(AdvisoryContextGapCategory.UNSAFE_EVIDENCE_ITEM_TYPE.value)
    if not config.training_only_context:
        categories.append(AdvisoryContextGapCategory.MISSING_TRAINING_ONLY_MARKER.value)
    if config.llm_runtime_allowed or config.cloud_llm_called or config.local_model_runtime_called:
        categories.append(AdvisoryContextGapCategory.LLM_RUNTIME_NOT_ALLOWED.value)
    source_texts = list(input_set.advisory_context_markers) + list(input_set.data_quality_flags)
    if any(_contains_executable_wording(text, policy.forbidden_wording_patterns) for text in source_texts):
        categories.append(AdvisoryContextGapCategory.EXECUTABLE_WORDING_DETECTED.value)
    return sorted(set(categories))


def _short_section(section_key: str, summary_text: str, structured_counts: dict, trace_references: list[str]):
    return {
        "section_key": section_key,
        "summary_text": summary_text,
        "structured_counts": structured_counts,
        "trace_references": trace_references,
    }


def build_domestic_shadow_advisory_context_bundle(
    fixture: DomesticShadowAdvisoryContextFixture,
) -> ShadowReviewAdvisoryContextBundle:
    categories = _validation_categories(fixture)
    if categories:
        raise ValueError(f"advisory context build blocked: {', '.join(categories)}")
    input_set = fixture.shadow_review_advisory_input_set
    config = fixture.shadow_review_advisory_context_config
    policy = fixture.advisory_context_policy
    outcome_review = input_set.outcome_review_report
    journal = input_set.paper_shadow_journal
    max_length = policy.deterministic_summary_length_cap

    blocked_counter = Counter()
    report_only_counter = Counter()
    non_actionable_counter = Counter()
    for entry in journal.entries:
        blocked_counter.update(entry.blocked_reasons)
        report_only_counter.update(entry.report_only_reasons)
        non_actionable_counter.update(entry.non_actionable_reasons)

    review_summary_text = _summary_text_cap(
        (
            f"Outcome review contains {outcome_review.total_outcome_labels} shadow-watch entries: "
            f"{outcome_review.favorable_count} favorable, {outcome_review.adverse_count} adverse, "
            f"{outcome_review.neutral_count} neutral, and {outcome_review.inconclusive_count} inconclusive."
        ),
        max_length,
    )
    review_level_summary = {
        "summary_text": review_summary_text,
        "total_outcome_labels": outcome_review.total_outcome_labels,
        "source_ids": [outcome_review.review_report_id, journal.journal_id],
    }
    scenario_family_sub_summaries = [
        _short_section(
            scenario,
            _summary_text_cap(f"Scenario family {scenario} contributed {count} reviewed outcomes.", max_length),
            {"count": count},
            [outcome_review.review_report_id],
        )
        for scenario, count in sorted(outcome_review.scenario_family_counts.items())
    ]
    replay_window_sub_summaries = [
        _short_section(
            window,
            _summary_text_cap(f"Replay window {window} contributed {count} reviewed outcomes.", max_length),
            {"count": count},
            [outcome_review.review_report_id],
        )
        for window, count in sorted(outcome_review.replay_window_counts.items())
    ]
    observation_horizon_sub_summaries = [
        _short_section(
            horizon,
            _summary_text_cap(f"Observation horizon {horizon} covered {count} reviewed outcomes.", max_length),
            {"count": count},
            [outcome_review.review_report_id],
        )
        for horizon, count in sorted(outcome_review.observation_horizon_counts.items())
    ]
    symbol_coverage_summary = {
        "summary_text": _summary_text_cap(
            f"Symbol coverage spans {len(outcome_review.symbol_counts)} symbols in the review report.",
            max_length,
        ),
        "symbol_counts": outcome_review.symbol_counts,
    }
    outcome_label_summary = {
        "summary_text": review_summary_text,
        "outcome_label_counts": outcome_review.outcome_label_counts,
    }
    blocked_summary = {
        "summary_text": _summary_text_cap(
            "Most blocked entries were caused by profitability and technical-evidence constraints."
            if blocked_counter
            else "No blocked entries were present in the advisory context bundle.",
            max_length,
        ),
        "blocked_reason_counts": dict(blocked_counter),
        "report_only_reason_counts": dict(report_only_counter),
        "non_actionable_reason_counts": dict(non_actionable_counter),
    }
    data_quality_summary = {
        "summary_text": _summary_text_cap(
            (
                f"Data quality flags present: {', '.join(input_set.data_quality_flags)}."
                if input_set.data_quality_flags
                else "No source data quality flags were present."
            ),
            max_length,
        ),
        "data_quality_flags": input_set.data_quality_flags,
        "advisory_context_markers": input_set.advisory_context_markers,
    }
    gap_summary = {
        "summary_text": _summary_text_cap("No advisory-context gaps were detected.", max_length),
        "gap_categories": [],
    }
    risk_summary = AdvisoryContextRiskSummary(
        safety_rejected_count=outcome_review.safety_rejected_count,
        blocked_confirmed_count=outcome_review.blocked_confirmed_count,
        report_only_count=outcome_review.report_only_count,
        non_actionable_count=sum(1 for entry in journal.entries if entry.non_actionable),
        data_quality_flags=list(input_set.data_quality_flags),
        summary_text=_summary_text_cap(
            f"Risk summary preserves {outcome_review.safety_rejected_count} safety rejections and {outcome_review.blocked_confirmed_count} blocked confirmations.",
            max_length,
        ),
    )
    evidence_items = [
        AdvisoryContextEvidenceItem(
            evidence_item_id=f"{fixture.run_id}-evidence-1",
            evidence_type=AdvisoryContextEvidenceItemType.SHADOW_DECISION_SUMMARY,
            summary_text=_summary_text_cap(
                f"Paper-shadow journal preserved {journal.entry_count} non-executable decisions.",
                max_length,
            ),
            structured_counts={"entry_count": journal.entry_count},
            source_ids=[journal.journal_id],
            trace_references=[*journal.source_candidate_evaluation_report_ids],
        ),
        AdvisoryContextEvidenceItem(
            evidence_item_id=f"{fixture.run_id}-evidence-2",
            evidence_type=AdvisoryContextEvidenceItemType.OUTCOME_LABEL_SUMMARY,
            summary_text=review_summary_text,
            structured_counts=outcome_review.outcome_label_counts,
            source_ids=[outcome_review.review_report_id],
            trace_references=[journal.journal_id],
        ),
        AdvisoryContextEvidenceItem(
            evidence_item_id=f"{fixture.run_id}-evidence-3",
            evidence_type=AdvisoryContextEvidenceItemType.BLOCKED_REASON_SUMMARY,
            summary_text=blocked_summary["summary_text"],
            structured_counts=dict(blocked_counter),
            source_ids=[journal.journal_id],
            trace_references=[outcome_review.review_report_id],
        ),
        AdvisoryContextEvidenceItem(
            evidence_item_id=f"{fixture.run_id}-evidence-4",
            evidence_type=AdvisoryContextEvidenceItemType.TRAINING_CONTEXT_SUMMARY,
            summary_text=_summary_text_cap("This bundle is non-executable advisory context only.", max_length),
            structured_counts={"training_only_context": 1, "distillation_eligible": 1},
            source_ids=[journal.journal_id, outcome_review.review_report_id],
            trace_references=[input_set.calibration_pack_reference],
        ),
    ]
    return ShadowReviewAdvisoryContextBundle(
        bundle_id=_bundle_id(fixture),
        fixture_id=fixture.run_id,
        source_outcome_review_report_id=outcome_review.review_report_id,
        source_paper_shadow_journal_id=journal.journal_id,
        source_promotion_gate_id=input_set.source_promotion_gate_id,
        strategy_track=config.strategy_track,
        market_profile_id=config.market_profile_id,
        supported_advisory_task_names=list(input_set.supported_advisory_task_names),
        supported_tracks=[track.value for track in config.supported_tracks],
        review_level_summary=review_level_summary,
        scenario_family_sub_summaries=scenario_family_sub_summaries,
        replay_window_sub_summaries=replay_window_sub_summaries,
        observation_horizon_sub_summaries=observation_horizon_sub_summaries,
        symbol_coverage_summary=symbol_coverage_summary,
        outcome_label_summary=outcome_label_summary,
        blocked_report_only_non_actionable_summary=blocked_summary,
        risk_summary=risk_summary,
        data_quality_summary=data_quality_summary,
        gap_summary=gap_summary,
        evidence_items=evidence_items,
        distillation_eligible=config.distillation_eligible,
        training_only_context=config.training_only_context,
        llm_training_context_allowed=config.llm_training_context_allowed,
        llm_runtime_allowed=config.llm_runtime_allowed,
        cloud_llm_called=config.cloud_llm_called,
        local_model_runtime_called=config.local_model_runtime_called,
        non_executable=config.non_executable,
        no_trade_instruction=config.no_trade_instruction,
        metadata_json=dict(DOMESTIC_SHADOW_ADVISORY_CONTEXT_METADATA),
    )


def build_domestic_shadow_advisory_context_validation_report(
    fixture: DomesticShadowAdvisoryContextFixture,
) -> AdvisoryContextValidationReport:
    categories = _validation_categories(fixture)
    coverage_failures = {
        AdvisoryContextGapCategory.INSUFFICIENT_SCENARIO_COVERAGE.value,
        AdvisoryContextGapCategory.INSUFFICIENT_SYMBOL_COVERAGE.value,
        AdvisoryContextGapCategory.INSUFFICIENT_OBSERVATION_WINDOW_COVERAGE.value,
    }
    return AdvisoryContextValidationReport(
        report_id=f"{fixture.run_id}-advisory-context-validation",
        bundle_reference=_bundle_id(fixture),
        valid=not categories,
        strategy_track=fixture.shadow_review_advisory_context_config.strategy_track,
        market_profile_id=fixture.shadow_review_advisory_context_config.market_profile_id,
        training_only_metadata_present=fixture.shadow_review_advisory_context_config.training_only_context,
        coverage_sufficient=not any(item in coverage_failures for item in categories),
        block_reasons=categories,
        warnings=[],
        metadata_json=dict(DOMESTIC_SHADOW_ADVISORY_CONTEXT_METADATA),
    )


def build_domestic_shadow_advisory_context_gap_report(
    fixture: DomesticShadowAdvisoryContextFixture,
) -> AdvisoryContextGapReport:
    categories = _validation_categories(fixture)
    return AdvisoryContextGapReport(
        report_id=f"{fixture.run_id}-advisory-context-gap",
        bundle_reference=_bundle_id(fixture),
        gap_categories=categories,
        missing_source_count=sum(
            1
            for item in categories
            if item
            in {
                AdvisoryContextGapCategory.MISSING_JOURNAL.value,
                AdvisoryContextGapCategory.MISSING_OUTCOME_REVIEW.value,
                AdvisoryContextGapCategory.MISSING_PROMOTION_GATE.value,
                AdvisoryContextGapCategory.MISSING_MARKET_PROFILE.value,
            }
        ),
        insufficient_coverage_count=sum(
            1
            for item in categories
            if item
            in {
                AdvisoryContextGapCategory.INSUFFICIENT_SCENARIO_COVERAGE.value,
                AdvisoryContextGapCategory.INSUFFICIENT_SYMBOL_COVERAGE.value,
                AdvisoryContextGapCategory.INSUFFICIENT_OBSERVATION_WINDOW_COVERAGE.value,
            }
        ),
        wording_violation_count=sum(
            1
            for item in categories
            if item == AdvisoryContextGapCategory.EXECUTABLE_WORDING_DETECTED.value
        ),
        unsupported_task_count=sum(
            1
            for item in categories
            if item == AdvisoryContextGapCategory.ADVISORY_TASK_UNSUPPORTED.value
        ),
        metadata_json=dict(DOMESTIC_SHADOW_ADVISORY_CONTEXT_METADATA),
    )


def build_domestic_shadow_advisory_context_safety_report(
    fixture: DomesticShadowAdvisoryContextFixture,
) -> AdvisoryContextSafetyReport:
    categories = _validation_categories(fixture)
    return AdvisoryContextSafetyReport(
        report_id=f"{fixture.run_id}-advisory-context-safety",
        strategy_track=fixture.shadow_review_advisory_context_config.strategy_track,
        safety_boundary=AdvisoryContextSafetyBoundary(
            llm_runtime_allowed=fixture.shadow_review_advisory_context_config.llm_runtime_allowed,
            local_model_runtime_called=fixture.shadow_review_advisory_context_config.local_model_runtime_called,
        ),
        warnings=[],
        block_reasons=categories,
        metadata_json=dict(DOMESTIC_SHADOW_ADVISORY_CONTEXT_METADATA),
    )
