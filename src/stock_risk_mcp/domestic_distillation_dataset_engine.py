from __future__ import annotations

from collections import Counter

from stock_risk_mcp.domestic_distillation_dataset_models import (
    DOMESTIC_DISTILLATION_DATASET_METADATA,
    UNSAFE_DATASET_LABELS,
    UNSAFE_EXECUTION_PATTERNS,
    DistillationDatasetAuxiliaryLabel,
    DistillationDatasetGapCategory,
    DistillationDatasetGapReport,
    DistillationDatasetPack,
    DistillationDatasetPrimaryLabel,
    DistillationDatasetRecord,
    DistillationDatasetRecordType,
    DistillationDatasetSafetyBoundary,
    DistillationDatasetSafetyReport,
    DistillationDatasetValidationReport,
    DistillationFeatureSet,
    DistillationLabelSet,
    DomesticDistillationDatasetFixture,
)


def _pack_id(fixture: DomesticDistillationDatasetFixture) -> str:
    return f"{fixture.run_id}-distillation-pack"


def _contains_unsafe_pattern(value: str, patterns: list[str]) -> bool:
    upper_value = value.upper()
    return any(pattern in upper_value for pattern in patterns)


def _validation_categories(fixture: DomesticDistillationDatasetFixture) -> list[str]:
    categories: list[str] = []
    config = fixture.training_only_distillation_config
    input_set = fixture.training_only_distillation_input_set
    policy = fixture.training_only_distillation_policy
    if len(input_set.scenario_family_coverage) < policy.minimum_scenario_coverage_count:
        categories.append(DistillationDatasetGapCategory.INSUFFICIENT_SCENARIO_COVERAGE.value)
    if len(input_set.symbol_coverage) < policy.minimum_symbol_coverage_count:
        categories.append(DistillationDatasetGapCategory.INSUFFICIENT_SYMBOL_COVERAGE.value)
    if len(input_set.observation_horizon_coverage) < policy.minimum_observation_horizon_coverage_count:
        categories.append(DistillationDatasetGapCategory.INSUFFICIENT_OBSERVATION_HORIZON_COVERAGE.value)
    if not config.training_only or not input_set.training_only:
        categories.append(DistillationDatasetGapCategory.MISSING_TRAINING_ONLY_MARKER.value)
    if not config.non_executable or not input_set.non_executable:
        categories.append(DistillationDatasetGapCategory.MISSING_NON_EXECUTABLE_MARKER.value)
    if not policy.allowed_primary_labels:
        categories.append(DistillationDatasetGapCategory.MISSING_PRIMARY_LABEL.value)
    if any(label in UNSAFE_DATASET_LABELS for label in policy.allowed_primary_labels):
        categories.append(DistillationDatasetGapCategory.UNSAFE_LABEL_DETECTED.value)
    if any(label in UNSAFE_DATASET_LABELS for label in policy.allowed_auxiliary_labels):
        categories.append(DistillationDatasetGapCategory.UNSAFE_AUXILIARY_LABEL_DETECTED.value)
    if input_set.prompt_stub_execution_requested or any(stub.executed for stub in input_set.prompt_stubs):
        categories.append(DistillationDatasetGapCategory.PROMPT_EXECUTION_NOT_ALLOWED.value)
    if config.runtime_decision_allowed or input_set.runtime_decision_requested:
        categories.append(DistillationDatasetGapCategory.ORDER_ARTIFACT_DETECTED.value)
    if config.llm_runtime_allowed or config.cloud_llm_called:
        categories.append(DistillationDatasetGapCategory.LLM_RUNTIME_NOT_ALLOWED.value)
    if config.local_model_runtime_called:
        categories.append(DistillationDatasetGapCategory.LOCAL_MODEL_RUNTIME_NOT_ALLOWED.value)
    if "FAIL_CLOSED" not in policy.leakage_policy_markers:
        categories.append(DistillationDatasetGapCategory.POTENTIAL_LEAKAGE_DETECTED.value)
    source_texts = []
    source_texts.extend(str(stub.prompt_text) for stub in input_set.prompt_stubs)
    source_texts.extend(str(value) for value in input_set.supported_advisory_task_names)
    if any(_contains_unsafe_pattern(text, policy.forbidden_label_patterns) for text in source_texts):
        categories.append(DistillationDatasetGapCategory.EXECUTABLE_WORDING_DETECTED.value)
    return sorted(set(categories))


