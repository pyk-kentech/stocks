from __future__ import annotations

from stock_risk_mcp.kiwoom_rest_readonly_quote_client import (
    TransportCallable,
    execute_kiwoom_rest_readonly_quote_transport,
)
from stock_risk_mcp.kiwoom_rest_readonly_quote_guard import validate_kiwoom_rest_quote_metadata_safety
from stock_risk_mcp.kiwoom_rest_readonly_quote_models import (
    CanonicalBasicInstrumentInfo,
    CanonicalLiquidityHint,
    CanonicalOrderbookRecord,
    CanonicalQuoteRecord,
    KiwoomRestBasicInfo,
    KiwoomRestBasicInfoReport,
    KiwoomRestCanonicalOrderbookReport,
    KiwoomRestCanonicalQuoteReport,
    KiwoomRestExecutionItem,
    KiwoomRestLiquidityHintReport,
    KiwoomRestOrderbookLevel,
    KiwoomRestQuoteAdapterResult,
    KiwoomRestQuoteApiId,
    KiwoomRestQuoteConfig,
    KiwoomRestQuoteContinuation,
    KiwoomRestQuoteContinuationReport,
    KiwoomRestQuoteGapEntry,
    KiwoomRestQuoteGapReport,
    KiwoomRestQuoteMockedResponseReport,
    KiwoomRestQuoteReadiness,
    KiwoomRestQuoteRequest,
    KiwoomRestQuoteRequestReport,
    KiwoomRestQuoteResponse,
    KiwoomRestQuoteSummaryReport,
    KiwoomRestQuoteV7IntegrationReport,
)


SUPPORTED_REQUEST_API_IDS = {
    KiwoomRestQuoteApiId.KA10004,
    KiwoomRestQuoteApiId.KA10003,
    KiwoomRestQuoteApiId.KA10001,
}


