from __future__ import annotations

from datetime import datetime

from stock_risk_mcp.historical_market_data_models import (
    HistoricalChartRawResponse,
    HistoricalMarketDataApiId,
    HistoricalMarketDataInterval,
    HistoricalOhlcvRow,
)


_ROW_ARRAY_CANDIDATE_KEYS = {
    HistoricalMarketDataApiId.KA10080: (
        "stk_min_pole_chart_qry",
        "stk_min_chart_qry",
        "min_pole_chart_qry",
        "chart_rows",
        "rows",
        "data",
        "output",
        "output1",
    ),
    HistoricalMarketDataApiId.KA10081: (
        "stk_day_pole_chart_qry",
        "stk_dt_pole_chart_qry",
        "stk_day_chart_qry",
        "day_pole_chart_qry",
        "chart_rows",
        "rows",
        "data",
        "output",
        "output1",
    ),
}

_DATE_KEYS = ("cntr_tm", "dt", "date", "bsop_date", "stck_bsop_date", "trade_date")
_OPEN_KEYS = ("open_pric", "open", "stck_oprc", "start_pric")
_HIGH_KEYS = ("high_pric", "high", "stck_hgpr")
_LOW_KEYS = ("low_pric", "low", "stck_lwpr")
_CLOSE_KEYS = ("cur_prc", "close", "stck_clpr", "last_pric")
_VOLUME_KEYS = ("trde_qty", "acc_trde_qty", "volume", "acml_vol", "cntg_vol")


def _parse_observed_at(raw_value: object, *, interval: HistoricalMarketDataInterval) -> datetime:
    text = str(raw_value).strip()
    if len(text) == 8 and text.isdigit():
        return datetime.fromisoformat(f"{text[:4]}-{text[4:6]}-{text[6:8]}T15:30:00+09:00")
    if len(text) == 12 and text.isdigit():
        return datetime.fromisoformat(f"{text[:4]}-{text[4:6]}-{text[6:8]}T{text[8:10]}:{text[10:12]}:00+09:00")
    if len(text) == 14 and text.isdigit():
        return datetime.fromisoformat(f"{text[:4]}-{text[4:6]}-{text[6:8]}T{text[8:10]}:{text[10:12]}:{text[12:14]}+09:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("observed_at must include timezone")
    return parsed


def _rows_key(api_id: HistoricalMarketDataApiId) -> tuple[str, HistoricalMarketDataInterval]:
    if api_id == HistoricalMarketDataApiId.KA10080:
        return "stk_min_pole_chart_qry", HistoricalMarketDataInterval.ONE_MINUTE
    if api_id == HistoricalMarketDataApiId.KA10081:
        return "stk_day_pole_chart_qry", HistoricalMarketDataInterval.ONE_DAY
    raise ValueError("normalizer supports ka10080/ka10081 only in v14")


def _pick(row: dict[str, object], keys: tuple[str, ...]) -> object:
    for key in keys:
        if row.get(key) not in (None, ""):
            return row.get(key)
    return None


def _looks_like_chart_row(row: object) -> bool:
    if not isinstance(row, dict):
        return False
    has_date = _pick(row, _DATE_KEYS) is not None
    has_close = _pick(row, _CLOSE_KEYS) is not None
    has_price_context = any(_pick(row, keys) is not None for keys in (_OPEN_KEYS, _HIGH_KEYS, _LOW_KEYS))
    return has_date and has_close and has_price_context


def extract_chart_rows(api_id: HistoricalMarketDataApiId, raw_payload: dict[str, object]) -> list[dict[str, object]] | None:
    for key in _ROW_ARRAY_CANDIDATE_KEYS.get(api_id, ()):
        rows = raw_payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    for value in raw_payload.values():
        if isinstance(value, list) and value and all(_looks_like_chart_row(item) for item in value):
            return [item for item in value if isinstance(item, dict)]
    return None


def classify_chart_payload(api_id: HistoricalMarketDataApiId, raw_payload: dict[str, object]) -> str:
    return_code = int(raw_payload.get("return_code", 0) or 0)
    return_msg = str(raw_payload.get("return_msg", "") or "")
    message = return_msg.lower()
    if return_code != 0 and any(term in message for term in ("token", "auth", "인증", "권한", "access")):
        return "BLOCKED_AUTH_OR_TOKEN"
    rows = extract_chart_rows(api_id, raw_payload)
    if rows is None:
        return "DEPENDENCY_GAP_KIWOOM_ENDPOINT_SCHEMA"
    if not rows:
        return "PROVIDER_EMPTY_RESPONSE"
    if not any(_looks_like_chart_row(row) for row in rows):
        return "DEPENDENCY_GAP_KIWOOM_ENDPOINT_SCHEMA"
    return "REAL_CAPTURE_EXECUTED"


def normalize_historical_ohlcv_rows(dataset_id: str, raw_responses: list[HistoricalChartRawResponse]) -> list[HistoricalOhlcvRow]:
    normalized: list[HistoricalOhlcvRow] = []
    seen: set[tuple[str, str, datetime]] = set()
    for response in raw_responses:
        _rows_key_name, interval = _rows_key(response.api_id)
        rows = extract_chart_rows(response.api_id, response.raw_payload)
        if rows is None:
            raise ValueError(f"{response.response_id} missing chart rows")
        last_observed: datetime | None = None
        for index, row in enumerate(rows):
            observed_at = _parse_observed_at(_pick(row, _DATE_KEYS), interval=interval)
            key = (response.canonical_instrument_id, interval.value, observed_at)
            quality_flags: list[str] = []
            if key in seen:
                quality_flags.append("DUPLICATE_BAR")
            if last_observed is not None and observed_at > last_observed and interval == HistoricalMarketDataInterval.ONE_DAY:
                quality_flags.append("OUT_OF_ORDER_SEQUENCE")
            last_observed = observed_at
            seen.add(key)
            normalized.append(
                HistoricalOhlcvRow(
                    row_id=f"{response.response_id}-{index}",
                    dataset_id=dataset_id,
                    instrument_id=response.canonical_instrument_id,
                    provider_symbol=response.provider_symbol,
                    interval=interval,
                    api_id=response.api_id,
                    observed_at=observed_at,
                    available_at=response.available_at,
                    open_price=float(_pick(row, _OPEN_KEYS)) if _pick(row, _OPEN_KEYS) is not None else None,
                    high_price=float(_pick(row, _HIGH_KEYS)) if _pick(row, _HIGH_KEYS) is not None else None,
                    low_price=float(_pick(row, _LOW_KEYS)) if _pick(row, _LOW_KEYS) is not None else None,
                    close_price=float(_pick(row, _CLOSE_KEYS)),
                    volume=float(_pick(row, _VOLUME_KEYS) or 0),
                    adjusted=True,
                    adjustment_policy="UPD_STKPC_TP_1",
                    continuation_cont_yn=response.cont_yn,
                    continuation_next_key=response.next_key,
                    source_ref=response.source_ref,
                    quality_flags=quality_flags,
                )
            )
    normalized.sort(key=lambda item: (item.instrument_id, item.interval.value, item.observed_at))
    return normalized
