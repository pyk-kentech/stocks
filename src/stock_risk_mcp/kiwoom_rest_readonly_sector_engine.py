from __future__ import annotations

from stock_risk_mcp.kiwoom_rest_readonly_sector_client import (
    TransportCallable,
    execute_kiwoom_rest_readonly_sector_transport,
)
from stock_risk_mcp.kiwoom_rest_readonly_sector_guard import validate_kiwoom_rest_sector_metadata_safety
from stock_risk_mcp.kiwoom_rest_readonly_sector_models import (
    CanonicalEtfTrendSignal,
    CanonicalSectorCapabilitySignal,
    CanonicalThemeLeadershipSignal,
    CanonicalThemeMembershipSignal,
    KiwoomRestCanonicalEtfTrendReport,
    KiwoomRestCanonicalThemeLeadershipReport,
    KiwoomRestCanonicalThemeMembershipReport,
    KiwoomRestEtfTrendItem,
    KiwoomRestSectorAdapterResult,
    KiwoomRestSectorApiId,
    KiwoomRestSectorConfig,
    KiwoomRestSectorContinuation,
    KiwoomRestSectorContinuationReport,
    KiwoomRestSectorEtfCapabilityMatrixReport,
    KiwoomRestSectorGapEntry,
    KiwoomRestSectorGapReport,
    KiwoomRestSectorMockedResponseReport,
    KiwoomRestSectorReadiness,
    KiwoomRestSectorRequest,
    KiwoomRestSectorRequestReport,
    KiwoomRestSectorResponse,
    KiwoomRestSectorSummaryReport,
    KiwoomRestSectorV7IntegrationReport,
    KiwoomRestThemeComponentItem,
    KiwoomRestThemeGroupItem,
)


CAPABILITY_GROUPS = {
    KiwoomRestSectorApiId.KA20001: "SECTOR",
    KiwoomRestSectorApiId.KA20002: "SECTOR",
    KiwoomRestSectorApiId.KA20003: "SECTOR",
    KiwoomRestSectorApiId.KA20004: "SECTOR",
    KiwoomRestSectorApiId.KA20005: "SECTOR",
    KiwoomRestSectorApiId.KA20006: "SECTOR",
    KiwoomRestSectorApiId.KA20007: "SECTOR",
    KiwoomRestSectorApiId.KA20008: "SECTOR",
    KiwoomRestSectorApiId.KA20009: "SECTOR",
    KiwoomRestSectorApiId.KA20019: "SECTOR",
    KiwoomRestSectorApiId.KA40001: "ETF",
    KiwoomRestSectorApiId.KA40002: "ETF",
    KiwoomRestSectorApiId.KA40003: "ETF",
    KiwoomRestSectorApiId.KA40004: "ETF",
    KiwoomRestSectorApiId.KA40006: "ETF",
    KiwoomRestSectorApiId.KA40007: "ETF",
    KiwoomRestSectorApiId.KA40008: "ETF",
    KiwoomRestSectorApiId.KA40009: "ETF",
    KiwoomRestSectorApiId.KA40010: "ETF",
    KiwoomRestSectorApiId.KA90001: "THEME",
    KiwoomRestSectorApiId.KA90002: "THEME",
}

READY_BUILDERS = {
    KiwoomRestSectorApiId.KA90001,
    KiwoomRestSectorApiId.KA90002,
    KiwoomRestSectorApiId.KA40003,
}


