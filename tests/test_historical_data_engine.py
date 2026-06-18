import json

from stock_risk_mcp.historical_data_engine import (
    build_historical_data_gap_report,
    build_historical_data_manifest,
    build_historical_data_quality_report,
    build_historical_data_validation_report,
    parse_historical_data_records,
)
from stock_risk_mcp.historical_data_models import (
    HistoricalDataAdjustmentPolicy,
    HistoricalDataIngestionConfig,
    HistoricalDataProviderProvenance,
    HistoricalDataSourceDescriptor,
    HistoricalGapStatus,
    HistoricalQualityBucket,
)


def market_profile_payload():
    return {
        "market_id": "KRX",
        "country": "KR",
        "base_currency": "KRW",
        "exchange_session_profile": "KRX_CASH",
        "trading_hours": "09:00-15:30",
        "settlement_cash_availability": "T+2",
        "fee_tax_profile_reference": "profiles/domestic_kr_fee_tax.json",
        "realtime_data_profile_reference": "profiles/domestic_kr_realtime.json",
        "provider_capability_reference": "profiles/domestic_kr_local_file_only.json",
    }


def build_ingestion_config(source_type: str = "local_csv", allow_report_only_downgrade: bool = False):
    return HistoricalDataIngestionConfig.model_validate(
        {
            "config_id": "historical-config-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile": market_profile_payload(),
            "source_type": source_type,
            "strict_validation_mode": True,
            "allow_report_only_downgrade": allow_report_only_downgrade,
            "currency_mismatch_policy": "FAIL_CLOSED",
            "duplicate_record_policy": "FAIL_CLOSED",
            "missing_session_policy": "FAIL_CLOSED",
            "stale_batch_policy": "FAIL_CLOSED",
            "unsupported_track_policy": "FAIL_CLOSED",
            "unsafe_source_policy": "FAIL_CLOSED",
        }
    )


def build_source_descriptor(local_file_path: str, source_type: str = "local_csv"):
    return HistoricalDataSourceDescriptor.model_validate(
        {
            "source_descriptor_id": "source-desc-1",
            "source_type": source_type,
            "local_file_path": local_file_path,
            "declared_format": "CSV" if source_type == "local_csv" else "JSONL",
            "declared_content_type": "text/csv" if source_type == "local_csv" else "application/x-ndjson",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "source_id": "KRX_MANUAL_EXPORT",
            "source_vendor_name": "KRX Manual Export",
            "source_reliability_tier": "OFFICIAL",
            "path_safety_class": "LOCAL_TMP",
            "timezone": "Asia/Seoul",
            "currency": "KRW",
            "source_symbol_namespace": "KRX",
            "contains_adjusted_prices": False,
            "contains_unadjusted_prices": True,
            "contains_turnover": True,
            "contains_trade_value": True,
            "report_only": False,
        }
    )


def build_provider_provenance():
    return HistoricalDataProviderProvenance.model_validate(
        {
            "provenance_id": "provenance-1",
            "source_family": "KRX_MANUAL_EXPORT",
            "source_name": "KRX Manual Export",
            "source_tier": "OFFICIAL",
            "acquisition_mode": "LOCAL_FILE",
            "original_export_context": "MANUAL_DOWNLOAD",
            "local_export_timestamp": "2026-06-18T08:59:00+09:00",
            "manual_or_automated_origin": "MANUAL",
            "requires_reconciliation": False,
            "official_source_reference": "KRX_EXPORT_PORTAL",
            "notes": "Local offline fixture",
        }
    )


def build_adjustment_policy():
    return HistoricalDataAdjustmentPolicy.model_validate(
        {
            "policy_id": "adjustment-policy-1",
            "price_adjustment_mode": "UNADJUSTED",
            "split_adjustment_expected": False,
            "dividend_adjustment_expected": False,
            "corporate_action_backfill_expected": False,
            "adjusted_close_required": False,
            "mixed_adjustment_state_allowed": False,
            "report_only_if_uncertain": True,
        }
    )