def _blocked_counts(bundle) -> dict:
    return dict(bundle.blocked_report_only_non_actionable_summary.get("blocked_reason_counts", {}))


def _report_only_counts(bundle) -> dict:
    return dict(bundle.blocked_report_only_non_actionable_summary.get("report_only_reason_counts", {}))


def _non_actionable_counts(bundle) -> dict:
    return dict(bundle.blocked_report_only_non_actionable_summary.get("non_actionable_reason_counts", {}))


def _primary_label_for_bundle(bundle) -> DistillationDatasetPrimaryLabel:
    outcome_counts = dict(bundle.outcome_label_summary.get("outcome_label_counts", {}))
    blocked_counts = _blocked_counts(bundle)
    if any("SAFETY" in key.upper() for key in blocked_counts):
        return DistillationDatasetPrimaryLabel.LABEL_BLOCKED_SAFETY_CONTEXT
    if any("PROFIT" in key.upper() for key in blocked_counts):
        return DistillationDatasetPrimaryLabel.LABEL_BLOCKED_PROFITABILITY_CONTEXT
    if any("TECH" in key.upper() for key in blocked_counts):
        return DistillationDatasetPrimaryLabel.LABEL_BLOCKED_TECHNICAL_EVIDENCE_CONTEXT
    if any("RISK" in key.upper() for key in blocked_counts):
        return DistillationDatasetPrimaryLabel.LABEL_BLOCKED_RISK_CONTEXT
    if bundle.risk_summary.report_only_count > 0:
        return DistillationDatasetPrimaryLabel.LABEL_REPORT_ONLY_CONTEXT
    ordered = [
        ("OUTCOME_FAVORABLE", DistillationDatasetPrimaryLabel.LABEL_FAVORABLE_OBSERVATION),
        ("OUTCOME_ADVERSE", DistillationDatasetPrimaryLabel.LABEL_ADVERSE_OBSERVATION),
        ("OUTCOME_NEUTRAL", DistillationDatasetPrimaryLabel.LABEL_NEUTRAL_OBSERVATION),
        ("OUTCOME_INCONCLUSIVE", DistillationDatasetPrimaryLabel.LABEL_INCONCLUSIVE_OBSERVATION),
    ]
    best_name = None
    best_count = -1
    for key, _ in ordered:
        count = int(outcome_counts.get(key, 0))
        if count > best_count:
            best_name = key
            best_count = count
    if best_count <= 0:
        return DistillationDatasetPrimaryLabel.LABEL_INSUFFICIENT_CONTEXT
    for key, label in ordered:
        if key == best_name:
            return label
    return DistillationDatasetPrimaryLabel.LABEL_INSUFFICIENT_CONTEXT


def _auxiliary_labels_for_bundle(fixture: DomesticDistillationDatasetFixture) -> list[DistillationDatasetAuxiliaryLabel]:
    labels: set[DistillationDatasetAuxiliaryLabel] = {
        DistillationDatasetAuxiliaryLabel.AUX_NON_ACTIONABLE_CONTEXT,
        DistillationDatasetAuxiliaryLabel.AUX_TRAINING_ONLY_CONTEXT,
    }
    bundle = fixture.training_only_distillation_input_set.advisory_context_bundle
    policy = fixture.training_only_distillation_policy
    if bundle.risk_summary.report_only_count > 0:
        labels.add(DistillationDatasetAuxiliaryLabel.AUX_REPORT_ONLY_CONTEXT)
    blocked_counts = _blocked_counts(bundle)
    if any("SAFETY" in key.upper() for key in blocked_counts):
        labels.add(DistillationDatasetAuxiliaryLabel.AUX_SAFETY_BLOCK_PRESENT)
    if any("PROFIT" in key.upper() for key in blocked_counts):
        labels.add(DistillationDatasetAuxiliaryLabel.AUX_PROFITABILITY_BLOCK_PRESENT)
    if any("TECH" in key.upper() for key in blocked_counts):
        labels.add(DistillationDatasetAuxiliaryLabel.AUX_TECHNICAL_EVIDENCE_BLOCK_PRESENT)
    if any("RISK" in key.upper() for key in blocked_counts):
        labels.add(DistillationDatasetAuxiliaryLabel.AUX_RISK_BLOCK_PRESENT)
    if fixture.training_only_distillation_input_set.data_quality_summary.get("data_quality_flags"):
        labels.add(DistillationDatasetAuxiliaryLabel.AUX_DATA_QUALITY_WARNING)
    if len(fixture.training_only_distillation_input_set.scenario_family_coverage) <= policy.minimum_scenario_coverage_count:
        labels.add(DistillationDatasetAuxiliaryLabel.AUX_LOW_SCENARIO_COVERAGE)
    if len(fixture.training_only_distillation_input_set.symbol_coverage) <= policy.minimum_symbol_coverage_count:
        labels.add(DistillationDatasetAuxiliaryLabel.AUX_LOW_SYMBOL_COVERAGE)
    if (
        len(fixture.training_only_distillation_input_set.observation_horizon_coverage)
        <= policy.minimum_observation_horizon_coverage_count
    ):
        labels.add(DistillationDatasetAuxiliaryLabel.AUX_LOW_OBSERVATION_HORIZON_COVERAGE)
    return sorted(labels, key=lambda item: item.value)


