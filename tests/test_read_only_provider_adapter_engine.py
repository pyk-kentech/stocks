from stock_risk_mcp.read_only_provider_adapter_engine import build_read_only_provider_adapter_boundary
from stock_risk_mcp.read_only_provider_adapter_models import (
    CapabilityStatus,
    ReadOnlyAdapterReadiness,
    ReadOnlyProvider,
    ReadOnlyProviderAdapterInput,
)
from tests.test_read_only_provider_adapter_models import read_only_provider_adapter_payload


def _run(**overrides):
    payload = read_only_provider_adapter_payload()
    payload.update(overrides)
    return build_read_only_provider_adapter_boundary(ReadOnlyProviderAdapterInput.model_validate(payload))


def test_ls_does_not_claim_implemented_coverage_without_evidence():
    result = _run(
        provider_definitions=[
            item if item["provider"] != "LS_OPEN_API" else {**item, "implemented": True}
            for item in read_only_provider_adapter_payload()["provider_definitions"]
        ]
    )
    assert result.summary_report.readiness == ReadOnlyAdapterReadiness.BLOCKED


def test_canonical_quote_ohlcv_rank_flow_sector_models_are_provider_independent():
    result = _run()
    assert result.canonical_readonly_contract_report.quotes[0].provider == ReadOnlyProvider.KIWOOM_REST
    assert result.canonical_readonly_contract_report.ohlcv_records[0].provider_symbol == "005930"
    assert result.canonical_readonly_contract_report.rank_signals[0].provider_api_id == "KA00198"
    assert result.canonical_readonly_contract_report.flow_signals[0].provider_api_id == "KA10008"
    assert result.canonical_readonly_contract_report.sector_theme_signals[0].provider_api_id == "KA20001"


def test_kiwoom_chart_apis_map_to_canonical_ohlcv_capability():
    result = _run()
    row = next(item for item in result.provider_capability_matrix_report.rows if item.capability_name == "DOMESTIC_OHLCV")
    assert row.provider == ReadOnlyProvider.KIWOOM_REST
    assert row.status == CapabilityStatus.AVAILABLE_NOW


def test_kiwoom_ranking_flow_sector_capabilities_map_correctly():
    result = _run()
    rank_row = next(item for item in result.provider_capability_matrix_report.rows if item.capability_name == "DOMESTIC_OUTLIER_RANKING")
    flow_row = next(item for item in result.provider_capability_matrix_report.rows if item.capability_name == "DOMESTIC_FLOW_SHORT_PROGRAM")
    sector_row = next(item for item in result.provider_capability_matrix_report.rows if item.capability_name == "SECTOR_THEME_ETF")
    assert rank_row.status == CapabilityStatus.AVAILABLE_NOW
    assert flow_row.status == CapabilityStatus.AVAILABLE_NOW
    assert sector_row.status == CapabilityStatus.AVAILABLE_NOW


def test_kiwoom_account_order_apis_and_streams_are_blocked():
    result = _run()
    blocked_ids = {item.api_id for item in result.blocked_account_order_api_report.blocked_records}
    assert {"KA00001", "KT10000", "00", "04"} <= blocked_ids
    blocked_row = next(item for item in result.provider_capability_matrix_report.rows if item.capability_name == "ACCOUNT_ORDER_APIS")
    assert blocked_row.status == CapabilityStatus.BLOCKED


def test_external_market_and_calendar_needs_remain_gaps():
    result = _run()
    blockers = set(result.provider_migration_readiness_report.migration_blockers)
    assert {"NQ_ES_FUTURES", "VIX_DXY_10Y_USDKRW", "ECONOMIC_CALENDAR"} <= blockers


def test_missing_ohlcv_evidence_produces_data_gap_or_partial_readiness():
    payload = read_only_provider_adapter_payload()
    payload["kiwoom_rest_evidence_entries"] = [
        item for item in payload["kiwoom_rest_evidence_entries"] if item["api_id"] not in {"KA10080", "KA10081"}
    ]
    result = build_read_only_provider_adapter_boundary(ReadOnlyProviderAdapterInput.model_validate(payload))
    assert result.summary_report.readiness in {
        ReadOnlyAdapterReadiness.DATA_GAP,
        ReadOnlyAdapterReadiness.KIWOOM_READONLY_EVIDENCE_READY,
    }


def test_audit_is_redacted():
    result = _run()
    assert result.audit_records[0].redaction_applied is True