def _gap(config_id: str, suffix: str, category: str, severity: str, message: str) -> KiwoomRestQuoteGapEntry:
    return KiwoomRestQuoteGapEntry(
        gap_id=f"{config_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def _path_for_api(api_id: KiwoomRestQuoteApiId) -> str:
    if api_id == KiwoomRestQuoteApiId.KA10004:
        return "/api/dostk/mrkcond"
    return "/api/dostk/stkinfo"


def _build_request(config: KiwoomRestQuoteConfig) -> KiwoomRestQuoteRequest:
    if config.api_id not in SUPPORTED_REQUEST_API_IDS:
        raise ValueError("account/order api id is blocked")
    body = {"stk_cd": config.provider_symbol}
    return KiwoomRestQuoteRequest(
        request_id=f"{config.config_id}-REQUEST",
        path=_path_for_api(config.api_id),
        api_id=config.api_id,
        provider_symbol=config.provider_symbol,
        continuation=config.continuation,
        request_headers={
            "api-id": config.api_id.value.lower(),
            "authorization": "Bearer <TOKEN_REF_ONLY>",
            "cont-yn": config.continuation.cont_yn,
            "next-key": config.continuation.next_key,
        },
        request_body=body,
    )


def build_kiwoom_rest_quote_orderbook_request(config: KiwoomRestQuoteConfig) -> KiwoomRestQuoteRequest:
    if config.api_id != KiwoomRestQuoteApiId.KA10004:
        raise ValueError("quote orderbook request requires ka10004")
    return _build_request(config)


def build_kiwoom_rest_execution_info_request(config: KiwoomRestQuoteConfig) -> KiwoomRestQuoteRequest:
    if config.api_id != KiwoomRestQuoteApiId.KA10003:
        raise ValueError("execution info request requires ka10003")
    return _build_request(config)


def build_kiwoom_rest_basic_info_request(config: KiwoomRestQuoteConfig) -> KiwoomRestQuoteRequest:
    if config.api_id != KiwoomRestQuoteApiId.KA10001:
        raise ValueError("basic info request requires ka10001")
    return _build_request(config)


def _response_symbol(payload: dict[str, object], config: KiwoomRestQuoteConfig) -> str:
    return str(payload.get("stk_cd") or config.provider_symbol).strip().upper()


def _response_stock_name(payload: dict[str, object]) -> str | None:
    value = payload.get("stk_nm") or payload.get("stock_name")
    if value in (None, ""):
        return None
    return str(value).strip()


def _execution_observed_at(config: KiwoomRestQuoteConfig, row: dict[str, object]) -> str:
    base_date = config.request_date or (config.available_at.strftime("%Y%m%d") if config.available_at is not None else "")
    tm = str(row.get("tm") or "").strip()
    if base_date and tm:
        return f"{base_date}{tm}"
    observed_at = row.get("observed_at")
    if observed_at is not None:
        return str(observed_at)
    return base_date


def _parse_orderbook_levels(payload: dict[str, object]) -> list[KiwoomRestOrderbookLevel]:
    levels: list[KiwoomRestOrderbookLevel] = []
    for index in range(1, 11):
        ask_price = payload.get(f"ask_price_{index}") or payload.get(f"sel_pri_{index}") or payload.get(f"offerho{index}")
        ask_qty = payload.get(f"ask_qty_{index}") or payload.get(f"sel_qty_{index}") or payload.get(f"offerrem{index}")
        ask_change = payload.get(f"ask_qty_change_{index}") or payload.get(f"sel_rem_chg_{index}")
        bid_price = payload.get(f"bid_price_{index}") or payload.get(f"buy_pri_{index}") or payload.get(f"bidho{index}")
        bid_qty = payload.get(f"bid_qty_{index}") or payload.get(f"buy_qty_{index}") or payload.get(f"bidrem{index}")
        bid_change = payload.get(f"bid_qty_change_{index}") or payload.get(f"buy_rem_chg_{index}")
        if ask_price is not None or ask_qty is not None or ask_change is not None:
            levels.append(
                KiwoomRestOrderbookLevel(
                    side="ASK",
                    level=index,
                    price=ask_price,
                    quantity=ask_qty,
                    quantity_change=ask_change,
                )
            )
        if bid_price is not None or bid_qty is not None or bid_change is not None:
            levels.append(
                KiwoomRestOrderbookLevel(
                    side="BID",
                    level=index,
                    price=bid_price,
                    quantity=bid_qty,
                    quantity_change=bid_change,
                )
            )
    return levels


def _parse_execution_items(config: KiwoomRestQuoteConfig, payload: dict[str, object]) -> list[KiwoomRestExecutionItem]:
    rows = payload.get("cntr_infr")
    if rows is None:
        return []
    if not isinstance(rows, list):
        raise ValueError("execution response rows are missing")
    items: list[KiwoomRestExecutionItem] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("execution row must be an object")
        items.append(
            KiwoomRestExecutionItem(
                observed_at=_execution_observed_at(config, row),
                last_price=row.get("cur_prc"),
                price_change=row.get("pred_pre"),
                percent_change=row.get("pre_rt"),
                priority_ask_price=row.get("pri_sel_bid_unit"),
                priority_bid_price=row.get("pri_buy_bid_unit"),
                last_trade_quantity=row.get("cntr_trde_qty"),
                sign_code=row.get("sign"),
            )
        )
    return items


def _parse_basic_info(payload: dict[str, object], config: KiwoomRestQuoteConfig) -> KiwoomRestBasicInfo | None:
    if config.api_id != KiwoomRestQuoteApiId.KA10001:
        return None
    return KiwoomRestBasicInfo(
        provider_symbol=_response_symbol(payload, config),
        stock_name=_response_stock_name(payload),
        settlement_month=payload.get("setl_mm"),
        face_value=payload.get("fav"),
        capital=payload.get("cap"),
        listed_shares=payload.get("flo_stk"),
        credit_ratio=payload.get("crd_rt"),
        yearly_high=payload.get("oyr_hgst"),
        yearly_low=payload.get("oyr_lwst"),
        market_cap=payload.get("mac"),
        market_cap_weight=payload.get("mac_wght"),
    )


def _parse_orderbook_base_time(config: KiwoomRestQuoteConfig, payload: dict[str, object]):
    raw_time = payload.get("bid_req_base_tm")
    if raw_time in (None, ""):
        return None
    base_date = config.request_date or (config.available_at.strftime("%Y%m%d") if config.available_at is not None else "")
    if base_date:
        return f"{base_date}{str(raw_time).strip()}"
    return str(raw_time).strip()


def _parse_response(config: KiwoomRestQuoteConfig, payload: dict[str, object]) -> KiwoomRestQuoteResponse:
    if not isinstance(payload, dict):
        raise ValueError("mocked response payload must be an object")
    continuation = KiwoomRestQuoteContinuation(
        cont_yn=(payload.get("cont_yn") or payload.get("contYn") or payload.get("cont-yn") or "N"),
        next_key=(payload.get("next_key") or payload.get("nextKey") or payload.get("next-key") or ""),
    )
    return_code = payload.get("return_code")
    return_msg = payload.get("return_msg")
    if return_code is None or return_msg is None:
        raise ValueError("response return_code/return_msg missing")
    orderbook_levels = _parse_orderbook_levels(payload) if int(return_code) == 0 and config.api_id == KiwoomRestQuoteApiId.KA10004 else []
    execution_items = _parse_execution_items(config, payload) if int(return_code) == 0 and config.api_id == KiwoomRestQuoteApiId.KA10003 else []
    basic_info = _parse_basic_info(payload, config) if int(return_code) == 0 else None
    return KiwoomRestQuoteResponse(
        response_id=f"{config.config_id}-RESPONSE",
        api_id=config.api_id,
        provider_symbol=_response_symbol(payload, config),
        stock_name=_response_stock_name(payload),
        return_code=int(return_code),
        return_msg=str(return_msg),
        orderbook_base_time=_parse_orderbook_base_time(config, payload),
        orderbook_levels=orderbook_levels,
        execution_items=execution_items,
        basic_info=basic_info,
        continuation=continuation,
        raw_payload_redacted=True,
    )


def _canonical_key(symbol: str) -> str:
    return f"{symbol}_KRX"


def _top_level(levels: list[KiwoomRestOrderbookLevel], side: str) -> KiwoomRestOrderbookLevel | None:
    matches = [level for level in levels if level.side == side]
    if not matches:
        return None
    matches.sort(key=lambda item: item.level)
    return matches[0]


def _spread(best_ask: KiwoomRestOrderbookLevel | None, best_bid: KiwoomRestOrderbookLevel | None) -> float | None:
    if best_ask is None or best_bid is None or best_ask.price is None or best_bid.price is None:
        return None
    return best_ask.price - best_bid.price


def _mid(best_ask: KiwoomRestOrderbookLevel | None, best_bid: KiwoomRestOrderbookLevel | None) -> float | None:
    if best_ask is None or best_bid is None or best_ask.price is None or best_bid.price is None:
        return None
    return (best_ask.price + best_bid.price) / 2


def _imbalance(best_ask: KiwoomRestOrderbookLevel | None, best_bid: KiwoomRestOrderbookLevel | None) -> float | None:
    if best_ask is None or best_bid is None or best_ask.quantity is None or best_bid.quantity is None:
        return None
    total = best_ask.quantity + best_bid.quantity
    if total == 0:
        return None
    return (best_bid.quantity - best_ask.quantity) / total


def _depth_summary(levels: list[KiwoomRestOrderbookLevel]) -> float | None:
    quantities = [level.quantity for level in levels if level.quantity is not None]
    if not quantities:
        return None
    return sum(quantities)


def _quote_observed_at(response: KiwoomRestQuoteResponse, config: KiwoomRestQuoteConfig):
    if response.orderbook_base_time is not None:
        return response.orderbook_base_time
    if response.execution_items:
        return response.execution_items[0].observed_at
    if config.available_at is not None:
        return config.available_at
    raise ValueError("observed_at is unavailable")


def _to_canonical_quote(config: KiwoomRestQuoteConfig, response: KiwoomRestQuoteResponse) -> list[CanonicalQuoteRecord]:
    best_ask = _top_level(response.orderbook_levels, "ASK")
    best_bid = _top_level(response.orderbook_levels, "BID")
    execution = response.execution_items[0] if response.execution_items else None
    gap_reason = None
    if best_ask is None or best_bid is None:
        gap_reason = "BID_ASK_UNAVAILABLE"
    return [
        CanonicalQuoteRecord(
            provider_api_id=config.api_id.value,
            canonical_instrument_key=_canonical_key(response.provider_symbol),
            provider_symbol=response.provider_symbol,
            stock_name=response.stock_name,
            observed_at=_quote_observed_at(response, config),
            available_at=config.available_at,
            last_price=execution.last_price if execution else None,
            bid_price=best_bid.price if best_bid else None,
            ask_price=best_ask.price if best_ask else None,
            bid_quantity=best_bid.quantity if best_bid else None,
            ask_quantity=best_ask.quantity if best_ask else None,
            spread=_spread(best_ask, best_bid),
            mid_price=_mid(best_ask, best_bid),
            last_trade_quantity=execution.last_trade_quantity if execution else None,
            percent_change=execution.percent_change if execution else None,
            price_change=execution.price_change if execution else None,
            liquidity_evidence_flag=bool(best_ask or best_bid or execution),
            source_ref=config.source_ref,
            quality_flags=["READ_ONLY_ONLY", "TOKEN_REF_ONLY", "KIWOOM_REST_CANONICAL_QUOTE"],
            stale_flag=False,
            gap_reason=gap_reason,
        )
    ]


def _to_canonical_orderbook(config: KiwoomRestQuoteConfig, response: KiwoomRestQuoteResponse) -> list[CanonicalOrderbookRecord]:
    best_ask = _top_level(response.orderbook_levels, "ASK")
    best_bid = _top_level(response.orderbook_levels, "BID")
    gap_reason = None if response.orderbook_levels else "ORDERBOOK_LEVELS_UNAVAILABLE"
    return [
        CanonicalOrderbookRecord(
            provider_api_id=config.api_id.value,
            canonical_instrument_key=_canonical_key(response.provider_symbol),
            provider_symbol=response.provider_symbol,
            stock_name=response.stock_name,
            observed_at=_quote_observed_at(response, config),
            available_at=config.available_at,
            levels=response.orderbook_levels,
            spread=_spread(best_ask, best_bid),
            mid_price=_mid(best_ask, best_bid),
            top_of_book_imbalance=_imbalance(best_ask, best_bid),
            depth_summary_quantity=_depth_summary(response.orderbook_levels),
            source_ref=config.source_ref,
            quality_flags=["READ_ONLY_ONLY", "TOKEN_REF_ONLY", "KIWOOM_REST_CANONICAL_ORDERBOOK"],
            stale_flag=False,
            gap_reason=gap_reason,
        )
    ]


def _to_liquidity_hint(config: KiwoomRestQuoteConfig, quote_records: list[CanonicalQuoteRecord], orderbook_records: list[CanonicalOrderbookRecord]) -> list[CanonicalLiquidityHint]:
    if not quote_records:
        return []
    quote = quote_records[0]
    orderbook = orderbook_records[0] if orderbook_records else None
    return [
        CanonicalLiquidityHint(
            provider_api_id=config.api_id.value,
            canonical_instrument_key=quote.canonical_instrument_key,
            provider_symbol=quote.provider_symbol,
            stock_name=quote.stock_name,
            observed_at=quote.observed_at,
            available_at=quote.available_at,
            spread=quote.spread,
            mid_price=quote.mid_price,
            last_trade_quantity=quote.last_trade_quantity,
            top_of_book_imbalance=orderbook.top_of_book_imbalance if orderbook else None,
            price_liquidity_ready=quote.last_price is not None or quote.bid_price is not None or quote.ask_price is not None,
            outlier_routing_ready=orderbook is not None and orderbook.top_of_book_imbalance is not None,
            mock_intent_preview_ready=quote.last_price is not None and (quote.bid_price is not None or quote.ask_price is not None),
            source_ref=config.source_ref,
            quality_flags=["READ_ONLY_ONLY", "TOKEN_REF_ONLY", "KIWOOM_REST_LIQUIDITY_HINT"],
            stale_flag=False,
            gap_reason=quote.gap_reason,
        )
    ]


def _to_basic_info(config: KiwoomRestQuoteConfig, response: KiwoomRestQuoteResponse) -> list[CanonicalBasicInstrumentInfo]:
    if response.basic_info is None:
        return []
    gap_reason = None
    if response.basic_info.stock_name is None:
        gap_reason = "BASIC_INFO_PARTIAL_METADATA"
    return [
        CanonicalBasicInstrumentInfo(
            provider_api_id=config.api_id.value,
            canonical_instrument_key=_canonical_key(response.basic_info.provider_symbol),
            provider_symbol=response.basic_info.provider_symbol,
            stock_name=response.basic_info.stock_name,
            available_at=config.available_at,
            settlement_month=response.basic_info.settlement_month,
            face_value=response.basic_info.face_value,
            capital=response.basic_info.capital,
            listed_shares=response.basic_info.listed_shares,
            credit_ratio=response.basic_info.credit_ratio,
            yearly_high=response.basic_info.yearly_high,
            yearly_low=response.basic_info.yearly_low,
            market_cap=response.basic_info.market_cap,
            market_cap_weight=response.basic_info.market_cap_weight,
            source_ref=config.source_ref,
            quality_flags=["READ_ONLY_ONLY", "TOKEN_REF_ONLY", "KIWOOM_REST_BASIC_INFO"],
            stale_flag=False,
            gap_reason=gap_reason,
        )
    ]


def build_kiwoom_rest_readonly_quote_adapter(
    config: KiwoomRestQuoteConfig,
    *,
    transport: TransportCallable | None = None,
) -> KiwoomRestQuoteAdapterResult:
    for audit in config.audit_records:
        validate_kiwoom_rest_quote_metadata_safety(
            {"source_path": audit.source_path, "operator_context": audit.operator_context},
            context="kiwoom rest quote audit",
        )

    gaps: list[KiwoomRestQuoteGapEntry] = []
    request = _build_request(config)
    if config.available_at is None:
        gaps.append(_gap(config.config_id, "AVAILABLE-AT", "MISSING_AVAILABLE_AT", "WARNING", "available_at is missing"))

    try:
        payload = execute_kiwoom_rest_readonly_quote_transport(
            request,
            transport=transport or (lambda _: config.mocked_response_payload) if config.mocked_response_payload is not None else None,
        )
    except Exception as exc:
        gaps.append(_gap(config.config_id, "TRANSPORT", "NETWORK_TRANSPORT_BLOCKED", "BLOCKING", str(exc)))
        readiness = KiwoomRestQuoteReadiness.BLOCKED
        response = KiwoomRestQuoteResponse(
            response_id=f"{config.config_id}-RESPONSE",
            api_id=config.api_id,
            provider_symbol=config.provider_symbol,
            return_code=-1,
            return_msg=str(exc),
            continuation=config.continuation,
        )
        quote_records: list[CanonicalQuoteRecord] = []
        orderbook_records: list[CanonicalOrderbookRecord] = []
        liquidity_hints: list[CanonicalLiquidityHint] = []
        basic_info_records: list[CanonicalBasicInstrumentInfo] = []
    else:
        try:
            response = _parse_response(config, payload)
        except Exception as exc:
            gaps.append(_gap(config.config_id, "SCHEMA", "SCHEMA_GAP", "BLOCKING", str(exc)))
            readiness = KiwoomRestQuoteReadiness.SCHEMA_GAP
            response = KiwoomRestQuoteResponse(
                response_id=f"{config.config_id}-RESPONSE",
                api_id=config.api_id,
                provider_symbol=config.provider_symbol,
                return_code=-1,
                return_msg=str(exc),
                continuation=config.continuation,
            )
            quote_records = []
            orderbook_records = []
            liquidity_hints = []
            basic_info_records = []
        else:
            if response.return_code != 0:
                gaps.append(_gap(config.config_id, "RETURN-CODE", "DATA_GAP", "WARNING", response.return_msg))
                readiness = KiwoomRestQuoteReadiness.DATA_GAP
                quote_records = []
                orderbook_records = []
                liquidity_hints = []
                basic_info_records = []
            else:
                quote_records = _to_canonical_quote(config, response)
                orderbook_records = _to_canonical_orderbook(config, response)
                liquidity_hints = _to_liquidity_hint(config, quote_records, orderbook_records)
                basic_info_records = _to_basic_info(config, response)
                if config.available_at is None:
                    readiness = KiwoomRestQuoteReadiness.DATA_GAP
                elif config.api_id == KiwoomRestQuoteApiId.KA10004 and orderbook_records and quote_records:
                    readiness = KiwoomRestQuoteReadiness.CANONICAL_ORDERBOOK_READY
                elif config.api_id == KiwoomRestQuoteApiId.KA10003 and liquidity_hints:
                    readiness = KiwoomRestQuoteReadiness.LIQUIDITY_HINT_READY
                elif config.api_id == KiwoomRestQuoteApiId.KA10001 and basic_info_records:
                    readiness = KiwoomRestQuoteReadiness.CANONICAL_QUOTE_READY
                else:
                    readiness = KiwoomRestQuoteReadiness.MOCKED_TRANSPORT_READY

    if quote_records and orderbook_records and liquidity_hints and readiness in {
        KiwoomRestQuoteReadiness.CANONICAL_ORDERBOOK_READY,
        KiwoomRestQuoteReadiness.LIQUIDITY_HINT_READY,
    }:
        readiness = KiwoomRestQuoteReadiness.READONLY_ADAPTER_READY
    if any(item.severity == "BLOCKING" for item in gaps) and readiness != KiwoomRestQuoteReadiness.SCHEMA_GAP:
        readiness = KiwoomRestQuoteReadiness.BLOCKED

    summary = KiwoomRestQuoteSummaryReport(
        report_id=f"{config.config_id}-SUMMARY-REPORT",
        readiness=readiness,
        decision_reason=(
            "mocked quote adapter produced canonical quote orderbook and liquidity records"
            if readiness == KiwoomRestQuoteReadiness.READONLY_ADAPTER_READY
            else "quote adapter has unresolved data or boundary gaps"
        ),
    )
    request_report = KiwoomRestQuoteRequestReport(report_id=f"{config.config_id}-REQUEST-REPORT", request=request)
    mocked_response_report = KiwoomRestQuoteMockedResponseReport(
        report_id=f"{config.config_id}-MOCKED-RESPONSE-REPORT",
        response=response,
    )
    canonical_quote_report = KiwoomRestCanonicalQuoteReport(
        report_id=f"{config.config_id}-CANONICAL-QUOTE-REPORT",
        records=quote_records,
    )
    canonical_orderbook_report = KiwoomRestCanonicalOrderbookReport(
        report_id=f"{config.config_id}-CANONICAL-ORDERBOOK-REPORT",
        records=orderbook_records,
    )
    liquidity_hint_report = KiwoomRestLiquidityHintReport(
        report_id=f"{config.config_id}-LIQUIDITY-HINT-REPORT",
        records=liquidity_hints,
    )
    basic_info_report = KiwoomRestBasicInfoReport(
        report_id=f"{config.config_id}-BASIC-INFO-REPORT",
        records=basic_info_records,
    )
    continuation_report = KiwoomRestQuoteContinuationReport(
        report_id=f"{config.config_id}-CONTINUATION-REPORT",
        continuation=response.continuation,
        has_more=response.continuation.cont_yn == "Y",
    )
    v7_integration_report = KiwoomRestQuoteV7IntegrationReport(
        report_id=f"{config.config_id}-V7-INTEGRATION-REPORT",
        v710_price_liquidity_ready=bool(liquidity_hints and liquidity_hints[0].price_liquidity_ready),
        v712_liquidity_outlier_ready=bool(liquidity_hints and liquidity_hints[0].outlier_routing_ready),
        v713_mock_intent_preview_ready=bool(liquidity_hints and liquidity_hints[0].mock_intent_preview_ready),
        canonical_fields_present=all(record.available_at is not None for record in quote_records + orderbook_records + liquidity_hints + basic_info_records)
        if (quote_records or orderbook_records or liquidity_hints or basic_info_records)
        else False,
    )
    gaps.append(_gap(config.config_id, "REPORT-GENERATED", "READONLY_QUOTE_REPORT_GENERATED", "REPORT_ONLY", "kiwoom readonly quote report generated"))
    gap_report = KiwoomRestQuoteGapReport(
        gap_report_id=f"{config.config_id}-GAP-REPORT",
        readiness=readiness,
        gap_entries=gaps,
    )
    return KiwoomRestQuoteAdapterResult(
        adapter_result_id=f"{config.config_id}-ADAPTER-RESULT",
        request=request,
        summary_report=summary,
        request_report=request_report,
        mocked_response_report=mocked_response_report,
        canonical_quote_report=canonical_quote_report,
        canonical_orderbook_report=canonical_orderbook_report,
        liquidity_hint_report=liquidity_hint_report,
        basic_info_report=basic_info_report,
        continuation_report=continuation_report,
        safety_report=config.safety_report,
        v7_integration_report=v7_integration_report,
        gap_report=gap_report,
        audit_records=config.audit_records,
    )
