from __future__ import annotations

from datetime import datetime

from stock_risk_mcp.kiwoom_rest_readonly_chart_client import (
    TransportCallable,
    execute_kiwoom_rest_readonly_chart_transport,
)
from stock_risk_mcp.kiwoom_rest_readonly_chart_guard import (
    validate_kiwoom_rest_chart_metadata_safety,
)
from stock_risk_mcp.kiwoom_rest_readonly_chart_models import (
    CanonicalOHLCVRecord,
    KiwoomRestChartAdapterResult,
    KiwoomRestChartApiId,
    KiwoomRestChartBar,
    KiwoomRestChartCanonicalOhlcvReport,
    KiwoomRestChartConfig,
    KiwoomRestChartContinuation,
    KiwoomRestChartContinuationReport,
    KiwoomRestChartGapEntry,
    KiwoomRestChartGapReport,
    KiwoomRestChartIntegrationCompatibilityReport,
    KiwoomRestChartMockedResponseReport,
    KiwoomRestChartReadiness,
    KiwoomRestChartRequest,
    KiwoomRestChartRequestReport,
    KiwoomRestChartResponse,
    KiwoomRestChartSummaryReport,
)


def _gap(config_id: str, suffix: str, category: str, severity: str, message: str) -> KiwoomRestChartGapEntry:
    return KiwoomRestChartGapEntry(
        gap_id=f"{config_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def build_kiwoom_rest_daily_chart_request(config: KiwoomRestChartConfig) -> KiwoomRestChartRequest:
    if config.api_id != KiwoomRestChartApiId.KA10081:
        raise ValueError("daily chart request requires ka10081")
    return KiwoomRestChartRequest(
        request_id=f"{config.config_id}-REQUEST",
        api_id=config.api_id,
        provider_symbol=config.provider_symbol,
        base_dt=config.base_dt,
        upd_stkpc_tp=config.upd_stkpc_tp,
        continuation=config.continuation,
        request_headers={
            "api-id": "ka10081",
            "authorization": "Bearer <TOKEN_REF_ONLY>",
            "cont-yn": config.continuation.cont_yn,
            "next-key": config.continuation.next_key,
        },
        request_body={
            "stk_cd": config.provider_symbol,
            "base_dt": config.base_dt,
            "upd_stkpc_tp": config.upd_stkpc_tp,
        },
    )


def build_kiwoom_rest_minute_chart_request(config: KiwoomRestChartConfig) -> KiwoomRestChartRequest:
    if config.api_id != KiwoomRestChartApiId.KA10080:
        raise ValueError("minute chart request requires ka10080")
    return KiwoomRestChartRequest(
        request_id=f"{config.config_id}-REQUEST",
        api_id=config.api_id,
        provider_symbol=config.provider_symbol,
        base_dt=config.base_dt,
        upd_stkpc_tp=config.upd_stkpc_tp,
        tic_scope=config.tic_scope,
        continuation=config.continuation,
        request_headers={
            "api-id": "ka10080",
            "authorization": "Bearer <TOKEN_REF_ONLY>",
            "cont-yn": config.continuation.cont_yn,
            "next-key": config.continuation.next_key,
        },
        request_body={
            "stk_cd": config.provider_symbol,
            "tic_scope": config.tic_scope,
            "upd_stkpc_tp": config.upd_stkpc_tp,
            "base_dt": config.base_dt,
        },
    )


def _build_request(config: KiwoomRestChartConfig) -> KiwoomRestChartRequest:
    if config.api_id == KiwoomRestChartApiId.KA10081:
        return build_kiwoom_rest_daily_chart_request(config)
    if config.api_id == KiwoomRestChartApiId.KA10080:
        return build_kiwoom_rest_minute_chart_request(config)
    raise ValueError("unsupported read-only chart api id")


def _parse_bars(config: KiwoomRestChartConfig, payload: dict[str, object]) -> list[KiwoomRestChartBar]:
    body_key = "stk_min_pole_chart_qry" if config.api_id == KiwoomRestChartApiId.KA10080 else "stk_dt_pole_chart_qry"
    rows = payload.get(body_key)
    if rows is None and config.api_id == KiwoomRestChartApiId.KA10081:
        rows = payload.get("stk_day_pole_chart_qry")
    if not isinstance(rows, list):
        raise ValueError("chart response rows are missing")
    bars: list[KiwoomRestChartBar] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("chart row must be an object")
        observed_key = row.get("cntr_tm") or row.get("dt") or row.get("date") or row.get("bsop_date")
        volume_value = row.get("trde_qty")
        if volume_value is None:
            volume_value = row.get("acc_trde_qty")
        bars.append(
            KiwoomRestChartBar(
                provider_symbol=payload.get("stk_cd", config.provider_symbol),
                observed_at=observed_key,
                open_price=row.get("open_pric"),
                high_price=row.get("high_pric"),
                low_price=row.get("low_pric"),
                close_price=row.get("cur_prc"),
                volume=volume_value,
                adjusted_flag=config.upd_stkpc_tp == "1",
                previous_close_diff=row.get("pred_pre"),
                previous_close_sign_code=row.get("pred_pre_sig"),
            )
        )
    return bars


def _parse_response(config: KiwoomRestChartConfig, payload: dict[str, object]) -> KiwoomRestChartResponse:
    if not isinstance(payload, dict):
        raise ValueError("mocked response payload must be an object")
    continuation = KiwoomRestChartContinuation(
        cont_yn=(payload.get("cont_yn") or payload.get("contYn") or payload.get("cont-yn") or "N"),
        next_key=(payload.get("next_key") or payload.get("nextKey") or payload.get("next-key") or ""),
    )
    return_code = payload.get("return_code")
    return_msg = payload.get("return_msg")
    if return_code is None or return_msg is None:
        raise ValueError("response return_code/return_msg missing")
    bars = _parse_bars(config, payload) if int(return_code) == 0 else []
    return KiwoomRestChartResponse(
        response_id=f"{config.config_id}-RESPONSE",
        api_id=config.api_id,
        provider_symbol=payload.get("stk_cd", config.provider_symbol),
        return_code=int(return_code),
        return_msg=str(return_msg),
        bars=bars,
        continuation=continuation,
        raw_payload_redacted=True,
    )


def _to_canonical(config: KiwoomRestChartConfig, bars: list[KiwoomRestChartBar]) -> list[CanonicalOHLCVRecord]:
    timeframe = "1D" if config.api_id == KiwoomRestChartApiId.KA10081 else "1M"
    return [
        CanonicalOHLCVRecord(
            provider_api_id=config.api_id.value,
            canonical_instrument_key=config.canonical_instrument_key,
            provider_symbol=bar.provider_symbol,
            timeframe=timeframe,
            observed_at=bar.observed_at,
            available_at=config.available_at,
            open=bar.open_price,
            high=bar.high_price,
            low=bar.low_price,
            close=bar.close_price,
            volume=bar.volume,
            source_ref=config.source_ref,
            quality_flags=["READ_ONLY_ONLY", "TOKEN_REF_ONLY", "KIWOOM_REST_CANONICAL"],
            stale_flag=False,
            gap_reason=None,
            adjusted_flag=bar.adjusted_flag,
        )
        for bar in bars
    ]


def build_kiwoom_rest_readonly_chart_adapter(
    config: KiwoomRestChartConfig,
    *,
    transport: TransportCallable | None = None,
) -> KiwoomRestChartAdapterResult:
    for audit in config.audit_records:
        validate_kiwoom_rest_chart_metadata_safety(
            {"source_path": audit.source_path, "operator_context": audit.operator_context},
            context="kiwoom rest chart audit",
        )

    gaps: list[KiwoomRestChartGapEntry] = []
    request = _build_request(config)
    if config.available_at is None:
        gaps.append(_gap(config.config_id, "AVAILABLE-AT", "MISSING_AVAILABLE_AT", "WARNING", "available_at is missing"))

    try:
        payload = execute_kiwoom_rest_readonly_chart_transport(
            request,
            transport=transport or (lambda _: config.mocked_response_payload) if config.mocked_response_payload is not None else None,
        )
    except Exception as exc:
        gaps.append(_gap(config.config_id, "TRANSPORT", "NETWORK_TRANSPORT_BLOCKED", "BLOCKING", str(exc)))
        readiness = KiwoomRestChartReadiness.BLOCKED
        response = KiwoomRestChartResponse(
            response_id=f"{config.config_id}-RESPONSE",
            api_id=config.api_id,
            provider_symbol=config.provider_symbol,
            return_code=-1,
            return_msg=str(exc),
            bars=[],
            continuation=config.continuation,
            raw_payload_redacted=True,
        )
        canonical_records: list[CanonicalOHLCVRecord] = []
    else:
        try:
            response = _parse_response(config, payload)
        except Exception as exc:
            gaps.append(_gap(config.config_id, "SCHEMA", "SCHEMA_GAP", "BLOCKING", str(exc)))
            readiness = KiwoomRestChartReadiness.SCHEMA_GAP
            response = KiwoomRestChartResponse(
                response_id=f"{config.config_id}-RESPONSE",
                api_id=config.api_id,
                provider_symbol=config.provider_symbol,
                return_code=-1,
                return_msg=str(exc),
                bars=[],
                continuation=config.continuation,
                raw_payload_redacted=True,
            )
            canonical_records = []
        else:
            if response.return_code != 0:
                gaps.append(_gap(config.config_id, "RETURN-CODE", "DATA_GAP", "WARNING", response.return_msg))
                readiness = KiwoomRestChartReadiness.DATA_GAP
                canonical_records = []
            else:
                canonical_records = _to_canonical(config, response.bars)
                readiness = KiwoomRestChartReadiness.READONLY_ADAPTER_READY if config.available_at is not None else KiwoomRestChartReadiness.DATA_GAP

    if any(item.severity == "BLOCKING" for item in gaps) and readiness != KiwoomRestChartReadiness.SCHEMA_GAP:
        readiness = KiwoomRestChartReadiness.BLOCKED

    summary = KiwoomRestChartSummaryReport(
        report_id=f"{config.config_id}-SUMMARY-REPORT",
        readiness=readiness,
        decision_reason=(
            "mocked chart adapter produced canonical ohlcv"
            if readiness == KiwoomRestChartReadiness.READONLY_ADAPTER_READY
            else "chart adapter has unresolved data or boundary gaps"
        ),
    )
    request_report = KiwoomRestChartRequestReport(
        report_id=f"{config.config_id}-REQUEST-REPORT",
        request=request,
    )
    mocked_response_report = KiwoomRestChartMockedResponseReport(
        report_id=f"{config.config_id}-MOCKED-RESPONSE-REPORT",
        response=response,
    )
    canonical_report = KiwoomRestChartCanonicalOhlcvReport(
        report_id=f"{config.config_id}-CANONICAL-OHLCV-REPORT",
        records=canonical_records,
    )
    continuation_report = KiwoomRestChartContinuationReport(
        report_id=f"{config.config_id}-CONTINUATION-REPORT",
        continuation=response.continuation,
        has_more=response.continuation.cont_yn == "Y",
    )
    integration_report = KiwoomRestChartIntegrationCompatibilityReport(
        report_id=f"{config.config_id}-INTEGRATION-COMPATIBILITY-REPORT",
        v79_market_data_ready=bool(canonical_records),
        v710_price_data_ready=bool(canonical_records),
        canonical_fields_present=all(item.available_at is not None for item in canonical_records) if canonical_records else False,
        timeframe_supported=bool(canonical_records),
    )
    gaps.append(_gap(config.config_id, "REPORT-GENERATED", "READONLY_CHART_REPORT_GENERATED", "REPORT_ONLY", "kiwoom readonly chart report generated"))
    gap_report = KiwoomRestChartGapReport(
        gap_report_id=f"{config.config_id}-GAP-REPORT",
        readiness=readiness,
        gap_entries=gaps,
    )
    return KiwoomRestChartAdapterResult(
        adapter_result_id=f"{config.config_id}-ADAPTER-RESULT",
        request=request,
        summary_report=summary,
        request_report=request_report,
        mocked_response_report=mocked_response_report,
        canonical_ohlcv_report=canonical_report,
        continuation_report=continuation_report,
        safety_report=config.safety_report,
        integration_compatibility_report=integration_report,
        gap_report=gap_report,
        audit_records=config.audit_records,
    )
