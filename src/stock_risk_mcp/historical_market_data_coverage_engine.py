from __future__ import annotations

from collections import defaultdict

from stock_risk_mcp.historical_market_data_models import (
    HistoricalChartRawResponse,
    HistoricalMarketDataCompletenessReport,
    HistoricalMarketDataCoverageReport,
    HistoricalMarketDataFreshnessReport,
    HistoricalMarketDataGapEntry,
    HistoricalMarketDataGapReport,
    HistoricalMarketDataReadinessStatus,
    HistoricalOhlcvRow,
)


def _gap(dataset_id: str, suffix: str, category: str, severity: str, message: str) -> HistoricalMarketDataGapEntry:
    return HistoricalMarketDataGapEntry(
        gap_id=f"{dataset_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def build_historical_market_data_coverage(
    dataset_id: str,
    raw_responses: list[HistoricalChartRawResponse],
    ohlcv_rows: list[HistoricalOhlcvRow],
) -> tuple[HistoricalMarketDataCoverageReport, HistoricalMarketDataFreshnessReport, HistoricalMarketDataCompletenessReport, HistoricalMarketDataGapReport]:
    covered_instrument_ids = sorted({row.instrument_id for row in ohlcv_rows})
    covered_intervals = sorted({row.interval.value for row in ohlcv_rows})
    duplicate_count = sum(1 for row in ohlcv_rows if "DUPLICATE_BAR" in row.quality_flags)
    out_of_order_count = sum(1 for row in ohlcv_rows if "OUT_OF_ORDER_SEQUENCE" in row.quality_flags)
    missing_field_count = sum(1 for row in ohlcv_rows if row.open_price is None or row.high_price is None or row.low_price is None)
    incomplete_request_ids = sorted(response.request_id for response in raw_responses if response.cont_yn == "Y")
    missing_instrument_ids: list[str] = []

    by_instrument: dict[str, int] = defaultdict(int)
    for row in ohlcv_rows:
        by_instrument[row.instrument_id] += 1
    for response in raw_responses:
        if by_instrument[response.canonical_instrument_id] == 0:
            missing_instrument_ids.append(response.canonical_instrument_id)

    readiness = HistoricalMarketDataReadinessStatus.COVERAGE_READY if ohlcv_rows else HistoricalMarketDataReadinessStatus.DATA_GAP
    gap_entries: list[HistoricalMarketDataGapEntry] = []
    if incomplete_request_ids:
        gap_entries.append(_gap(dataset_id, "CONTINUATION", "CONTINUATION_GAP", "WARNING", "continuation pages remain incomplete"))
    if missing_instrument_ids:
        gap_entries.append(_gap(dataset_id, "MISSING-INSTRUMENT", "DATA_GAP", "WARNING", "missing normalized rows for at least one request"))
    if duplicate_count:
        gap_entries.append(_gap(dataset_id, "DUPLICATE", "DUPLICATE_BAR", "WARNING", "duplicate bars detected"))

    newest = max((row.observed_at for row in ohlcv_rows), default=None)
    oldest = min((row.observed_at for row in ohlcv_rows), default=None)
    return (
        HistoricalMarketDataCoverageReport(
            report_id=f"{dataset_id}-COVERAGE-REPORT",
            readiness_status=readiness,
            covered_instrument_ids=covered_instrument_ids,
            covered_intervals=covered_intervals,
            missing_instrument_ids=sorted(set(missing_instrument_ids)),
            continuation_incomplete_request_ids=incomplete_request_ids,
            row_count=len(ohlcv_rows),
        ),
        HistoricalMarketDataFreshnessReport(
            report_id=f"{dataset_id}-FRESHNESS-REPORT",
            readiness_status=HistoricalMarketDataReadinessStatus.STALE if not ohlcv_rows else HistoricalMarketDataReadinessStatus.COVERAGE_READY,
            newest_observed_at=newest,
            oldest_observed_at=oldest,
            stale=not bool(ohlcv_rows),
        ),
        HistoricalMarketDataCompletenessReport(
            report_id=f"{dataset_id}-COMPLETENESS-REPORT",
            readiness_status=readiness,
            duplicate_row_count=duplicate_count,
            out_of_order_row_count=out_of_order_count,
            missing_field_row_count=missing_field_count,
            continuation_gap_count=len(incomplete_request_ids),
        ),
        HistoricalMarketDataGapReport(
            report_id=f"{dataset_id}-GAP-REPORT",
            readiness_status=HistoricalMarketDataReadinessStatus.RESEARCH_ONLY if gap_entries else readiness,
            gap_entries=gap_entries,
        ),
    )
