from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from pydantic import ValidationError

from stock_risk_mcp.historical_data_guard import build_historical_data_issue, validate_historical_data_source_path
from stock_risk_mcp.historical_data_models import (
    HistoricalDataAdjustmentPolicy,
    HistoricalDataGapReport,
    HistoricalDataIngestionConfig,
    HistoricalDataProviderProvenance,
    HistoricalDataQualityReport,
    HistoricalDataSourceDescriptor,
    HistoricalDataValidationReport,
    HistoricalGapCategory,
    HistoricalGapStatus,
    HistoricalMarketDataManifest,
    HistoricalOHLCVRecord,
    HistoricalQualityBucket,
    HistoricalValidationStatus,
)


def _rows_from_csv(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _rows_from_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _normalize_row(
    row: dict[str, object],
    *,
    source_descriptor: HistoricalDataSourceDescriptor,
    ingestion_batch_id: str,
) -> dict[str, object]:
    normalized = dict(row)
    normalized.setdefault("market", source_descriptor.market_profile_id)
    normalized.setdefault("timezone", source_descriptor.timezone)
    normalized.setdefault("currency", source_descriptor.currency)
    normalized.setdefault("source_id", source_descriptor.source_id)
    normalized.setdefault("ingestion_batch_id", ingestion_batch_id)
    return normalized


def _map_validation_error_to_issue(exc: ValidationError, *, row_number: int) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    for error in exc.errors():
        field_name = ".".join(str(part) for part in error["loc"])
        message = error["msg"]
        if field_name == "timestamp":
            category = HistoricalGapCategory.TIMEZONE_MISMATCH if "timezone" in message.lower() else HistoricalGapCategory.UNSAFE_SOURCE_PATH
        elif field_name in {"open", "high", "low", "close"}:
            category = HistoricalGapCategory.INVALID_OHLC
        elif field_name == "volume":
            category = HistoricalGapCategory.INVALID_VOLUME
        else:
            category = HistoricalGapCategory.UNSAFE_SOURCE_PATH
        issues.append(build_historical_data_issue(category, message, row_number=row_number, field_name=field_name))
    return issues


def parse_historical_data_records(
    source_descriptor: HistoricalDataSourceDescriptor,
    *,
    ingestion_batch_id: str,
) -> tuple[list[HistoricalOHLCVRecord], list[dict[str, object]]]:
    path, issues = validate_historical_data_source_path(source_descriptor)
    if path is None:
        return [], issues

    raw_rows = _rows_from_csv(path) if source_descriptor.source_type.value == "local_csv" else _rows_from_jsonl(path)
    records: list[HistoricalOHLCVRecord] = []
    for index, row in enumerate(raw_rows, start=1):
        payload = _normalize_row(
            row,
            source_descriptor=source_descriptor,
            ingestion_batch_id=ingestion_batch_id,
        )
        try:
            records.append(HistoricalOHLCVRecord.model_validate(payload))
        except ValidationError as exc:
            issues.extend(_map_validation_error_to_issue(exc, row_number=index))
    return records, issues


def build_historical_data_validation_report(
    *,
    ingestion_config: HistoricalDataIngestionConfig,
    source_descriptor: HistoricalDataSourceDescriptor,
    records: list[HistoricalOHLCVRecord],
    parse_issues: list[dict[str, object]],
    ingestion_batch_id: str,
) -> HistoricalDataValidationReport:
    issues = list(parse_issues)

    seen_keys: set[tuple[str, str, object]] = set()
    symbol_timestamps: dict[str, list[object]] = defaultdict(list)
    for record in records:
        if record.market != source_descriptor.market_profile_id:
            issues.append(
                build_historical_data_issue(
                    HistoricalGapCategory.MARKET_PROFILE_MISMATCH,
                    "record market must match source descriptor market profile",
                )
            )
        if record.currency != source_descriptor.currency:
            issues.append(
                build_historical_data_issue(
                    HistoricalGapCategory.CURRENCY_MISMATCH,
                    "record currency must match source descriptor currency",
                )
            )
        if record.timezone != source_descriptor.timezone:
            issues.append(
                build_historical_data_issue(
                    HistoricalGapCategory.TIMEZONE_MISMATCH,
                    "record timezone must match source descriptor timezone",
                )
            )
        key = (record.symbol, record.market, record.timestamp)
        if key in seen_keys:
            issues.append(
                build_historical_data_issue(
                    HistoricalGapCategory.DUPLICATE_RECORD,
                    "duplicate historical OHLCV record detected",
                )
            )
        else:
            seen_keys.add(key)
        symbol_timestamps[record.symbol].append(record.timestamp)

    for timestamps in symbol_timestamps.values():
        previous = None
        for timestamp in timestamps:
            if previous is not None and timestamp < previous:
                issues.append(
                    build_historical_data_issue(
                        HistoricalGapCategory.OUT_OF_ORDER_RECORD,
                        "historical OHLCV records must be ordered by timestamp within symbol",
                    )
                )
            previous = timestamp

    if issues:
        if ingestion_config.allow_report_only_downgrade:
            status = HistoricalValidationStatus.VALID_WITH_WARNINGS
            error_count = 0
            warning_count = len(issues)
            report_only = True
        else:
            status = HistoricalValidationStatus.INVALID
            error_count = len(issues)
            warning_count = 0
            report_only = False
    else:
        status = HistoricalValidationStatus.VALID
        error_count = 0
        warning_count = 0
        report_only = False

    return HistoricalDataValidationReport(
        validation_report_id=f"{ingestion_batch_id}-validation",
        ingestion_batch_id=ingestion_batch_id,
        strategy_track=ingestion_config.strategy_track,
        market_profile_id=source_descriptor.market_profile_id,
        validation_status=status,
        error_count=error_count,
        warning_count=warning_count,
        validation_issues=issues,
        report_only=report_only,
    )


def build_historical_data_quality_report(
    *,
    ingestion_batch_id: str,
    records: list[HistoricalOHLCVRecord],
    validation_report: HistoricalDataValidationReport,
    adjustment_policy: HistoricalDataAdjustmentPolicy,
) -> HistoricalDataQualityReport:
    issue_categories = [issue.get("category") for issue in validation_report.validation_issues]
    timestamps = [record.timestamp for record in records]
    quality_bucket = HistoricalQualityBucket.READY
    if validation_report.validation_status == HistoricalValidationStatus.INVALID:
        quality_bucket = HistoricalQualityBucket.BLOCKED
    elif validation_report.validation_status == HistoricalValidationStatus.VALID_WITH_WARNINGS:
        quality_bucket = HistoricalQualityBucket.REPORT_ONLY

    return HistoricalDataQualityReport(
        quality_report_id=f"{ingestion_batch_id}-quality",
        ingestion_batch_id=ingestion_batch_id,
        record_count=len(records),
        symbol_count=len({record.symbol for record in records}),
        market_count=len({record.market for record in records}),
        date_range_start=min(timestamps) if timestamps else None,
        date_range_end=max(timestamps) if timestamps else None,
        timezone_distribution=dict(Counter(record.timezone for record in records)),
        currency_distribution=dict(Counter(record.currency for record in records)),
        missing_value_count=0,
        duplicate_count=issue_categories.count(HistoricalGapCategory.DUPLICATE_RECORD.value),
        invalid_ohlc_count=issue_categories.count(HistoricalGapCategory.INVALID_OHLC.value),
        invalid_volume_count=issue_categories.count(HistoricalGapCategory.INVALID_VOLUME.value),
        out_of_order_count=issue_categories.count(HistoricalGapCategory.OUT_OF_ORDER_RECORD.value),
        missing_session_count=0,
        stale_batch_marker=False,
        adjustment_policy_summary={
            "price_adjustment_mode": adjustment_policy.price_adjustment_mode,
            "split_adjustment_expected": adjustment_policy.split_adjustment_expected,
            "dividend_adjustment_expected": adjustment_policy.dividend_adjustment_expected,
        },
        quality_bucket=quality_bucket,
        report_only=validation_report.report_only,
    )


def build_historical_data_gap_report(
    *,
    ingestion_config: HistoricalDataIngestionConfig,
    validation_report: HistoricalDataValidationReport,
    quality_report: HistoricalDataQualityReport,
    ingestion_batch_id: str,
) -> HistoricalDataGapReport:
    del quality_report
    categories = [
        HistoricalGapCategory(issue["category"])
        for issue in validation_report.validation_issues
    ]
    unique_categories = list(dict.fromkeys(categories))

    if not unique_categories:
        gap_status = HistoricalGapStatus.NO_GAPS
        blocking_gap_count = 0
        report_only_gap_count = 0
    elif ingestion_config.allow_report_only_downgrade:
        gap_status = HistoricalGapStatus.REPORT_ONLY_GAPS
        blocking_gap_count = 0
        report_only_gap_count = len(validation_report.validation_issues)
    else:
        gap_status = HistoricalGapStatus.BLOCKING_GAPS
        blocking_gap_count = len(validation_report.validation_issues)
        report_only_gap_count = 0

    return HistoricalDataGapReport(
        gap_report_id=f"{ingestion_batch_id}-gap",
        ingestion_batch_id=ingestion_batch_id,
        gap_status=gap_status,
        gap_categories=unique_categories,
        blocking_gap_count=blocking_gap_count,
        report_only_gap_count=report_only_gap_count,
        gaps=validation_report.validation_issues,
    )


def build_historical_data_manifest(
    *,
    ingestion_config: HistoricalDataIngestionConfig,
    source_descriptor: HistoricalDataSourceDescriptor,
    provider_provenance: HistoricalDataProviderProvenance,
    adjustment_policy: HistoricalDataAdjustmentPolicy,
    records: list[HistoricalOHLCVRecord],
    validation_report: HistoricalDataValidationReport,
    quality_report: HistoricalDataQualityReport,
    gap_report: HistoricalDataGapReport,
    audit_record_ids: list[str],
) -> HistoricalMarketDataManifest:
    source_file_path = Path(source_descriptor.local_file_path)
    source_file_hash = hashlib.sha256(source_file_path.read_bytes()).hexdigest()

    return HistoricalMarketDataManifest(
        manifest_id=f"{validation_report.ingestion_batch_id}-manifest",
        ingestion_batch_id=validation_report.ingestion_batch_id,
        source_descriptor_id=source_descriptor.source_descriptor_id,
        source_file_path=str(source_file_path),
        source_file_hash=source_file_hash,
        source_provenance=provider_provenance,
        strategy_track=ingestion_config.strategy_track,
        market_profile_id=source_descriptor.market_profile_id,
        symbol_count=len({record.symbol for record in records}),
        record_count=len(records),
        date_range_start=quality_report.date_range_start,
        date_range_end=quality_report.date_range_end,
        timezone=source_descriptor.timezone,
        currency=source_descriptor.currency,
        adjustment_policy=adjustment_policy,
        validation_report_id=validation_report.validation_report_id,
        quality_report_id=quality_report.quality_report_id,
        gap_report_id=gap_report.gap_report_id,
        audit_record_ids=audit_record_ids,
    )
