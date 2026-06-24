from __future__ import annotations

from stock_risk_mcp.read_only_provider_adapter_guard import (
    validate_read_only_provider_adapter_metadata_safety,
)
from stock_risk_mcp.read_only_provider_adapter_models import (
    BlockedAccountOrderApiReport,
    CanonicalReadOnlyContractReport,
    CapabilityStatus,
    KiwoomRestEvidenceMapReport,
    LsFutureCompatibilityReport,
    ProviderCapabilityMatrixReport,
    ProviderCapabilityMatrixRow,
    ProviderRole,
    ReadOnlyAdapterReadiness,
    ReadOnlyProvider,
    ReadOnlyProviderAdapterGapEntry,
    ReadOnlyProviderAdapterGapReport,
    ReadOnlyProviderAdapterInput,
    ReadOnlyProviderAdapterSummaryReport,
    ProviderMigrationReadinessReport,
)


def _gap(adapter_id: str, suffix: str, category: str, severity: str, message: str) -> ReadOnlyProviderAdapterGapEntry:
    return ReadOnlyProviderAdapterGapEntry(
        gap_id=f"{adapter_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def build_read_only_provider_adapter_boundary(adapter_input: ReadOnlyProviderAdapterInput) -> ReadOnlyProviderAdapterInput:
    for audit in adapter_input.audit_records:
        validate_read_only_provider_adapter_metadata_safety(
            {"source_path": audit.source_path, "operator_context": audit.operator_context},
            context="read-only provider adapter audit",
        )

    provider_map = {item.provider: item for item in adapter_input.provider_definitions}
    evidence_ids = {item.api_id for item in adapter_input.kiwoom_rest_evidence_entries}
    gaps: list[ReadOnlyProviderAdapterGapEntry] = []
    blockers: list[str] = []

    kiwoom = provider_map.get(ReadOnlyProvider.KIWOOM_REST)
    ls = provider_map.get(ReadOnlyProvider.LS_OPEN_API)
    if kiwoom is None or kiwoom.role != ProviderRole.CURRENT_PRIMARY:
        gaps.append(_gap(adapter_input.adapter_id, "KIWOOM-ROLE", "KIWOOM_NOT_CURRENT_PRIMARY", "BLOCKING", "Kiwoom REST must be current primary"))
    if ls is None or ls.role != ProviderRole.FUTURE_MIGRATION_TARGET:
        gaps.append(_gap(adapter_input.adapter_id, "LS-ROLE", "LS_NOT_FUTURE_TARGET", "BLOCKING", "LS OPEN API must remain future migration target"))
    if ls is not None and (ls.implemented or not ls.placeholder_only or not ls.future_api_evidence_required):
        gaps.append(_gap(adapter_input.adapter_id, "LS-CLAIM", "LS_IMPLEMENTATION_CLAIM_BLOCKED", "BLOCKING", "LS must remain placeholder only"))
    if adapter_input.ls_future_placeholder.implemented_now or adapter_input.ls_future_placeholder.coverage_claimed_now:
        gaps.append(_gap(adapter_input.adapter_id, "LS-PLACEHOLDER", "LS_PLACEHOLDER_CLAIM_BLOCKED", "BLOCKING", "LS placeholder must not claim coverage"))

    core_ohlcv_ids = {"KA10005", "KA10080", "KA10081", "KA10082", "KA10083", "KA10086"}
    core_quote_ids = {"KA10004", "KA10006"}
    ranking_ids = {"KA00198", "KA10016", "KA10017", "KA10019", "KA10023", "KA10027", "KA10030", "KA10032", "KA10098"}
    flow_ids = {"KA10008", "KA10014", "KA10058", "KA10059", "KA10060", "KA10061", "KA10063", "KA10064", "KA10065", "KA10066", "KA10068", "KA90003", "KA90004", "KA90005", "KA90007", "KA90008", "KA90009", "KA90010", "KA90012", "KA90013"}
    sector_theme_ids = {"KA20001", "KA20002", "KA20003", "KA20006", "KA40002", "KA40003", "KA40004", "KA90001", "KA90002"}
    realtime_ids = {"0B", "0D", "0E", "0J", "0U", "1H"}
    blocked_ids = {item.api_id for item in adapter_input.blocked_account_order_api_records}

    if not (core_ohlcv_ids & evidence_ids):
        gaps.append(_gap(adapter_input.adapter_id, "OHLCV", "KIWOOM_OHLCV_EVIDENCE_GAP", "WARNING", "Kiwoom OHLCV evidence is incomplete"))
    if not (core_quote_ids & evidence_ids):
        gaps.append(_gap(adapter_input.adapter_id, "QUOTE", "KIWOOM_QUOTE_EVIDENCE_GAP", "WARNING", "Kiwoom quote evidence is incomplete"))
    if not (ranking_ids & evidence_ids):
        gaps.append(_gap(adapter_input.adapter_id, "RANK", "KIWOOM_RANK_EVIDENCE_GAP", "WARNING", "Kiwoom ranking evidence is incomplete"))
    if not (flow_ids & evidence_ids):
        gaps.append(_gap(adapter_input.adapter_id, "FLOW", "KIWOOM_FLOW_EVIDENCE_GAP", "WARNING", "Kiwoom flow evidence is incomplete"))
    if not (sector_theme_ids & evidence_ids):
        gaps.append(_gap(adapter_input.adapter_id, "SECTOR", "KIWOOM_SECTOR_THEME_EVIDENCE_GAP", "WARNING", "Kiwoom sector/theme evidence is incomplete"))
    if not (blocked_ids & {"KA00001", "KT10000", "00", "04"}):
        gaps.append(_gap(adapter_input.adapter_id, "BLOCKED-APIS", "ACCOUNT_ORDER_BLOCK_LIST_INCOMPLETE", "WARNING", "blocked account/order APIs are incomplete"))

    if not adapter_input.canonical_quotes or not adapter_input.canonical_ohlcv_records:
        gaps.append(_gap(adapter_input.adapter_id, "CANONICAL", "CANONICAL_CONTRACT_GAP", "WARNING", "canonical quote/OHLCV samples are missing"))
    if not adapter_input.canonical_capability_records:
        gaps.append(_gap(adapter_input.adapter_id, "CAPABILITY", "CANONICAL_CAPABILITY_GAP", "WARNING", "canonical capability records are missing"))

    capability_rows = [
        ProviderCapabilityMatrixRow(
            capability_name="DOMESTIC_OHLCV",
            provider=ReadOnlyProvider.KIWOOM_REST,
            status=CapabilityStatus.AVAILABLE_NOW if core_ohlcv_ids & evidence_ids else CapabilityStatus.UNKNOWN,
            notes="KIWOOM_CHART_APIS_MAP_TO_CANONICAL_OHLCV",
        ),
        ProviderCapabilityMatrixRow(
            capability_name="DOMESTIC_QUOTE_ORDERBOOK",
            provider=ReadOnlyProvider.KIWOOM_REST,
            status=CapabilityStatus.AVAILABLE_NOW if core_quote_ids & evidence_ids else CapabilityStatus.UNKNOWN,
            notes="KIWOOM_QUOTE_APIS_MAP_TO_CANONICAL_QUOTE",
        ),
        ProviderCapabilityMatrixRow(
            capability_name="DOMESTIC_OUTLIER_RANKING",
            provider=ReadOnlyProvider.KIWOOM_REST,
            status=CapabilityStatus.AVAILABLE_NOW if ranking_ids & evidence_ids else CapabilityStatus.UNKNOWN,
            notes="KIWOOM_RANKING_APIS_MAP_TO_CANONICAL_RANK",
        ),
        ProviderCapabilityMatrixRow(
            capability_name="DOMESTIC_FLOW_SHORT_PROGRAM",
            provider=ReadOnlyProvider.KIWOOM_REST,
            status=CapabilityStatus.AVAILABLE_NOW if flow_ids & evidence_ids else CapabilityStatus.UNKNOWN,
            notes="KIWOOM_FLOW_APIS_MAP_TO_CANONICAL_FLOW",
        ),
        ProviderCapabilityMatrixRow(
            capability_name="SECTOR_THEME_ETF",
            provider=ReadOnlyProvider.KIWOOM_REST,
            status=CapabilityStatus.AVAILABLE_NOW if sector_theme_ids & evidence_ids else CapabilityStatus.UNKNOWN,
            notes="KIWOOM_SECTOR_THEME_APIS_MAP_TO_CANONICAL_SECTOR_THEME",
        ),
        ProviderCapabilityMatrixRow(
            capability_name="READONLY_REALTIME_EVENTS",
            provider=ReadOnlyProvider.KIWOOM_REST,
            status=CapabilityStatus.AVAILABLE_NOW if realtime_ids & evidence_ids else CapabilityStatus.UNKNOWN,
            notes="KIWOOM_REALTIME_EVENTS_ARE_READONLY_ONLY",
        ),
        ProviderCapabilityMatrixRow(
            capability_name="ACCOUNT_ORDER_APIS",
            provider=ReadOnlyProvider.KIWOOM_REST,
            status=CapabilityStatus.BLOCKED,
            notes="ACCOUNT_AND_ORDER_APIS_BLOCKED_IN_READONLY_LAYER",
        ),
        ProviderCapabilityMatrixRow(
            capability_name="LS_FUTURE_DOMESTIC_READONLY",
            provider=ReadOnlyProvider.LS_OPEN_API,
            status=CapabilityStatus.FUTURE_PLACEHOLDER,
            notes="LS_REQUIRES_EXACT_EVIDENCE_BEFORE_COVERAGE",
        ),
        ProviderCapabilityMatrixRow(
            capability_name="NQ_ES_FUTURES",
            provider=ReadOnlyProvider.UNKNOWN,
            status=CapabilityStatus.EXTERNAL_REQUIRED,
            notes="EXTERNAL_PROVIDER_REQUIRED",
        ),
        ProviderCapabilityMatrixRow(
            capability_name="VIX_DXY_US10Y_USDKRW",
            provider=ReadOnlyProvider.UNKNOWN,
            status=CapabilityStatus.EXTERNAL_REQUIRED,
            notes="EXTERNAL_PROVIDER_REQUIRED",
        ),
        ProviderCapabilityMatrixRow(
            capability_name="ECONOMIC_CALENDAR",
            provider=ReadOnlyProvider.UNKNOWN,
            status=CapabilityStatus.EXTERNAL_REQUIRED,
            notes="EXTERNAL_PROVIDER_REQUIRED",
        ),
    ]

    if any(item.severity == "BLOCKING" for item in gaps):
        readiness = ReadOnlyAdapterReadiness.BLOCKED
        decision_reason = "blocking provider boundary violation detected"
    elif any(item.gap_category == "CANONICAL_CONTRACT_GAP" for item in gaps):
        readiness = ReadOnlyAdapterReadiness.KIWOOM_READONLY_EVIDENCE_READY
        decision_reason = "Kiwoom read-only evidence exists but canonical contract is incomplete"
    elif any(item.severity == "WARNING" for item in gaps):
        readiness = ReadOnlyAdapterReadiness.DATA_GAP
        decision_reason = "provider boundary has unresolved data gaps"
    else:
        readiness = ReadOnlyAdapterReadiness.CANONICAL_CONTRACT_READY
        decision_reason = "Kiwoom-first canonical read-only boundary is ready"

    if ls is not None and ls.placeholder_only:
        blockers.append("LS_EXACT_API_EVIDENCE_REQUIRED")
    for gap_market in adapter_input.external_gap_markets:
        blockers.append(gap_market)

    summary_report = ReadOnlyProviderAdapterSummaryReport(
        report_id=f"{adapter_input.adapter_id}-SUMMARY-REPORT",
        readiness=readiness,
        current_primary_provider=adapter_input.current_provider,
        future_provider=adapter_input.future_provider,
        decision_reason=decision_reason,
    )
    evidence_map_report = KiwoomRestEvidenceMapReport(
        report_id=f"{adapter_input.adapter_id}-KIWOOM-EVIDENCE-MAP-REPORT",
        entries=adapter_input.kiwoom_rest_evidence_entries,
    )
    ls_report = LsFutureCompatibilityReport(
        report_id=f"{adapter_input.adapter_id}-LS-FUTURE-COMPATIBILITY-REPORT",
        placeholder=adapter_input.ls_future_placeholder,
    )
    canonical_report = CanonicalReadOnlyContractReport(
        report_id=f"{adapter_input.adapter_id}-CANONICAL-READONLY-CONTRACT-REPORT",
        request_envelope_boundary=adapter_input.request_envelope_boundary,
        quotes=adapter_input.canonical_quotes,
        ohlcv_records=adapter_input.canonical_ohlcv_records,
        rank_signals=adapter_input.canonical_rank_signals,
        flow_signals=adapter_input.canonical_flow_signals,
        sector_theme_signals=adapter_input.canonical_sector_theme_signals,
        realtime_events=adapter_input.canonical_realtime_events,
        capability_records=adapter_input.canonical_capability_records,
    )
    capability_report = ProviderCapabilityMatrixReport(
        report_id=f"{adapter_input.adapter_id}-PROVIDER-CAPABILITY-MATRIX-REPORT",
        rows=capability_rows,
    )
    blocked_report = BlockedAccountOrderApiReport(
        report_id=f"{adapter_input.adapter_id}-BLOCKED-ACCOUNT-ORDER-API-REPORT",
        blocked_records=adapter_input.blocked_account_order_api_records,
    )
    migration_report = ProviderMigrationReadinessReport(
        report_id=f"{adapter_input.adapter_id}-PROVIDER-MIGRATION-READINESS-REPORT",
        kiwoom_primary_ready=bool(kiwoom and kiwoom.role == ProviderRole.CURRENT_PRIMARY),
        ls_placeholder_only=bool(ls and ls.role == ProviderRole.FUTURE_MIGRATION_TARGET and ls.placeholder_only),
        canonical_contract_ready=readiness == ReadOnlyAdapterReadiness.CANONICAL_CONTRACT_READY,
        migration_blockers=blockers,
    )
    gaps.append(_gap(adapter_input.adapter_id, "REPORT-GENERATED", "READONLY_PROVIDER_REPORT_GENERATED", "REPORT_ONLY", "read-only provider adapter report generated"))
    gap_report = ReadOnlyProviderAdapterGapReport(
        gap_report_id=f"{adapter_input.adapter_id}-READONLY-PROVIDER-GAP-REPORT",
        readiness=readiness,
        gap_entries=gaps,
    )
    return adapter_input.model_copy(
        update={
            "summary_report": summary_report,
            "kiwoom_rest_evidence_map_report": evidence_map_report,
            "ls_future_compatibility_report": ls_report,
            "canonical_readonly_contract_report": canonical_report,
            "provider_capability_matrix_report": capability_report,
            "blocked_account_order_api_report": blocked_report,
            "provider_migration_readiness_report": migration_report,
            "gap_report": gap_report,
        }
    )