def test_historical_data_engine_parses_local_csv_and_builds_ready_reports(tmp_path):
    csv_file = tmp_path / "ohlcv.csv"
    csv_file.write_text(
        "symbol,timestamp,open,high,low,close,volume,turnover,trade_value\n"
        "005930,2026-06-18T09:00:00+09:00,70000,71000,69900,70500,1000,70500000,70500000\n"
        "005930,2026-06-19T09:00:00+09:00,70600,71500,70500,71200,1500,106800000,106800000\n",
        encoding="utf-8",
    )
    ingestion_config = build_ingestion_config()
    source_descriptor = build_source_descriptor(str(csv_file))

    records, parse_issues = parse_historical_data_records(source_descriptor, ingestion_batch_id="batch-1")
    validation = build_historical_data_validation_report(
        ingestion_config=ingestion_config,
        source_descriptor=source_descriptor,
        records=records,
        parse_issues=parse_issues,
        ingestion_batch_id="batch-1",
    )
    quality = build_historical_data_quality_report(
        ingestion_batch_id="batch-1",
        records=records,
        validation_report=validation,
        adjustment_policy=build_adjustment_policy(),
    )
    gap = build_historical_data_gap_report(
        ingestion_config=ingestion_config,
        validation_report=validation,
        quality_report=quality,
        ingestion_batch_id="batch-1",
    )
    manifest = build_historical_data_manifest(
        ingestion_config=ingestion_config,
        source_descriptor=source_descriptor,
        provider_provenance=build_provider_provenance(),
        adjustment_policy=build_adjustment_policy(),
        records=records,
        validation_report=validation,
        quality_report=quality,
        gap_report=gap,
        audit_record_ids=["audit-1"],
    )

    assert parse_issues == []
    assert len(records) == 2
    assert validation.validation_status.value == "VALID"
    assert quality.record_count == 2
    assert quality.quality_bucket == HistoricalQualityBucket.READY
    assert gap.gap_status == HistoricalGapStatus.NO_GAPS
    assert manifest.record_count == 2
    assert manifest.symbol_count == 1
    assert manifest.source_file_path == str(csv_file)


def test_historical_data_engine_parses_local_jsonl_and_downgrades_currency_mismatch_to_report_only(tmp_path):
    jsonl_file = tmp_path / "ohlcv.jsonl"
    jsonl_file.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "symbol": "005930",
                        "timestamp": "2026-06-18T09:00:00+09:00",
                        "open": 70000,
                        "high": 71000,
                        "low": 69900,
                        "close": 70500,
                        "volume": 1000,
                        "currency": "USD",
                    }
                )
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    ingestion_config = build_ingestion_config(source_type="local_jsonl", allow_report_only_downgrade=True)
    source_descriptor = build_source_descriptor(str(jsonl_file), source_type="local_jsonl")

    records, parse_issues = parse_historical_data_records(source_descriptor, ingestion_batch_id="batch-2")
    validation = build_historical_data_validation_report(
        ingestion_config=ingestion_config,
        source_descriptor=source_descriptor,
        records=records,
        parse_issues=parse_issues,
        ingestion_batch_id="batch-2",
    )
    quality = build_historical_data_quality_report(
        ingestion_batch_id="batch-2",
        records=records,
        validation_report=validation,
        adjustment_policy=build_adjustment_policy(),
    )
    gap = build_historical_data_gap_report(
        ingestion_config=ingestion_config,
        validation_report=validation,
        quality_report=quality,
        ingestion_batch_id="batch-2",
    )

    assert parse_issues == []
    assert len(records) == 1
    assert validation.validation_status.value == "VALID_WITH_WARNINGS"
    assert validation.warning_count == 1
    assert quality.quality_bucket == HistoricalQualityBucket.REPORT_ONLY
    assert gap.gap_status == HistoricalGapStatus.REPORT_ONLY_GAPS
    assert [item.value for item in gap.gap_categories] == ["CURRENCY_MISMATCH"]
