from __future__ import annotations

from datetime import datetime

from stock_risk_mcp.historical_market_data_models import (
    HistoricalChartRawResponse,
    HistoricalMarketDataApiId,
    HistoricalMarketDataInterval,
    HistoricalOhlcvRow,
)


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


def normalize_historical_ohlcv_rows(dataset_id: str, raw_responses: list[HistoricalChartRawResponse]) -> list[HistoricalOhlcvRow]:
    normalized: list[HistoricalOhlcvRow] = []
    seen: set[tuple[str, str, datetime]] = set()
    for response in raw_responses:
        rows_key, interval = _rows_key(response.api_id)
        rows = response.raw_payload.get(rows_key)
        if rows is None and response.api_id == HistoricalMarketDataApiId.KA10081:
            rows = response.raw_payload.get("stk_dt_pole_chart_qry")
        if not isinstance(rows, list):
            raise ValueError(f"{response.response_id} missing chart rows")
        last_observed: datetime | None = None
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError("chart row must be an object")
            observed_at = _parse_observed_at(row.get("cntr_tm") or row.get("dt") or row.get("date") or row.get("bsop_date"), interval=interval)
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
                    open_price=float(row["open_pric"]) if row.get("open_pric") is not None else None,
                    high_price=float(row["high_pric"]) if row.get("high_pric") is not None else None,
                    low_price=float(row["low_pric"]) if row.get("low_pric") is not None else None,
                    close_price=float(row["cur_prc"]),
                    volume=float(row["trde_qty"] if row.get("trde_qty") is not None else row.get("acc_trde_qty", 0) or 0),
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