def _feature_set_for_bundle(fixture: DomesticDistillationDatasetFixture) -> DistillationFeatureSet:
    bundle = fixture.training_only_distillation_input_set.advisory_context_bundle
    input_set = fixture.training_only_distillation_input_set
    outcome_counts = dict(bundle.outcome_label_summary.get("outcome_label_counts", {}))
    total = max(sum(int(value) for value in outcome_counts.values()), 1)
    ratio = {f"{key.lower()}_ratio": round(int(value) / total, 6) for key, value in outcome_counts.items()}
    coverage = {
        "scenario_family_count": len(input_set.scenario_family_coverage),
        "symbol_count": len(input_set.symbol_coverage),
        "observation_horizon_count": len(input_set.observation_horizon_coverage),
    }
    risk_features = {
        "safety_rejected_count": bundle.risk_summary.safety_rejected_count,
        "blocked_confirmed_count": bundle.risk_summary.blocked_confirmed_count,
        "report_only_count": bundle.risk_summary.report_only_count,
        "non_actionable_count": bundle.risk_summary.non_actionable_count,
    }
    return DistillationFeatureSet(
        outcome_count_features={**outcome_counts, **ratio},
        blocked_reason_features=_blocked_counts(bundle),
        report_only_features=_report_only_counts(bundle),
        non_actionable_features=_non_actionable_counts(bundle),
        coverage_features=coverage,
        risk_features=risk_features,
        data_quality_features={
            "data_quality_flags": input_set.data_quality_summary.get("data_quality_flags", []),
            "warning_count": len(input_set.data_quality_summary.get("data_quality_flags", [])),
        },
        market_profile_reference_features={"market_profile_id": bundle.market_profile_id, "strategy_track": bundle.strategy_track.value},
    )


def _record_from_section(
    fixture: DomesticDistillationDatasetFixture,
    record_type: DistillationDatasetRecordType,
    section: dict,
    index: int,
) -> DistillationDatasetRecord:
    bundle = fixture.training_only_distillation_input_set.advisory_context_bundle
    feature_set = _feature_set_for_bundle(fixture)
    primary_label = _primary_label_for_bundle(bundle)
    auxiliary_labels = _auxiliary_labels_for_bundle(fixture)
    section_key = section["section_key"]
    return DistillationDatasetRecord(
        record_id=f"{_pack_id(fixture)}-{record_type.value.lower()}-{index}",
        dataset_pack_id=_pack_id(fixture),
        record_type=record_type,
        source_bundle_id=bundle.bundle_id,
        source_evidence_item_ids=[item.evidence_item_id for item in bundle.evidence_items],
        source_outcome_review_report_id=bundle.source_outcome_review_report_id,
        source_paper_shadow_journal_id=bundle.source_paper_shadow_journal_id,
        source_promotion_gate_id=bundle.source_promotion_gate_id,
        source_sub_summary_id=section_key,
        strategy_track=bundle.strategy_track,
        market_profile_id=bundle.market_profile_id,
        scenario_family=section_key if record_type == DistillationDatasetRecordType.SCENARIO_FAMILY_RECORD else None,
        replay_window=section_key if record_type == DistillationDatasetRecordType.REPLAY_WINDOW_RECORD else None,
        observation_horizon=section_key if record_type == DistillationDatasetRecordType.OBSERVATION_HORIZON_RECORD else None,
        feature_set=feature_set,
        label_set=DistillationLabelSet(
            primary_label=primary_label,
            auxiliary_labels=auxiliary_labels,
            label_source_summary={
                "section_key": section_key,
                "source_summary_text": section["summary_text"],
            },
        ),
        context_summary=section["summary_text"],
        source_trace_references=list(section.get("trace_references", [])),
        prompt_stubs=list(fixture.training_only_distillation_input_set.prompt_stubs),
    )


