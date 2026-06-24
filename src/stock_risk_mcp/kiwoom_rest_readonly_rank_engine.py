from __future__ import annotations

from stock_risk_mcp.kiwoom_rest_readonly_rank_client import (
    TransportCallable,
    execute_kiwoom_rest_readonly_rank_transport,
)
from stock_risk_mcp.kiwoom_rest_readonly_rank_guard import validate_kiwoom_rest_rank_metadata_safety
from stock_risk_mcp.kiwoom_rest_readonly_rank_models import (
    CanonicalOutlierCategory,
    CanonicalOutlierMomentumSignal,
    CanonicalRankSignal,
    KiwoomRestCanonicalOutlierSignalReport,
    KiwoomRestCanonicalRankSignalReport,
    KiwoomRestRankAdapterResult,
    KiwoomRestRankApiId,
    KiwoomRestRankConfig,
    KiwoomRestRankContinuation,
    KiwoomRestRankContinuationReport,
    KiwoomRestRankGapEntry,
    KiwoomRestRankGapReport,
    KiwoomRestRankItem,
    KiwoomRestRankMockedResponseReport,
    KiwoomRestRankReadiness,
    KiwoomRestRankRequest,
    KiwoomRestRankRequestReport,
    KiwoomRestRankResponse,
    KiwoomRestRankSummaryReport,
    KiwoomRestRankV7IntegrationReport,
)


SUPPORTED_REQUEST_API_IDS = {
    KiwoomRestRankApiId.KA00198,
    KiwoomRestRankApiId.KA10023,
    KiwoomRestRankApiId.KA10030,
    KiwoomRestRankApiId.KA10032,
}
FUTURE_SUPPORTED_API_IDS = {
    KiwoomRestRankApiId.KA10019,
    KiwoomRestRankApiId.KA10027,
    KiwoomRestRankApiId.KA10098,
}


