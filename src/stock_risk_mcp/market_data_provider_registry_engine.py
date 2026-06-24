from __future__ import annotations

from stock_risk_mcp.market_data_provider_registry_guard import validate_market_data_provider_registry_metadata_safety
from stock_risk_mcp.market_data_provider_registry_models import (
    CanonicalDataContractReport,
    DataClass,
    GlobalProviderRegistryReport,
    MarketDataProviderGapReport,
    MarketDataProviderRegistryInput,
    ModuleDataRequirementReport,
    ProviderCandidate,
    ProviderCandidateName,
    ProviderReadinessLevel,
    ProviderRegistryGapEntry,
    ProviderReadinessMatrixReport,
    ProviderSelectionDecision,
    ProviderSelectionReport,
    SymbolMappingReport,
)


def _gap(input_id: str, suffix: str, category: str, severity: str, message: str) -> ProviderRegistryGapEntry:
    return ProviderRegistryGapEntry(
        gap_id=f"{input_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def _provider_map(providers: list[ProviderCandidate]) -> dict[ProviderCandidateName, ProviderCandidate]:
    return {item.provider_name: item for item in providers}


def build_market_data_provider_registry(registry_input: MarketDataProviderRegistryInput) -> MarketDataProviderRegistryInput:
    for audit in registry_input.audit_records:
        validate_market_data_provider_registry_metadata_safety(
            {"source_path": audit.source_path, "operator_context": audit.operator_context},
            context="provider registry",
        )

    providers = registry_input.provider_candidates
    provider_map = _provider_map(providers)
    gaps: list[ProviderRegistryGapEntry] = []
    missing_evidence: list[str] = []
    subscription_cost_gaps: list[str] = []
    license_terms_gaps: list[str] = []
    latency_gaps: list[str] = []
    coverage_gaps: list[str] = []
    symbol_mapping_gaps: list[str] = []
    rejected_providers: list[str] = []

    for provider in providers:
        if provider.api_key_evidence_ref:
            validate_market_data_provider_registry_metadata_safety({"api_key_evidence_ref": provider.api_key_evidence_ref}, context=provider.provider_name.value)
        if provider.subscription_evidence_ref:
            validate_market_data_provider_registry_metadata_safety({"subscription_evidence_ref": provider.subscription_evidence_ref}, context=provider.provider_name.value)
        if provider.api_key_required and not provider.api_key_evidence_ref:
            missing_evidence.append(f"{provider.provider_name.value}_API_KEY_EVIDENCE")
            gaps.append(_gap(registry_input.registry_id, f"{provider.provider_name.value}-API-KEY-GAP", "API_KEY_EVIDENCE_GAP", "WARNING", f"{provider.provider_name.value} api key evidence is missing"))
        if provider.subscription_required and not provider.subscription_evidence_ref:
            subscription_cost_gaps.append(provider.provider_name.value)
            gaps.append(_gap(registry_input.registry_id, f"{provider.provider_name.value}-SUBSCRIPTION-GAP", "SUBSCRIPTION_COST_GAP", "WARNING", f"{provider.provider_name.value} subscription evidence is missing"))
        if not provider.license_terms_note_ref:
            license_terms_gaps.append(provider.provider_name.value)
        if provider.readiness_level in {ProviderReadinessLevel.REJECTED, ProviderReadinessLevel.GAP}:
            rejected_providers.append(provider.provider_name.value)

    mapping_keys = {item.canonical_key for item in registry_input.symbol_mappings}
    for required_key in (
        "NQ_FUTURES_MAIN",
        "ES_FUTURES_MAIN",
        "VIX_INDEX",
        "DXY_INDEX",
        "US10Y_YIELD",
        "USDKRW_SPOT",
        "FOMC_EVENT",
        "US_CPI_EVENT",
    ):
        if required_key not in mapping_keys:
            symbol_mapping_gaps.append(required_key)
            gaps.append(_gap(registry_input.registry_id, f"MISSING-{required_key}", "SYMBOL_MAPPING_GAP", "WARNING", f"{required_key} symbol mapping is missing"))

    preferred_provider_by_data_class: dict[str, str] = {}
    fallback_provider_by_data_class: dict[str, str] = {}

    if ProviderCandidateName.DATABENTO in provider_map:
        preferred_provider_by_data_class[DataClass.FUTURES.value] = ProviderCandidateName.DATABENTO.value
        if provider_map[ProviderCandidateName.DATABENTO].subscription_evidence_ref is None or provider_map[ProviderCandidateName.DATABENTO].api_key_evidence_ref is None:
            gaps.append(_gap(registry_input.registry_id, "FUTURES-DATABENTO-EVIDENCE", "SUBSCRIPTION_COST_GAP", "WARNING", "Databento evidence refs are incomplete"))
    else:
        coverage_gaps.append(DataClass.FUTURES.value)
        gaps.append(_gap(registry_input.registry_id, "MISSING-FUTURES-PROVIDER", "CRITICAL_DATA_CLASS_MISSING", "WARNING", "preferred futures provider is missing"))

    if ProviderCandidateName.IBKR in provider_map:
        fallback_provider_by_data_class[DataClass.FUTURES.value] = ProviderCandidateName.IBKR.value
        preferred_provider_by_data_class[DataClass.BREADTH_MARKET_INTERNALS.value] = ProviderCandidateName.LOCAL_FIXTURE.value if ProviderCandidateName.LOCAL_FIXTURE in provider_map else ProviderCandidateName.UNKNOWN.value
    if ProviderCandidateName.YAHOO_DELAYED in provider_map:
        preferred_provider_by_data_class[DataClass.VOLATILITY_INDEX.value] = ProviderCandidateName.YAHOO_DELAYED.value
        fallback_provider_by_data_class[DataClass.EQUITY_PRICE_OHLCV.value] = ProviderCandidateName.YAHOO_DELAYED.value
    else:
        coverage_gaps.append(DataClass.VOLATILITY_INDEX.value)
    if ProviderCandidateName.FRED in provider_map:
        preferred_provider_by_data_class[DataClass.RATES_YIELDS.value] = ProviderCandidateName.FRED.value
    else:
        coverage_gaps.append(DataClass.RATES_YIELDS.value)
        gaps.append(_gap(registry_input.registry_id, "MISSING-RATES-PROVIDER", "CRITICAL_DATA_CLASS_MISSING", "WARNING", "rates provider is missing"))
    if ProviderCandidateName.ECOS_BOK in provider_map:
        preferred_provider_by_data_class[DataClass.FX.value] = ProviderCandidateName.ECOS_BOK.value
    else:
        coverage_gaps.append(DataClass.FX.value)
        gaps.append(_gap(registry_input.registry_id, "MISSING-FX-PROVIDER", "CRITICAL_DATA_CLASS_MISSING", "WARNING", "fx provider is missing"))
    if ProviderCandidateName.LOCAL_FIXTURE in provider_map:
        fallback_provider_by_data_class[DataClass.ECONOMIC_CALENDAR.value] = ProviderCandidateName.LOCAL_FIXTURE.value
        fallback_provider_by_data_class[DataClass.EARNINGS_CALENDAR.value] = ProviderCandidateName.LOCAL_FIXTURE.value
        fallback_provider_by_data_class[DataClass.BREADTH_MARKET_INTERNALS.value] = ProviderCandidateName.LOCAL_FIXTURE.value
        fallback_provider_by_data_class[DataClass.FEE_TAX_SLIPPAGE.value] = ProviderCandidateName.LOCAL_FIXTURE.value
    if ProviderCandidateName.CNN_FEAR_GREED in provider_map:
        preferred_provider_by_data_class[DataClass.SENTIMENT_FEAR_INDEX.value] = ProviderCandidateName.CNN_FEAR_GREED.value
    else:
        fallback_provider_by_data_class[DataClass.SENTIMENT_FEAR_INDEX.value] = ProviderCandidateName.LOCAL_FIXTURE.value if ProviderCandidateName.LOCAL_FIXTURE in provider_map else ProviderCandidateName.UNKNOWN.value

    for requirement in registry_input.module_requirements:
        for data_class in requirement.required_data_classes:
            if data_class.value not in preferred_provider_by_data_class and data_class.value not in fallback_provider_by_data_class:
                coverage_gaps.append(f"{requirement.module_name.value}:{data_class.value}")
                gaps.append(_gap(registry_input.registry_id, f"{requirement.module_name.value}-{data_class.value}-GAP", "CRITICAL_DATA_CLASS_MISSING", "WARNING", f"{requirement.module_name.value} has no provider candidate for {data_class.value}"))

    if coverage_gaps or any(item.gap_category == "CRITICAL_DATA_CLASS_MISSING" for item in gaps):
        selection_decision = ProviderSelectionDecision.GAP
    else:
        selection_decision = ProviderSelectionDecision.TRAINING_READY

    global_report = GlobalProviderRegistryReport(
        report_id=f"{registry_input.registry_id}-GLOBAL-PROVIDER-REGISTRY-REPORT",
        providers=providers,
    )
    module_report = ModuleDataRequirementReport(
        report_id=f"{registry_input.registry_id}-MODULE-DATA-REQUIREMENT-REPORT",
        requirements=registry_input.module_requirements,
    )
    readiness_report = ProviderReadinessMatrixReport(
        report_id=f"{registry_input.registry_id}-PROVIDER-READINESS-MATRIX-REPORT",
        readiness_by_provider={item.provider_name.value: item.readiness_level.value for item in providers},
    )
    contract_report = CanonicalDataContractReport(
        report_id=f"{registry_input.registry_id}-CANONICAL-DATA-CONTRACT-REPORT",
        contracts=registry_input.canonical_contracts,
    )
    mapping_report = SymbolMappingReport(
        report_id=f"{registry_input.registry_id}-SYMBOL-MAPPING-REPORT",
        mappings=registry_input.symbol_mappings,
    )
    selection_report = ProviderSelectionReport(
        report_id=f"{registry_input.registry_id}-PROVIDER-SELECTION-REPORT",
        selection_decision=selection_decision,
        preferred_provider_by_data_class=preferred_provider_by_data_class,
        fallback_provider_by_data_class=fallback_provider_by_data_class,
        rejected_providers=rejected_providers,
        missing_evidence=missing_evidence,
        subscription_cost_gaps=subscription_cost_gaps,
        license_terms_gaps=license_terms_gaps,
        latency_gaps=latency_gaps,
        coverage_gaps=coverage_gaps,
        symbol_mapping_gaps=symbol_mapping_gaps,
    )
    gaps.append(_gap(registry_input.registry_id, "REPORT-GENERATED", "REPORT_GENERATED", "REPORT_ONLY", "provider registry report generated"))
    gap_report = MarketDataProviderGapReport(
        gap_report_id=f"{registry_input.registry_id}-PROVIDER-GAP-REPORT",
        selection_decision=selection_decision,
        gap_entries=gaps,
    )
    return registry_input.model_copy(
        update={
            "global_provider_registry_report": global_report,
            "module_data_requirement_report": module_report,
            "provider_readiness_matrix_report": readiness_report,
            "canonical_data_contract_report": contract_report,
            "symbol_mapping_report": mapping_report,
            "provider_selection_report": selection_report,
            "gap_report": gap_report,
        }
    )