def _aggregate_record(fixture: DomesticDistillationDatasetFixture, index: int) -> DistillationDatasetRecord:
    bundle = fixture.training_only_distillation_input_set.advisory_context_bundle
    return DistillationDatasetRecord(
        record_id=f"{_pack_id(fixture)}-bundle-aggregate-{index}",
        dataset_pack_id=_pack_id(fixture),
        record_type=DistillationDatasetRecordType.BUNDLE_AGGREGATE_RECORD,
        source_bundle_id=bundle.bundle_id,
        source_evidence_item_ids=[item.evidence_item_id for item in bundle.evidence_items],
        source_outcome_review_report_id=bundle.source_outcome_review_report_id,
        source_paper_shadow_journal_id=bundle.source_paper_shadow_journal_id,
        source_promotion_gate_id=bundle.source_promotion_gate_id,
        source_sub_summary_id="REVIEW_LEVEL_SUMMARY",
        strategy_track=bundle.strategy_track,
        market_profile_id=bundle.market_profile_id,
        feature_set=_feature_set_for_bundle(fixture),
        label_set=DistillationLabelSet(
            primary_label=_primary_label_for_bundle(bundle),
            auxiliary_labels=_auxiliary_labels_for_bundle(fixture),
            label_source_summary={"section_key": "REVIEW_LEVEL_SUMMARY"},
        ),
        context_summary=bundle.review_level_summary.get("summary_text"),
        source_trace_references=list(bundle.review_level_summary.get("source_ids", [])),
        prompt_stubs=list(fixture.training_only_distillation_input_set.prompt_stubs),
    )


def build_domestic_distillation_dataset_pack(
    fixture: DomesticDistillationDatasetFixture,
) -> DistillationDatasetPack:
    categories = _validation_categories(fixture)
    if categories:
        raise ValueError(f"distillation dataset build blocked: {', '.join(categories)}")
    bundle = fixture.training_only_distillation_input_set.advisory_context_bundle
    records: list[DistillationDatasetRecord] = []
    for index, section in enumerate(bundle.scenario_family_sub_summaries, start=1):
        records.append(_record_from_section(fixture, DistillationDatasetRecordType.SCENARIO_FAMILY_RECORD, section, index))
    for index, section in enumerate(bundle.replay_window_sub_summaries, start=1):
        records.append(_record_from_section(fixture, DistillationDatasetRecordType.REPLAY_WINDOW_RECORD, section, index))
    for index, section in enumerate(bundle.observation_horizon_sub_summaries, start=1):
        records.append(_record_from_section(fixture, DistillationDatasetRecordType.OBSERVATION_HORIZON_RECORD, section, index))
    if fixture.training_only_distillation_policy.aggregate_record_enabled:
        records.append(_aggregate_record(fixture, len(records) + 1))
    type_counts = Counter(record.record_type.value for record in records)
    return DistillationDatasetPack(
        pack_id=_pack_id(fixture),
        source_bundle_id=bundle.bundle_id,
        strategy_track=bundle.strategy_track,
        market_profile_id=bundle.market_profile_id,
        record_count=len(records),
        records=records,
        summary_counts=dict(type_counts),
        metadata_json=dict(DOMESTIC_DISTILLATION_DATASET_METADATA),
    )


def build_domestic_distillation_dataset_validation_report(
    fixture: DomesticDistillationDatasetFixture,
) -> DistillationDatasetValidationReport:
    categories = _validation_categories(fixture)
    coverage_failures = {
        DistillationDatasetGapCategory.INSUFFICIENT_SCENARIO_COVERAGE.value,
        DistillationDatasetGapCategory.INSUFFICIENT_SYMBOL_COVERAGE.value,
        DistillationDatasetGapCategory.INSUFFICIENT_OBSERVATION_HORIZON_COVERAGE.value,
    }
    training_only_present = (
        fixture.training_only_distillation_config.training_only
        and fixture.training_only_distillation_input_set.training_only
        and fixture.training_only_distillation_config.non_executable
        and fixture.training_only_distillation_input_set.non_executable
    )
    return DistillationDatasetValidationReport(
        report_id=f"{fixture.run_id}-distillation-validation",
        pack_reference=_pack_id(fixture),
        valid=not categories,
        strategy_track=fixture.training_only_distillation_config.strategy_track,
        market_profile_id=fixture.training_only_distillation_config.market_profile_id,
        training_only_metadata_present=training_only_present,
        coverage_sufficient=not any(category in coverage_failures for category in categories),
        block_reasons=categories,
        warnings=[],
        metadata_json=dict(DOMESTIC_DISTILLATION_DATASET_METADATA),
    )


