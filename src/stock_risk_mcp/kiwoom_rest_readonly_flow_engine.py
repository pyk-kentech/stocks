from __future__ import annotations

from stock_risk_mcp.kiwoom_rest_readonly_flow_client import (
    TransportCallable,
    execute_kiwoom_rest_readonly_flow_transport,
)
from stock_risk_mcp.kiwoom_rest_readonly_flow_guard import validate_kiwoom_rest_flow_metadata_safety
from stock_risk_mcp.kiwoom_rest_readonly_flow_models import (
    CanonicalFlowCategory,
    CanonicalInvestorFlowSignal,
    CanonicalProgramTradingSignal,
    KiwoomRestCanonicalInvestorFlowReport,
    KiwoomRestCanonicalProgramFlowReport,
    KiwoomRestFlowAdapterResult,
    KiwoomRestFlowApiId,
    KiwoomRestFlowCapabilityMatrixEntry,
    KiwoomRestFlowCapabilityMatrixReport,
    KiwoomRestFlowConfig,
    KiwoomRestFlowContinuation,
    KiwoomRestFlowContinuationReport,
    KiwoomRestFlowGapEntry,
    KiwoomRestFlowGapReport,
    KiwoomRestFlowMockedResponseReport,
    KiwoomRestFlowReadiness,
    KiwoomRestFlowRequest,
    KiwoomRestFlowRequestReport,
    KiwoomRestFlowResponse,
    KiwoomRestFlowSummaryReport,
    KiwoomRestFlowV7IntegrationReport,
    KiwoomRestInvestorFlowItem,
    KiwoomRestLendingItem,
    KiwoomRestProgramFlowItem,
    KiwoomRestShortLendingCapabilityReport,
    KiwoomRestShortSellingItem,
)


CAPABILITY_GROUPS = {
    KiwoomRestFlowApiId.KA10008: "FLOW",
    KiwoomRestFlowApiId.KA10014: "SHORT",
    KiwoomRestFlowApiId.KA10058: "FLOW",
    KiwoomRestFlowApiId.KA10059: "FLOW",
    KiwoomRestFlowApiId.KA10060: "FLOW",
    KiwoomRestFlowApiId.KA10061: "FLOW",
    KiwoomRestFlowApiId.KA10063: "FLOW",
    KiwoomRestFlowApiId.KA10064: "FLOW",
    KiwoomRestFlowApiId.KA10065: "FLOW",
    KiwoomRestFlowApiId.KA10066: "FLOW",
    KiwoomRestFlowApiId.KA10068: "LENDING",
    KiwoomRestFlowApiId.KA10069: "LENDING",
    KiwoomRestFlowApiId.KA90003: "PROGRAM",
    KiwoomRestFlowApiId.KA90004: "PROGRAM",
    KiwoomRestFlowApiId.KA90005: "PROGRAM",
    KiwoomRestFlowApiId.KA90007: "PROGRAM",
    KiwoomRestFlowApiId.KA90008: "PROGRAM",
    KiwoomRestFlowApiId.KA90009: "FLOW",
    KiwoomRestFlowApiId.KA90010: "PROGRAM",
    KiwoomRestFlowApiId.KA90012: "LENDING",
    KiwoomRestFlowApiId.KA90013: "PROGRAM",
}

READY_BUILDERS = {KiwoomRestFlowApiId.KA10059}
SCHEMA_GAP_BUILDERS = {KiwoomRestFlowApiId.KA90003}
SHORT_CAPABILITIES = {KiwoomRestFlowApiId.KA10014}
LENDING_CAPABILITIES = {KiwoomRestFlowApiId.KA10068, KiwoomRestFlowApiId.KA10069, KiwoomRestFlowApiId.KA90012}