def _gap(config_id: str, suffix: str, category: str, severity: str, message: str) -> KiwoomRestRankGapEntry:
    return KiwoomRestRankGapEntry(
        gap_id=f"{config_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def _category_for_api(api_id: KiwoomRestRankApiId) -> CanonicalOutlierCategory:
    return {
        KiwoomRestRankApiId.KA00198: CanonicalOutlierCategory.REALTIME_INQUIRY_RANK,
        KiwoomRestRankApiId.KA10023: CanonicalOutlierCategory.VOLUME_SURGE,
        KiwoomRestRankApiId.KA10030: CanonicalOutlierCategory.VOLUME_RANK,
        KiwoomRestRankApiId.KA10032: CanonicalOutlierCategory.TRADING_VALUE_RANK,
        KiwoomRestRankApiId.KA10019: CanonicalOutlierCategory.PRICE_SURGE,
        KiwoomRestRankApiId.KA10098: CanonicalOutlierCategory.AFTER_HOURS_SURGE,
    }.get(api_id, CanonicalOutlierCategory.UNKNOWN)


def _rank_type_for_api(api_id: KiwoomRestRankApiId) -> str:
    return _category_for_api(api_id).value


def _path_for_api(api_id: KiwoomRestRankApiId) -> str:
    if api_id == KiwoomRestRankApiId.KA00198:
        return "/api/dostk/stkinfo"
    return "/api/dostk/rkinfo"


def _build_request(config: KiwoomRestRankConfig) -> KiwoomRestRankRequest:
    if config.api_id in FUTURE_SUPPORTED_API_IDS:
        raise ValueError(f"{config.api_id.value.lower()} is future supported only and remains schema_gap for request builder")
    if config.api_id not in SUPPORTED_REQUEST_API_IDS:
        raise ValueError("account/order api id is blocked")

    body_by_api = {
        KiwoomRestRankApiId.KA00198: {"qry_tp": config.qry_tp},
        KiwoomRestRankApiId.KA10023: {
            "mrkt_tp": config.mrkt_tp,
            "sort_tp": config.sort_tp,
            "tm_tp": config.tm_tp,
            "trde_qty_tp": config.trde_qty_tp,
            "tm": config.tm,
            "stk_cnd": config.stk_cnd,
            "pric_tp": config.pric_tp,
            "stex_tp": config.stex_tp,
        },
        KiwoomRestRankApiId.KA10030: {
            "mrkt_tp": config.mrkt_tp,
            "sort_tp": config.sort_tp,
            "mang_stk_incls": config.mang_stk_incls,
            "crd_tp": config.crd_tp,
            "trde_qty_tp": config.trde_qty_tp,
            "pric_tp": config.pric_tp,
            "stex_tp": config.stex_tp,
        },
        KiwoomRestRankApiId.KA10032: {
            "mrkt_tp": config.mrkt_tp,
            "mang_stk_incls": config.mang_stk_incls,
            "stex_tp": config.stex_tp,
        },
    }
    api_id_lower = config.api_id.value.lower()
    return KiwoomRestRankRequest(
        request_id=f"{config.config_id}-REQUEST",
        path=_path_for_api(config.api_id),
        api_id=config.api_id,
        continuation=config.continuation,
        request_headers={
            "api-id": api_id_lower,
            "authorization": "Bearer <TOKEN_REF_ONLY>",
            "cont-yn": config.continuation.cont_yn,
            "next-key": config.continuation.next_key,
        },
        request_body=body_by_api[config.api_id],
    )


def build_kiwoom_rest_realtime_inquiry_rank_request(config: KiwoomRestRankConfig) -> KiwoomRestRankRequest:
    if config.api_id != KiwoomRestRankApiId.KA00198:
        raise ValueError("realtime inquiry rank request requires ka00198")
    return _build_request(config)


def build_kiwoom_rest_volume_surge_rank_request(config: KiwoomRestRankConfig) -> KiwoomRestRankRequest:
    if config.api_id != KiwoomRestRankApiId.KA10023:
        raise ValueError("volume surge rank request requires ka10023")
    return _build_request(config)


def build_kiwoom_rest_today_volume_rank_request(config: KiwoomRestRankConfig) -> KiwoomRestRankRequest:
    if config.api_id != KiwoomRestRankApiId.KA10030:
        raise ValueError("today volume rank request requires ka10030")
    return _build_request(config)


def build_kiwoom_rest_trading_value_rank_request(config: KiwoomRestRankConfig) -> KiwoomRestRankRequest:
    if config.api_id != KiwoomRestRankApiId.KA10032:
        raise ValueError("trading value rank request requires ka10032")
    return _build_request(config)


def _response_rows(payload: dict[str, object], api_id: KiwoomRestRankApiId):
    keys = {
        KiwoomRestRankApiId.KA00198: ("item_inq_rank",),
        KiwoomRestRankApiId.KA10023: ("vol_surge_rank", "trde_qty_surge", "stk_list"),
        KiwoomRestRankApiId.KA10030: ("trde_qty_upper", "today_volume_rank", "stk_list"),
        KiwoomRestRankApiId.KA10032: ("trde_prica_upper", "trading_value_rank", "stk_list"),
    }[api_id]
    for key in keys:
        rows = payload.get(key)
        if rows is not None:
            return rows
    return None


def _symbol(row: dict[str, object]) -> str:
    return str(row.get("stk_cd") or row.get("symbol") or "").strip().upper()


def _stock_name(row: dict[str, object]) -> str:
    return str(row.get("stk_nm") or row.get("stock_name") or "").strip()


def _observed_at(row: dict[str, object]) -> str:
    dt = str(row.get("dt") or "").strip()
    tm = str(row.get("tm") or "").strip()
    if dt and tm:
        return f"{dt}{tm}"
    if dt:
        return dt
    return str(row.get("observed_at") or "").strip()


def _parse_items(config: KiwoomRestRankConfig, payload: dict[str, object]) -> list[KiwoomRestRankItem]:
    rows = _response_rows(payload, config.api_id)
    if not isinstance(rows, list):
        raise ValueError("rank response rows are missing")
    items: list[KiwoomRestRankItem] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("rank row must be an object")
        gap_reason = None
        relative_volume = row.get("rel_vol") or row.get("relative_volume")
        if relative_volume in (None, ""):
            gap_reason = "RELATIVE_VOLUME_UNAVAILABLE"
        price_value = row.get("past_curr_prc")
        if price_value is None:
            price_value = row.get("cur_prc")
        price_change = row.get("pred_pre")
        percent_change = row.get("base_comp_chgr")
        if percent_change is None:
            percent_change = row.get("prev_base_chgr")
        if percent_change is None:
            percent_change = row.get("flu_rt")
        volume = row.get("trde_qty")
        trading_value = row.get("trde_prica")
        if trading_value is None:
            trading_value = row.get("trde_prica_amt")
        previous_rank = row.get("pred_rank")
        rank_change = row.get("rank_chg")
        if previous_rank is None and rank_change not in (None, "") and row.get("now_rank") not in (None, ""):
            previous_rank = int(float(str(row.get("now_rank")).replace(",", ""))) + int(float(str(rank_change).replace(",", "")))
        items.append(
            KiwoomRestRankItem(
                provider_symbol=_symbol(row),
                stock_name=_stock_name(row),
                observed_at=_observed_at(row),
                rank=row.get("bigd_rank") or row.get("now_rank") or row.get("rank"),
                previous_rank=previous_rank,
                rank_change=rank_change,
                rank_change_sign=row.get("rank_chg_sign"),
                price=price_value,
                price_change=price_change,
                percent_change=percent_change,
                volume=volume,
                trading_value=trading_value,
                relative_volume=relative_volume,
                liquidity_evidence_flag=bool(volume not in (None, "") and trading_value not in (None, "")),
                outlier_category=_category_for_api(config.api_id),
                gap_reason=gap_reason,
            )
        )
    return items


def _parse_response(config: KiwoomRestRankConfig, payload: dict[str, object]) -> KiwoomRestRankResponse:
    if not isinstance(payload, dict):
        raise ValueError("mocked response payload must be an object")
    continuation = KiwoomRestRankContinuation(
        cont_yn=(payload.get("cont_yn") or payload.get("contYn") or payload.get("cont-yn") or "N"),
        next_key=(payload.get("next_key") or payload.get("nextKey") or payload.get("next-key") or ""),
    )
    return_code = payload.get("return_code")
    return_msg = payload.get("return_msg")
    if return_code is None or return_msg is None:
        raise ValueError("response return_code/return_msg missing")
    items = _parse_items(config, payload) if int(return_code) == 0 else []
    return KiwoomRestRankResponse(
        response_id=f"{config.config_id}-RESPONSE",
        api_id=config.api_id,
        return_code=int(return_code),
        return_msg=str(return_msg),
        items=items,
        continuation=continuation,
        raw_payload_redacted=True,
    )


def _canonical_key(symbol: str) -> str:
    return f"{symbol}_KRX"


def _to_canonical_rank(config: KiwoomRestRankConfig, items: list[KiwoomRestRankItem]) -> list[CanonicalRankSignal]:
    return [
        CanonicalRankSignal(
            provider_api_id=config.api_id.value,
            canonical_instrument_key=_canonical_key(item.provider_symbol),
            provider_symbol=item.provider_symbol,
            stock_name=item.stock_name,
            observed_at=item.observed_at,
            available_at=config.available_at,
            rank_type=_rank_type_for_api(config.api_id),
            rank=item.rank,
            previous_rank=item.previous_rank,
            rank_change=item.rank_change,
            price=item.price,
            price_change=item.price_change,
            percent_change=item.percent_change,
            volume=item.volume,
            trading_value=item.trading_value,
            relative_volume=item.relative_volume,
            liquidity_evidence_flag=item.liquidity_evidence_flag,
            outlier_category=item.outlier_category,
            source_ref=config.source_ref,
            quality_flags=["READ_ONLY_ONLY", "TOKEN_REF_ONLY", "KIWOOM_REST_CANONICAL_RANK"],
            stale_flag=False,
            gap_reason=item.gap_reason,
        )
        for item in items
    ]


def _to_canonical_outlier(config: KiwoomRestRankConfig, items: list[KiwoomRestRankItem]) -> list[CanonicalOutlierMomentumSignal]:
    return [
        CanonicalOutlierMomentumSignal(
            provider_api_id=config.api_id.value,
            canonical_instrument_key=_canonical_key(item.provider_symbol),
            provider_symbol=item.provider_symbol,
            stock_name=item.stock_name,
            observed_at=item.observed_at,
            available_at=config.available_at,
            rank_type=_rank_type_for_api(config.api_id),
            rank=item.rank,
            previous_rank=item.previous_rank,
            rank_change=item.rank_change,
            price=item.price,
            price_change=item.price_change,
            percent_change=item.percent_change,
            volume=item.volume,
            trading_value=item.trading_value,
            relative_volume=item.relative_volume,
            liquidity_evidence_flag=item.liquidity_evidence_flag,
            outlier_category=item.outlier_category,
            source_ref=config.source_ref,
            quality_flags=["READ_ONLY_ONLY", "TOKEN_REF_ONLY", "KIWOOM_REST_CANONICAL_OUTLIER"],
            stale_flag=False,
            gap_reason=item.gap_reason,
        )
        for item in items
    ]


def build_kiwoom_rest_readonly_rank_adapter(
    config: KiwoomRestRankConfig,
    *,
    transport: TransportCallable | None = None,
) -> KiwoomRestRankAdapterResult:
    for audit in config.audit_records:
        validate_kiwoom_rest_rank_metadata_safety(
            {"source_path": audit.source_path, "operator_context": audit.operator_context},
            context="kiwoom rest rank audit",
        )

    gaps: list[KiwoomRestRankGapEntry] = []
    try:
        request = _build_request(config)
    except Exception as exc:
        gaps.append(_gap(config.config_id, "REQUEST", "SCHEMA_GAP", "BLOCKING", str(exc)))
        request = KiwoomRestRankRequest(
            request_id=f"{config.config_id}-REQUEST",
            path=_path_for_api(config.api_id),
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
        response = KiwoomRestRankResponse(
            response_id=f"{config.config_id}-RESPONSE",
            api_id=config.api_id,
            return_code=-1,
            return_msg=str(exc),
            items=[],
            continuation=config.continuation,
        )
        canonical_rank_signals: list[CanonicalRankSignal] = []
        canonical_outlier_signals: list[CanonicalOutlierMomentumSignal] = []
        readiness = KiwoomRestRankReadiness.SCHEMA_GAP
    else:
        if config.available_at is None:
            gaps.append(_gap(config.config_id, "AVAILABLE-AT", "MISSING_AVAILABLE_AT", "WARNING", "available_at is missing"))
        try:
            payload = execute_kiwoom_rest_readonly_rank_transport(
                request,
                transport=transport or (lambda _: config.mocked_response_payload) if config.mocked_response_payload is not None else None,
            )
        except Exception as exc:
            gaps.append(_gap(config.config_id, "TRANSPORT", "NETWORK_TRANSPORT_BLOCKED", "BLOCKING", str(exc)))
            readiness = KiwoomRestRankReadiness.BLOCKED
            response = KiwoomRestRankResponse(
                response_id=f"{config.config_id}-RESPONSE",
                api_id=config.api_id,
                return_code=-1,
                return_msg=str(exc),
                items=[],
                continuation=config.continuation,
            )
            canonical_rank_signals = []
            canonical_outlier_signals = []
        else:
            try:
                response = _parse_response(config, payload)
            except Exception as exc:
                gaps.append(_gap(config.config_id, "SCHEMA", "SCHEMA_GAP", "BLOCKING", str(exc)))
                readiness = KiwoomRestRankReadiness.SCHEMA_GAP
                response = KiwoomRestRankResponse(
                    response_id=f"{config.config_id}-RESPONSE",
                    api_id=config.api_id,
                    return_code=-1,
                    return_msg=str(exc),
                    items=[],
                    continuation=config.continuation,
                )
                canonical_rank_signals = []
                canonical_outlier_signals = []
            else:
                if response.return_code != 0:
                    gaps.append(_gap(config.config_id, "RETURN-CODE", "DATA_GAP", "WARNING", response.return_msg))
                    readiness = KiwoomRestRankReadiness.DATA_GAP
                    canonical_rank_signals = []
                    canonical_outlier_signals = []
                else:
                    canonical_rank_signals = _to_canonical_rank(config, response.items)
                    canonical_outlier_signals = _to_canonical_outlier(config, response.items)
                    if config.available_at is None:
                        readiness = KiwoomRestRankReadiness.DATA_GAP
                    elif config.api_id == KiwoomRestRankApiId.KA00198:
                        readiness = KiwoomRestRankReadiness.CANONICAL_RANK_READY
                    elif config.api_id in {KiwoomRestRankApiId.KA10023, KiwoomRestRankApiId.KA10030, KiwoomRestRankApiId.KA10032}:
                        readiness = KiwoomRestRankReadiness.CANONICAL_OUTLIER_READY
                    else:
                        readiness = KiwoomRestRankReadiness.READONLY_ADAPTER_READY

    if canonical_rank_signals and canonical_outlier_signals and readiness in {
        KiwoomRestRankReadiness.CANONICAL_RANK_READY,
        KiwoomRestRankReadiness.CANONICAL_OUTLIER_READY,
    }:
        readiness = KiwoomRestRankReadiness.READONLY_ADAPTER_READY
    if any(item.severity == "BLOCKING" for item in gaps) and readiness != KiwoomRestRankReadiness.SCHEMA_GAP:
        readiness = KiwoomRestRankReadiness.BLOCKED

    summary = KiwoomRestRankSummaryReport(
        report_id=f"{config.config_id}-SUMMARY-REPORT",
        readiness=readiness,
        decision_reason=(
            "mocked rank adapter produced canonical rank and outlier signals"
            if readiness == KiwoomRestRankReadiness.READONLY_ADAPTER_READY
            else "rank adapter has unresolved data or boundary gaps"
        ),
    )
    request_report = KiwoomRestRankRequestReport(
        report_id=f"{config.config_id}-REQUEST-REPORT",
        request=request,
    )
    mocked_response_report = KiwoomRestRankMockedResponseReport(
        report_id=f"{config.config_id}-MOCKED-RESPONSE-REPORT",
        response=response,
    )
    canonical_rank_report = KiwoomRestCanonicalRankSignalReport(
        report_id=f"{config.config_id}-CANONICAL-RANK-REPORT",
        signals=canonical_rank_signals,
    )
    canonical_outlier_report = KiwoomRestCanonicalOutlierSignalReport(
        report_id=f"{config.config_id}-CANONICAL-OUTLIER-REPORT",
        signals=canonical_outlier_signals,
    )
    continuation_report = KiwoomRestRankContinuationReport(
        report_id=f"{config.config_id}-CONTINUATION-REPORT",
        continuation=response.continuation,
        has_more=response.continuation.cont_yn == "Y",
    )
    v7_integration_report = KiwoomRestRankV7IntegrationReport(
        report_id=f"{config.config_id}-V7-INTEGRATION-REPORT",
        v712_breadth_routing_ready=bool(canonical_outlier_signals),
        v710_price_liquidity_hints_ready=all(
            signal.price is not None and signal.volume is not None for signal in canonical_outlier_signals
        )
        if canonical_outlier_signals
        else False,
        canonical_fields_present=all(signal.available_at is not None for signal in canonical_rank_signals + canonical_outlier_signals)
        if (canonical_rank_signals or canonical_outlier_signals)
        else False,
        future_supported_api_ids=sorted(item.value for item in FUTURE_SUPPORTED_API_IDS),
        request_builder_ready_api_ids=sorted(item.value for item in SUPPORTED_REQUEST_API_IDS),
    )
    gaps.append(_gap(config.config_id, "REPORT-GENERATED", "READONLY_RANK_REPORT_GENERATED", "REPORT_ONLY", "kiwoom readonly rank report generated"))
    gap_report = KiwoomRestRankGapReport(
        gap_report_id=f"{config.config_id}-GAP-REPORT",
        readiness=readiness,
        gap_entries=gaps,
    )
    return KiwoomRestRankAdapterResult(
        adapter_result_id=f"{config.config_id}-ADAPTER-RESULT",
        request=request,
        summary_report=summary,
        request_report=request_report,
        mocked_response_report=mocked_response_report,
        canonical_rank_report=canonical_rank_report,
        canonical_outlier_report=canonical_outlier_report,
        continuation_report=continuation_report,
        safety_report=config.safety_report,
        v7_integration_report=v7_integration_report,
        gap_report=gap_report,
        audit_records=config.audit_records,
    )