def build_domestic_distillation_dataset_gap_report(
    fixture: DomesticDistillationDatasetFixture,
) -> DistillationDatasetGapReport:
    categories = _validation_categories(fixture)
    missing_markers = {
        DistillationDatasetGapCategory.MISSING_TRAINING_ONLY_MARKER.value,
        DistillationDatasetGapCategory.MISSING_NON_EXECUTABLE_MARKER.value,
        DistillationDatasetGapCategory.MISSING_PRIMARY_LABEL.value,
    }
    coverage = {
        DistillationDatasetGapCategory.INSUFFICIENT_SCENARIO_COVERAGE.value,
        DistillationDatasetGapCategory.INSUFFICIENT_SYMBOL_COVERAGE.value,
        DistillationDatasetGapCategory.INSUFFICIENT_OBSERVATION_HORIZON_COVERAGE.value,
        DistillationDatasetGapCategory.INSUFFICIENT_LABEL_DISTRIBUTION.value,
    }
    runtime = {
        DistillationDatasetGapCategory.PROMPT_EXECUTION_NOT_ALLOWED.value,
        DistillationDatasetGapCategory.LLM_RUNTIME_NOT_ALLOWED.value,
        DistillationDatasetGapCategory.LOCAL_MODEL_RUNTIME_NOT_ALLOWED.value,
        DistillationDatasetGapCategory.ORDER_ARTIFACT_DETECTED.value,
    }
    unsafe = {
        DistillationDatasetGapCategory.UNSAFE_LABEL_DETECTED.value,
        DistillationDatasetGapCategory.UNSAFE_AUXILIARY_LABEL_DETECTED.value,
        DistillationDatasetGapCategory.EXECUTABLE_WORDING_DETECTED.value,
        DistillationDatasetGapCategory.POTENTIAL_LEAKAGE_DETECTED.value,
    }
    return DistillationDatasetGapReport(
        report_id=f"{fixture.run_id}-distillation-gap-report",
        pack_reference=_pack_id(fixture),
        gap_categories=categories,
        missing_marker_count=sum(category in missing_markers for category in categories),
        insufficient_coverage_count=sum(category in coverage for category in categories),
        unsafe_pattern_count=sum(category in unsafe for category in categories),
        runtime_violation_count=sum(category in runtime for category in categories),
        metadata_json=dict(DOMESTIC_DISTILLATION_DATASET_METADATA),
    )


def build_domestic_distillation_dataset_safety_report(
    fixture: DomesticDistillationDatasetFixture,
) -> DistillationDatasetSafetyReport:
    categories = _validation_categories(fixture)
    safety_related = {
        DistillationDatasetGapCategory.PROMPT_EXECUTION_NOT_ALLOWED.value,
        DistillationDatasetGapCategory.LLM_RUNTIME_NOT_ALLOWED.value,
        DistillationDatasetGapCategory.LOCAL_MODEL_RUNTIME_NOT_ALLOWED.value,
        DistillationDatasetGapCategory.ORDER_ARTIFACT_DETECTED.value,
        DistillationDatasetGapCategory.UNSAFE_LABEL_DETECTED.value,
        DistillationDatasetGapCategory.UNSAFE_AUXILIARY_LABEL_DETECTED.value,
        DistillationDatasetGapCategory.EXECUTABLE_WORDING_DETECTED.value,
    }
    config = fixture.training_only_distillation_config
    return DistillationDatasetSafetyReport(
        report_id=f"{fixture.run_id}-distillation-safety-report",
        strategy_track=config.strategy_track,
        safety_boundary=DistillationDatasetSafetyBoundary(
            training_only=config.training_only,
            non_executable=config.non_executable,
            runtime_decision_allowed=config.runtime_decision_allowed,
            llm_runtime_allowed=config.llm_runtime_allowed,
            cloud_llm_called=config.cloud_llm_called,
            local_model_runtime_called=config.local_model_runtime_called,
            prompt_stub_execution_allowed=False,
            no_trade_instruction=config.no_trade_instruction,
        ),
        warnings=[],
        block_reasons=[category for category in categories if category in safety_related],
        metadata_json=dict(DOMESTIC_DISTILLATION_DATASET_METADATA),
    )