def _gap(config_id: str, suffix: str, category: str, severity: str, message: str) -> KiwoomRestFlowGapEntry:
    return KiwoomRestFlowGapEntry(
        gap_id=f"{config_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def _capability_readiness(api_id: KiwoomRestFlowApiId) -> KiwoomRestFlowReadiness:
    if api_id in READY_BUILDERS:
        return KiwoomRestFlowReadiness.INVESTOR_FLOW_READY
    if api_id in SCHEMA_GAP_BUILDERS:
        return KiwoomRestFlowReadiness.SCHEMA_GAP
    return KiwoomRestFlowReadiness.FUTURE_SUPPORTED


def _path_for_api(config: KiwoomRestFlowConfig) -> str | None:
    if config.api_id == KiwoomRestFlowApiId.KA10059:
        return "/api/dostk/stkinfo"
    if config.api_id == KiwoomRestFlowApiId.KA90003:
        return config.path_hint
    return None


def _build_request(config: KiwoomRestFlowConfig) -> KiwoomRestFlowRequest:
    if config.api_id == KiwoomRestFlowApiId.KA10059:
        return KiwoomRestFlowRequest(
            request_id=f"{config.config_id}-REQUEST",
            path="/api/dostk/stkinfo",
            api_id=config.api_id,
            continuation=config.continuation,
            request_headers={
                "api-id": "ka10059",
                "authorization": "Bearer <TOKEN_REF_ONLY>",
                "cont-yn": config.continuation.cont_yn,
                "next-key": config.continuation.next_key,
            },
            request_body={
                "dt": config.request_date,
                "stk_cd": config.provider_symbol,
                "amt_qty_tp": config.amt_qty_tp,
                "trde_tp": config.trde_tp,
                "unit_tp": config.unit_tp,
            },
        )
    if config.api_id == KiwoomRestFlowApiId.KA90003:
        if not config.path_hint:
            raise ValueError("ka90003 path evidence is missing; request builder remains schema_gap")
        return KiwoomRestFlowRequest(
            request_id=f"{config.config_id}-REQUEST",
            path=config.path_hint,
            api_id=config.api_id,
            continuation=config.continuation,
            request_headers={
                "api-id": "ka90003",
                "authorization": "Bearer <TOKEN_REF_ONLY>",
                "cont-yn": config.continuation.cont_yn,
                "next-key": config.continuation.next_key,
            },
            request_body={
                "trde_upper_tp": config.trde_upper_tp,
                "amt_qty_tp": config.amt_qty_tp,
                "mrkt_tp": config.mrkt_tp,
                "stex_tp": config.stex_tp,
            },
        )
    raise ValueError("account/order api id is blocked")


def build_kiwoom_rest_investor_flow_request(config: KiwoomRestFlowConfig) -> KiwoomRestFlowRequest:
    if config.api_id != KiwoomRestFlowApiId.KA10059:
        raise ValueError("investor flow request requires ka10059")
    return _build_request(config)


def build_kiwoom_rest_program_flow_request(config: KiwoomRestFlowConfig) -> KiwoomRestFlowRequest:
    if config.api_id != KiwoomRestFlowApiId.KA90003:
        raise ValueError("program flow request requires ka90003")
    return _build_request(config)


def _capability_matrix() -> list[KiwoomRestFlowCapabilityMatrixEntry]:
    entries: list[KiwoomRestFlowCapabilityMatrixEntry] = []
    for api_id in KiwoomRestFlowApiId:
        entries.append(
            KiwoomRestFlowCapabilityMatrixEntry(
                api_id=api_id,
                capability_group=CAPABILITY_GROUPS[api_id],
                request_builder_ready=api_id in READY_BUILDERS,
                readiness=_capability_readiness(api_id),
            )
        )
    return entries


def _short_lending_report_entries():
    short_entries = [
        KiwoomRestShortSellingItem(
            capability_id=f"{api_id.value}-CAPABILITY",
            api_id=api_id,
            request_builder_ready=False,
            schema_evidence_available=False,
        )
        for api_id in sorted(SHORT_CAPABILITIES, key=lambda item: item.value)
    ]
    lending_entries = [
        KiwoomRestLendingItem(
            capability_id=f"{api_id.value}-CAPABILITY",
            api_id=api_id,
            request_builder_ready=False,
            schema_evidence_available=False,
        )
        for api_id in sorted(LENDING_CAPABILITIES, key=lambda item: item.value)
    ]
    return short_entries, lending_entries


def _response_symbol(row: dict[str, object], config: KiwoomRestFlowConfig) -> str:
    return str(row.get("stk_cd") or config.provider_symbol or "").strip().upper()


def _response_stock_name(row: dict[str, object]) -> str | None:
    value = row.get("stk_nm") or row.get("stock_name")
    if value in (None, ""):
        return None
    return str(value).strip()


def _observed_at(config: KiwoomRestFlowConfig, row: dict[str, object]) -> str:
    dt = str(row.get("dt") or config.request_date or "").strip()
    return dt


def _parse_investor_items(config: KiwoomRestFlowConfig, payload: dict[str, object]) -> list[KiwoomRestInvestorFlowItem]:
    rows = payload.get("stk_invsr_orgn")
    if rows is None:
        raise ValueError("investor flow response rows are missing")
    if not isinstance(rows, list):
        raise ValueError("investor flow rows must be a list")
    items: list[KiwoomRestInvestorFlowItem] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("investor flow row must be an object")
        items.append(
            KiwoomRestInvestorFlowItem(
                observed_at=_observed_at(config, row),
                provider_symbol=_response_symbol(row, config),
                stock_name=_response_stock_name(row),
                current_price=row.get("cur_prc"),
                price_change=row.get("pred_pre"),
                foreign_net_amount=row.get("frgnr_net_amt"),
                institution_net_amount=row.get("orgn_net_amt"),
                retail_net_amount=row.get("retl_net_amt"),
                foreign_net_quantity=row.get("frgnr_net_qty"),
                institution_net_quantity=row.get("orgn_net_qty"),
                retail_net_quantity=row.get("retl_net_qty"),
            )
        )
    return items


def _parse_program_items(payload: dict[str, object]) -> list[KiwoomRestProgramFlowItem]:
    rows = payload.get("program_net_buy_top50") or payload.get("program_top50") or payload.get("stk_list")
    if rows is None:
        raise ValueError("program flow response rows are missing")
    if not isinstance(rows, list):
        raise ValueError("program flow rows must be a list")
    items: list[KiwoomRestProgramFlowItem] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("program flow row must be an object")
        items.append(
            KiwoomRestProgramFlowItem(
                observed_at=_aware(row.get("observed_at")) if row.get("observed_at") is not None else None,
                provider_symbol=str(row.get("stk_cd")).strip().upper() if row.get("stk_cd") not in (None, "") else None,
                stock_name=_response_stock_name(row),
                accumulated_trade_quantity=row.get("acc_trde_qty"),
                program_sell_amount=row.get("prm_sell_amt"),
                program_buy_amount=row.get("prm_buy_amt"),
                program_net_amount=row.get("prm_netprps_amt"),
            )
        )
    return items


def _parse_response(config: KiwoomRestFlowConfig, payload: dict[str, object]) -> KiwoomRestFlowResponse:
    if not isinstance(payload, dict):
        raise ValueError("mocked response payload must be an object")
    continuation = KiwoomRestFlowContinuation(
        cont_yn=(payload.get("cont_yn") or payload.get("contYn") or payload.get("cont-yn") or "N"),
        next_key=(payload.get("next_key") or payload.get("nextKey") or payload.get("next-key") or ""),
    )
    return_code = payload.get("return_code")
    return_msg = payload.get("return_msg")
    if return_code is None or return_msg is None:
        raise ValueError("response return_code/return_msg missing")
    investor_items = _parse_investor_items(config, payload) if int(return_code) == 0 and config.api_id == KiwoomRestFlowApiId.KA10059 else []
    program_items = _parse_program_items(payload) if int(return_code) == 0 and config.api_id == KiwoomRestFlowApiId.KA90003 else []
    return KiwoomRestFlowResponse(
        response_id=f"{config.config_id}-RESPONSE",
        api_id=config.api_id,
        return_code=int(return_code),
        return_msg=str(return_msg),
        investor_items=investor_items,
        program_items=program_items,
        continuation=continuation,
        raw_payload_redacted=True,
    )


def _canonical_key(symbol: str | None) -> str | None:
    if not symbol:
        return None
    return f"{symbol}_KRX"


def _to_investor_signals(config: KiwoomRestFlowConfig, items: list[KiwoomRestInvestorFlowItem]) -> list[CanonicalInvestorFlowSignal]:
    signals: list[CanonicalInvestorFlowSignal] = []
    for item in items:
        for category, amount, quantity in (
            (CanonicalFlowCategory.FOREIGN, item.foreign_net_amount, item.foreign_net_quantity),
            (CanonicalFlowCategory.INSTITUTION, item.institution_net_amount, item.institution_net_quantity),
            (CanonicalFlowCategory.RETAIL, item.retail_net_amount, item.retail_net_quantity),
        ):
            if amount is None and quantity is None:
                continue
            signals.append(
                CanonicalInvestorFlowSignal(
                    provider_api_id=config.api_id.value,
                    canonical_instrument_key=_canonical_key(item.provider_symbol),
                    provider_symbol=item.provider_symbol,
                    stock_name=item.stock_name,
                    observed_at=item.observed_at,
                    available_at=config.available_at,
                    flow_category=category,
                    net_buy_amount=amount,
                    net_buy_quantity=quantity,
                    confidence_flags=["CONSERVATIVE_FIELD_MAPPING"],
                    source_ref=config.source_ref,
                    quality_flags=["READ_ONLY_ONLY", "TOKEN_REF_ONLY", "KIWOOM_REST_CANONICAL_FLOW"],
                    gap_reason=None,
                )
            )
    return signals


def _to_program_signals(config: KiwoomRestFlowConfig, items: list[KiwoomRestProgramFlowItem]) -> list[CanonicalProgramTradingSignal]:
    return [
        CanonicalProgramTradingSignal(
            provider_api_id=config.api_id.value,
            canonical_instrument_key=_canonical_key(item.provider_symbol),
            provider_symbol=item.provider_symbol,
            stock_name=item.stock_name,
            observed_at=item.observed_at or config.available_at,
            available_at=config.available_at,
            flow_category=CanonicalFlowCategory.PROGRAM,
            program_buy_amount=item.program_buy_amount,
            program_sell_amount=item.program_sell_amount,
            program_net_amount=item.program_net_amount,
            buy_quantity=item.accumulated_trade_quantity,
            confidence_flags=["SCHEMA_PATH_EXPLICIT"] if config.path_hint else ["SCHEMA_GAP"],
            source_ref=config.source_ref,
            quality_flags=["READ_ONLY_ONLY", "TOKEN_REF_ONLY", "KIWOOM_REST_CANONICAL_PROGRAM_FLOW"],
            gap_reason=None if config.path_hint else "PROGRAM_PATH_EVIDENCE_OPTIONAL",
        )
        for item in items
    ]


def build_kiwoom_rest_readonly_flow_adapter(
    config: KiwoomRestFlowConfig,
    *,
    transport: TransportCallable | None = None,
) -> KiwoomRestFlowAdapterResult:
    for audit in config.audit_records:
        validate_kiwoom_rest_flow_metadata_safety(
            {"source_path": audit.source_path, "operator_context": audit.operator_context},
            context="kiwoom rest flow audit",
        )

    gaps: list[KiwoomRestFlowGapEntry] = []
    capability_matrix = _capability_matrix()
    short_entries, lending_entries = _short_lending_report_entries()

    try:
        request = _build_request(config)
    except Exception as exc:
        request = KiwoomRestFlowRequest(
            request_id=f"{config.config_id}-REQUEST",
            path=_path_for_api(config),
            api_id=config.api_id,
            continuation=config.continuation,
            request_headers={
                "api-id": config.api_id.value.lower(),
                "authorization": "Bearer <TOKEN_REF_ONLY>",
                "cont-yn": config.continuation.cont_yn,
                "next-key": config.continuation.next_key,
            },
            request_body={},
        )
        gaps.append(_gap(config.config_id, "REQUEST", "SCHEMA_GAP", "BLOCKING", str(exc)))
        response = KiwoomRestFlowResponse(
            response_id=f"{config.config_id}-RESPONSE",
            api_id=config.api_id,
            return_code=-1,
            return_msg=str(exc),
            continuation=config.continuation,
        )
        investor_signals: list[CanonicalInvestorFlowSignal] = []
        program_signals: list[CanonicalProgramTradingSignal] = []
        readiness = KiwoomRestFlowReadiness.SCHEMA_GAP if config.api_id == KiwoomRestFlowApiId.KA90003 else KiwoomRestFlowReadiness.FUTURE_SUPPORTED
    else:
        if config.available_at is None:
            gaps.append(_gap(config.config_id, "AVAILABLE-AT", "MISSING_AVAILABLE_AT", "WARNING", "available_at is missing"))
        try:
            payload = execute_kiwoom_rest_readonly_flow_transport(
                request,
                transport=transport or (lambda _: config.mocked_response_payload) if config.mocked_response_payload is not None else None,
            )
        except Exception as exc:
            gaps.append(_gap(config.config_id, "TRANSPORT", "NETWORK_TRANSPORT_BLOCKED", "BLOCKING", str(exc)))
            readiness = KiwoomRestFlowReadiness.BLOCKED
            response = KiwoomRestFlowResponse(
                response_id=f"{config.config_id}-RESPONSE",
                api_id=config.api_id,
                return_code=-1,
                return_msg=str(exc),
                continuation=config.continuation,
            )
            investor_signals = []
            program_signals = []
        else:
            try:
                response = _parse_response(config, payload)
            except Exception as exc:
                gaps.append(_gap(config.config_id, "SCHEMA", "SCHEMA_GAP", "BLOCKING", str(exc)))
                readiness = KiwoomRestFlowReadiness.SCHEMA_GAP
                response = KiwoomRestFlowResponse(
                    response_id=f"{config.config_id}-RESPONSE",
                    api_id=config.api_id,
                    return_code=-1,
                    return_msg=str(exc),
                    continuation=config.continuation,
                )
                investor_signals = []
                program_signals = []
            else:
                if response.return_code != 0:
                    gaps.append(_gap(config.config_id, "RETURN-CODE", "DATA_GAP", "WARNING", response.return_msg))
                    readiness = KiwoomRestFlowReadiness.DATA_GAP
                    investor_signals = []
                    program_signals = []
                else:
                    investor_signals = _to_investor_signals(config, response.investor_items)
                    program_signals = _to_program_signals(config, response.program_items)
                    if config.available_at is None:
                        readiness = KiwoomRestFlowReadiness.DATA_GAP
                    elif config.api_id == KiwoomRestFlowApiId.KA10059 and investor_signals:
                        readiness = KiwoomRestFlowReadiness.INVESTOR_FLOW_READY
                    elif config.api_id == KiwoomRestFlowApiId.KA90003 and program_signals:
                        readiness = KiwoomRestFlowReadiness.PROGRAM_FLOW_READY
                    else:
                        readiness = KiwoomRestFlowReadiness.CANONICAL_FLOW_READY

    if investor_signals and readiness == KiwoomRestFlowReadiness.INVESTOR_FLOW_READY:
        readiness = KiwoomRestFlowReadiness.READONLY_ADAPTER_READY
    if any(item.severity == "BLOCKING" for item in gaps) and readiness not in {
        KiwoomRestFlowReadiness.SCHEMA_GAP,
        KiwoomRestFlowReadiness.FUTURE_SUPPORTED,
    }:
        readiness = KiwoomRestFlowReadiness.BLOCKED

    summary = KiwoomRestFlowSummaryReport(
        report_id=f"{config.config_id}-SUMMARY-REPORT",
        readiness=readiness,
        decision_reason=(
            "mocked flow adapter produced canonical flow/program signals"
            if readiness == KiwoomRestFlowReadiness.READONLY_ADAPTER_READY
            else "flow adapter has unresolved data or boundary gaps"
        ),
    )
    request_report = KiwoomRestFlowRequestReport(report_id=f"{config.config_id}-REQUEST-REPORT", request=request)
    mocked_response_report = KiwoomRestFlowMockedResponseReport(
        report_id=f"{config.config_id}-MOCKED-RESPONSE-REPORT",
        response=response,
    )
    investor_report = KiwoomRestCanonicalInvestorFlowReport(
        report_id=f"{config.config_id}-CANONICAL-INVESTOR-FLOW-REPORT",
        signals=investor_signals,
    )
    program_report = KiwoomRestCanonicalProgramFlowReport(
        report_id=f"{config.config_id}-CANONICAL-PROGRAM-FLOW-REPORT",
        signals=program_signals,
    )
    short_lending_report = KiwoomRestShortLendingCapabilityReport(
        report_id=f"{config.config_id}-SHORT-LENDING-CAPABILITY-REPORT",
        short_selling_capabilities=short_entries,
        lending_capabilities=lending_entries,
    )
    capability_matrix_report = KiwoomRestFlowCapabilityMatrixReport(
        report_id=f"{config.config_id}-FLOW-CAPABILITY-MATRIX-REPORT",
        entries=capability_matrix,
    )
    continuation_report = KiwoomRestFlowContinuationReport(
        report_id=f"{config.config_id}-CONTINUATION-REPORT",
        continuation=response.continuation,
        has_more=response.continuation.cont_yn == "Y",
    )
    v7_integration_report = KiwoomRestFlowV7IntegrationReport(
        report_id=f"{config.config_id}-V7-INTEGRATION-REPORT",
        v712_flow_program_ready=bool(investor_signals or program_signals),
        v710_risk_liquidity_hints_ready=bool(investor_signals or program_signals),
        canonical_fields_present=all(signal.available_at is not None for signal in investor_signals + program_signals)
        if (investor_signals or program_signals)
        else False,
    )
    gaps.append(_gap(config.config_id, "REPORT-GENERATED", "READONLY_FLOW_REPORT_GENERATED", "REPORT_ONLY", "kiwoom readonly flow report generated"))
    gap_report = KiwoomRestFlowGapReport(
        gap_report_id=f"{config.config_id}-GAP-REPORT",
        readiness=readiness,
        gap_entries=gaps,
    )
    return KiwoomRestFlowAdapterResult(
        adapter_result_id=f"{config.config_id}-ADAPTER-RESULT",
        request=request,
        summary_report=summary,
        request_report=request_report,
        mocked_response_report=mocked_response_report,
        canonical_investor_flow_report=investor_report,
        canonical_program_flow_report=program_report,
        short_lending_capability_report=short_lending_report,
        flow_capability_matrix_report=capability_matrix_report,
        continuation_report=continuation_report,
        safety_report=config.safety_report,
        v7_integration_report=v7_integration_report,
        gap_report=gap_report,
        audit_records=config.audit_records,
    )