def _gap(config_id: str, suffix: str, category: str, severity: str, message: str) -> KiwoomRestSectorGapEntry:
    return KiwoomRestSectorGapEntry(
        gap_id=f"{config_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def _capability_readiness(api_id: KiwoomRestSectorApiId) -> KiwoomRestSectorReadiness:
    if api_id == KiwoomRestSectorApiId.KA90001:
        return KiwoomRestSectorReadiness.THEME_LEADERSHIP_READY
    if api_id == KiwoomRestSectorApiId.KA90002:
        return KiwoomRestSectorReadiness.THEME_MEMBERSHIP_READY
    if api_id == KiwoomRestSectorApiId.KA40003:
        return KiwoomRestSectorReadiness.ETF_TREND_READY
    return KiwoomRestSectorReadiness.FUTURE_SUPPORTED


def _path_for_api(api_id: KiwoomRestSectorApiId) -> str | None:
    if api_id in {KiwoomRestSectorApiId.KA90001, KiwoomRestSectorApiId.KA90002}:
        return "/api/dostk/thme"
    if api_id == KiwoomRestSectorApiId.KA40003:
        return "/api/dostk/etf"
    return None


def _build_request(config: KiwoomRestSectorConfig) -> KiwoomRestSectorRequest:
    if config.api_id == KiwoomRestSectorApiId.KA90001:
        return KiwoomRestSectorRequest(
            request_id=f"{config.config_id}-REQUEST",
            path="/api/dostk/thme",
            api_id=config.api_id,
            continuation=config.continuation,
            request_headers={
                "api-id": "ka90001",
                "authorization": "Bearer <TOKEN_REF_ONLY>",
                "cont-yn": config.continuation.cont_yn,
                "next-key": config.continuation.next_key,
            },
            request_body={
                "qry_tp": config.qry_tp,
                "stk_cd": config.provider_symbol or "",
                "date_tp": config.date_tp,
                "thema_nm": config.theme_name or "",
                "flu_pl_amt_tp": config.flu_pl_amt_tp,
                "stex_tp": config.stex_tp,
            },
        )
    if config.api_id == KiwoomRestSectorApiId.KA90002:
        return KiwoomRestSectorRequest(
            request_id=f"{config.config_id}-REQUEST",
            path="/api/dostk/thme",
            api_id=config.api_id,
            continuation=config.continuation,
            request_headers={
                "api-id": "ka90002",
                "authorization": "Bearer <TOKEN_REF_ONLY>",
                "cont-yn": config.continuation.cont_yn,
                "next-key": config.continuation.next_key,
            },
            request_body={
                "date_tp": config.date_tp,
                "thema_grp_cd": config.theme_group_code,
                "stex_tp": config.stex_tp,
            },
        )
    if config.api_id == KiwoomRestSectorApiId.KA40003:
        return KiwoomRestSectorRequest(
            request_id=f"{config.config_id}-REQUEST",
            path="/api/dostk/etf",
            api_id=config.api_id,
            continuation=config.continuation,
            request_headers={
                "api-id": "ka40003",
                "authorization": "Bearer <TOKEN_REF_ONLY>",
                "cont-yn": config.continuation.cont_yn,
                "next-key": config.continuation.next_key,
            },
            request_body={"stk_cd": config.provider_symbol},
        )
    raise ValueError("account/order api id is blocked")


def build_kiwoom_rest_theme_group_request(config: KiwoomRestSectorConfig) -> KiwoomRestSectorRequest:
    if config.api_id != KiwoomRestSectorApiId.KA90001:
        raise ValueError("theme group request requires ka90001")
    return _build_request(config)


def build_kiwoom_rest_theme_component_request(config: KiwoomRestSectorConfig) -> KiwoomRestSectorRequest:
    if config.api_id != KiwoomRestSectorApiId.KA90002:
        raise ValueError("theme component request requires ka90002")
    return _build_request(config)


def build_kiwoom_rest_etf_daily_trend_request(config: KiwoomRestSectorConfig) -> KiwoomRestSectorRequest:
    if config.api_id != KiwoomRestSectorApiId.KA40003:
        raise ValueError("etf daily trend request requires ka40003")
    return _build_request(config)


def _capability_matrix() -> list[CanonicalSectorCapabilitySignal]:
    entries: list[CanonicalSectorCapabilitySignal] = []
    for api_id in KiwoomRestSectorApiId:
        entries.append(
            CanonicalSectorCapabilitySignal(
                api_id=api_id,
                capability_group=CAPABILITY_GROUPS[api_id],
                request_builder_ready=api_id in READY_BUILDERS,
                readiness=_capability_readiness(api_id),
            )
        )
    return entries


def _parse_theme_groups(payload: dict[str, object]) -> list[KiwoomRestThemeGroupItem]:
    rows = payload.get("thema_grp")
    if rows is None:
        raise ValueError("theme group response rows are missing")
    if not isinstance(rows, list):
        raise ValueError("theme group rows must be a list")
    items: list[KiwoomRestThemeGroupItem] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("theme group row must be an object")
        items.append(
            KiwoomRestThemeGroupItem(
                theme_group_code=row.get("thema_grp_cd"),
                theme_name=row.get("thema_nm"),
                stock_count=row.get("stk_num"),
                change_sign=row.get("flu_sig"),
                change_rate=row.get("flu_rt"),
                rising_stock_count=row.get("rising_stk_num"),
                falling_stock_count=row.get("fall_stk_num"),
                period_return=row.get("dt_prft_rt"),
                main_stock=row.get("main_stk"),
            )
        )
    return items


def _parse_theme_components(config: KiwoomRestSectorConfig, payload: dict[str, object]) -> list[KiwoomRestThemeComponentItem]:
    rows = payload.get("thema_cmpst_stk") or payload.get("component_list")
    if rows is None:
        return [
            KiwoomRestThemeComponentItem(
                theme_group_code=config.theme_group_code or "UNKNOWN",
                theme_name=payload.get("thema_nm"),
                component_change_rate=payload.get("flu_rt"),
                component_return=payload.get("dt_prft_rt"),
                membership_evidence_flag=False,
            )
        ]
    if not isinstance(rows, list):
        raise ValueError("theme component rows must be a list")
    items: list[KiwoomRestThemeComponentItem] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("theme component row must be an object")
        items.append(
            KiwoomRestThemeComponentItem(
                theme_group_code=config.theme_group_code or row.get("thema_grp_cd"),
                theme_name=row.get("thema_nm") or payload.get("thema_nm"),
                component_stock_code=row.get("stk_cd"),
                component_stock_name=row.get("stk_nm"),
                component_change_rate=row.get("flu_rt"),
                component_return=row.get("dt_prft_rt"),
                membership_evidence_flag=True,
            )
        )
    return items


def _parse_etf_trends(config: KiwoomRestSectorConfig, payload: dict[str, object]) -> list[KiwoomRestEtfTrendItem]:
    rows = payload.get("etfdaly_trnsn")
    if rows is None:
        raise ValueError("etf trend response rows are missing")
    if not isinstance(rows, list):
        raise ValueError("etf trend rows must be a list")
    items: list[KiwoomRestEtfTrendItem] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("etf trend row must be an object")
        items.append(
            KiwoomRestEtfTrendItem(
                etf_stock_code=config.provider_symbol or row.get("stk_cd"),
                observed_at=row.get("cntr_dt"),
                price=row.get("cur_prc"),
                previous_close_diff=row.get("pred_pre"),
                percent_change=row.get("pre_rt"),
            )
        )
    return items


def _parse_response(config: KiwoomRestSectorConfig, payload: dict[str, object]) -> KiwoomRestSectorResponse:
    if not isinstance(payload, dict):
        raise ValueError("mocked response payload must be an object")
    continuation = KiwoomRestSectorContinuation(
        cont_yn=(payload.get("cont_yn") or payload.get("contYn") or payload.get("cont-yn") or "N"),
        next_key=(payload.get("next_key") or payload.get("nextKey") or payload.get("next-key") or ""),
    )
    return_code = payload.get("return_code")
    return_msg = payload.get("return_msg")
    if return_code is None or return_msg is None:
        raise ValueError("response return_code/return_msg missing")
    theme_groups = _parse_theme_groups(payload) if int(return_code) == 0 and config.api_id == KiwoomRestSectorApiId.KA90001 else []
    theme_components = _parse_theme_components(config, payload) if int(return_code) == 0 and config.api_id == KiwoomRestSectorApiId.KA90002 else []
    etf_trends = _parse_etf_trends(config, payload) if int(return_code) == 0 and config.api_id == KiwoomRestSectorApiId.KA40003 else []
    return KiwoomRestSectorResponse(
        response_id=f"{config.config_id}-RESPONSE",
        api_id=config.api_id,
        return_code=int(return_code),
        return_msg=str(return_msg),
        theme_groups=theme_groups,
        theme_components=theme_components,
        etf_trends=etf_trends,
        continuation=continuation,
        raw_payload_redacted=True,
    )


def _participation_hint(item: KiwoomRestThemeGroupItem) -> float | None:
    if item.stock_count in (None, 0) or item.rising_stock_count is None:
        return None
    return item.rising_stock_count / item.stock_count


def _concentration_hint(item: KiwoomRestThemeGroupItem) -> float | None:
    if item.stock_count in (None, 0) or not item.main_stock:
        return None
    return 1 / item.stock_count


def _to_theme_leadership(config: KiwoomRestSectorConfig, items: list[KiwoomRestThemeGroupItem]) -> list[CanonicalThemeLeadershipSignal]:
    return [
        CanonicalThemeLeadershipSignal(
            provider_api_id=config.api_id.value,
            theme_group_code=item.theme_group_code,
            theme_name=item.theme_name,
            stock_count=item.stock_count,
            rising_stock_count=item.rising_stock_count,
            falling_stock_count=item.falling_stock_count,
            theme_change_rate=item.change_rate,
            period_return=item.period_return,
            main_stock=item.main_stock,
            participation_hint=_participation_hint(item),
            concentration_hint=_concentration_hint(item),
            observed_at=config.available_at,
            available_at=config.available_at,
            source_ref=config.source_ref,
            quality_flags=["READ_ONLY_ONLY", "TOKEN_REF_ONLY", "KIWOOM_REST_THEME_LEADERSHIP"],
            gap_reason=None,
        )
        for item in items
    ]


def _to_theme_membership(config: KiwoomRestSectorConfig, items: list[KiwoomRestThemeComponentItem]) -> list[CanonicalThemeMembershipSignal]:
    return [
        CanonicalThemeMembershipSignal(
            provider_api_id=config.api_id.value,
            theme_group_code=item.theme_group_code,
            theme_name=item.theme_name,
            component_stock_code=item.component_stock_code,
            component_stock_name=item.component_stock_name,
            component_change_rate=item.component_change_rate,
            component_return=item.component_return,
            membership_evidence_flag=item.membership_evidence_flag,
            observed_at=config.available_at,
            available_at=config.available_at,
            source_ref=config.source_ref,
            gap_reason=None if item.membership_evidence_flag else "THEME_COMPONENT_FIELDS_PARTIAL",
        )
        for item in items
    ]


def _trend_direction(item: KiwoomRestEtfTrendItem) -> str | None:
    if item.previous_close_diff is None:
        return None
    if item.previous_close_diff > 0:
        return "UP"
    if item.previous_close_diff < 0:
        return "DOWN"
    return "FLAT"


def _to_etf_trends(config: KiwoomRestSectorConfig, items: list[KiwoomRestEtfTrendItem]) -> list[CanonicalEtfTrendSignal]:
    return [
        CanonicalEtfTrendSignal(
            provider_api_id=config.api_id.value,
            etf_stock_code=item.etf_stock_code,
            date=item.observed_at.strftime("%Y%m%d"),
            price=item.price,
            previous_close_difference=item.previous_close_diff,
            percent_change=item.percent_change,
            trend_direction=_trend_direction(item),
            observed_at=item.observed_at,
            available_at=config.available_at,
            source_ref=config.source_ref,
            quality_flags=["READ_ONLY_ONLY", "TOKEN_REF_ONLY", "KIWOOM_REST_ETF_TREND"],
            gap_reason=None,
        )
        for item in items
    ]


def build_kiwoom_rest_readonly_sector_adapter(
    config: KiwoomRestSectorConfig,
    *,
    transport: TransportCallable | None = None,
) -> KiwoomRestSectorAdapterResult:
    for audit in config.audit_records:
        validate_kiwoom_rest_sector_metadata_safety(
            {"source_path": audit.source_path, "operator_context": audit.operator_context},
            context="kiwoom rest sector audit",
        )

    gaps: list[KiwoomRestSectorGapEntry] = []
    capability_matrix = _capability_matrix()
    try:
        request = _build_request(config)
    except Exception as exc:
        request = KiwoomRestSectorRequest(
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
        gaps.append(_gap(config.config_id, "REQUEST", "SCHEMA_GAP", "BLOCKING", str(exc)))
        response = KiwoomRestSectorResponse(
            response_id=f"{config.config_id}-RESPONSE",
            api_id=config.api_id,
            return_code=-1,
            return_msg=str(exc),
            continuation=config.continuation,
        )
        leadership_signals: list[CanonicalThemeLeadershipSignal] = []
        membership_signals: list[CanonicalThemeMembershipSignal] = []
        etf_signals: list[CanonicalEtfTrendSignal] = []
        readiness = KiwoomRestSectorReadiness.FUTURE_SUPPORTED
    else:
        if config.available_at is None:
            gaps.append(_gap(config.config_id, "AVAILABLE-AT", "MISSING_AVAILABLE_AT", "WARNING", "available_at is missing"))
        try:
            payload = execute_kiwoom_rest_readonly_sector_transport(
                request,
                transport=transport or (lambda _: config.mocked_response_payload) if config.mocked_response_payload is not None else None,
            )
        except Exception as exc:
            gaps.append(_gap(config.config_id, "TRANSPORT", "NETWORK_TRANSPORT_BLOCKED", "BLOCKING", str(exc)))
            readiness = KiwoomRestSectorReadiness.BLOCKED
            response = KiwoomRestSectorResponse(
                response_id=f"{config.config_id}-RESPONSE",
                api_id=config.api_id,
                return_code=-1,
                return_msg=str(exc),
                continuation=config.continuation,
            )
            leadership_signals = []
            membership_signals = []
            etf_signals = []
        else:
            try:
                response = _parse_response(config, payload)
            except Exception as exc:
                gaps.append(_gap(config.config_id, "SCHEMA", "SCHEMA_GAP", "BLOCKING", str(exc)))
                readiness = KiwoomRestSectorReadiness.SCHEMA_GAP
                response = KiwoomRestSectorResponse(
                    response_id=f"{config.config_id}-RESPONSE",
                    api_id=config.api_id,
                    return_code=-1,
                    return_msg=str(exc),
                    continuation=config.continuation,
                )
                leadership_signals = []
                membership_signals = []
                etf_signals = []
            else:
                if response.return_code != 0:
                    gaps.append(_gap(config.config_id, "RETURN-CODE", "DATA_GAP", "WARNING", response.return_msg))
                    readiness = KiwoomRestSectorReadiness.DATA_GAP
                    leadership_signals = []
                    membership_signals = []
                    etf_signals = []
                else:
                    leadership_signals = _to_theme_leadership(config, response.theme_groups) if config.available_at is not None else []
                    membership_signals = _to_theme_membership(config, response.theme_components) if config.available_at is not None else []
                    etf_signals = _to_etf_trends(config, response.etf_trends)
                    if config.available_at is None and config.api_id in {
                        KiwoomRestSectorApiId.KA90001,
                        KiwoomRestSectorApiId.KA90002,
                    }:
                        readiness = KiwoomRestSectorReadiness.DATA_GAP
                    elif config.api_id == KiwoomRestSectorApiId.KA90001 and leadership_signals:
                        readiness = KiwoomRestSectorReadiness.THEME_LEADERSHIP_READY
                    elif config.api_id == KiwoomRestSectorApiId.KA90002 and membership_signals:
                        readiness = KiwoomRestSectorReadiness.THEME_MEMBERSHIP_READY
                    elif config.api_id == KiwoomRestSectorApiId.KA40003 and etf_signals:
                        readiness = KiwoomRestSectorReadiness.ETF_TREND_READY
                    else:
                        readiness = KiwoomRestSectorReadiness.MOCKED_TRANSPORT_READY

    if (
        (leadership_signals and readiness == KiwoomRestSectorReadiness.THEME_LEADERSHIP_READY)
        or (membership_signals and readiness == KiwoomRestSectorReadiness.THEME_MEMBERSHIP_READY)
        or (etf_signals and readiness == KiwoomRestSectorReadiness.ETF_TREND_READY)
    ):
        readiness = KiwoomRestSectorReadiness.READONLY_ADAPTER_READY
    if any(item.severity == "BLOCKING" for item in gaps) and readiness not in {
        KiwoomRestSectorReadiness.SCHEMA_GAP,
        KiwoomRestSectorReadiness.FUTURE_SUPPORTED,
    }:
        readiness = KiwoomRestSectorReadiness.BLOCKED

    summary = KiwoomRestSectorSummaryReport(
        report_id=f"{config.config_id}-SUMMARY-REPORT",
        readiness=readiness,
        decision_reason=(
            "mocked sector adapter produced canonical theme or etf signals"
            if readiness == KiwoomRestSectorReadiness.READONLY_ADAPTER_READY
            else "sector adapter has unresolved data or boundary gaps"
        ),
    )
    request_report = KiwoomRestSectorRequestReport(report_id=f"{config.config_id}-REQUEST-REPORT", request=request)
    mocked_response_report = KiwoomRestSectorMockedResponseReport(
        report_id=f"{config.config_id}-MOCKED-RESPONSE-REPORT",
        response=response,
    )
    leadership_report = KiwoomRestCanonicalThemeLeadershipReport(
        report_id=f"{config.config_id}-CANONICAL-THEME-LEADERSHIP-REPORT",
        signals=leadership_signals,
    )
    membership_report = KiwoomRestCanonicalThemeMembershipReport(
        report_id=f"{config.config_id}-CANONICAL-THEME-MEMBERSHIP-REPORT",
        signals=membership_signals,
    )
    etf_report = KiwoomRestCanonicalEtfTrendReport(
        report_id=f"{config.config_id}-CANONICAL-ETF-TREND-REPORT",
        signals=etf_signals,
    )
    capability_report = KiwoomRestSectorEtfCapabilityMatrixReport(
        report_id=f"{config.config_id}-SECTOR-ETF-CAPABILITY-MATRIX-REPORT",
        entries=capability_matrix,
    )
    continuation_report = KiwoomRestSectorContinuationReport(
        report_id=f"{config.config_id}-CONTINUATION-REPORT",
        continuation=response.continuation,
        has_more=response.continuation.cont_yn == "Y",
    )
    v7_integration_report = KiwoomRestSectorV7IntegrationReport(
        report_id=f"{config.config_id}-V7-INTEGRATION-REPORT",
        v712_leadership_membership_etf_ready=bool(leadership_signals or membership_signals or etf_signals),
        v710_etf_liquidity_risk_context_ready=bool(etf_signals),
        canonical_fields_present=all(signal.available_at is not None for signal in leadership_signals + membership_signals + etf_signals)
        if (leadership_signals or membership_signals or etf_signals)
        else False,
    )
    gaps.append(_gap(config.config_id, "REPORT-GENERATED", "READONLY_SECTOR_REPORT_GENERATED", "REPORT_ONLY", "kiwoom readonly sector report generated"))
    gap_report = KiwoomRestSectorGapReport(
        gap_report_id=f"{config.config_id}-GAP-REPORT",
        readiness=readiness,
        gap_entries=gaps,
    )
    return KiwoomRestSectorAdapterResult(
        adapter_result_id=f"{config.config_id}-ADAPTER-RESULT",
        request=request,
        summary_report=summary,
        request_report=request_report,
        mocked_response_report=mocked_response_report,
        canonical_theme_leadership_report=leadership_report,
        canonical_theme_membership_report=membership_report,
        canonical_etf_trend_report=etf_report,
        sector_etf_capability_matrix_report=capability_report,
        continuation_report=continuation_report,
        safety_report=config.safety_report,
        v7_integration_report=v7_integration_report,
        gap_report=gap_report,
        audit_records=config.audit_records,
    )
