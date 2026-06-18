import pytest

from stock_risk_mcp.historical_data_models import (
    HistoricalDataGapReport,
    HistoricalDataSafetyBoundary,
    HistoricalMarketDataSnapshot,
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


def historical_snapshot_payload():
    return {
        "schema_version": "5.1-historical-market-data-snapshot",
        "snapshot_id": "historical-domestic-kr-1",
        "created_at": "2026-06-18T09:00:00+09:00",
        "ingestion_config": {
            "config_id": "historical-config-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile": market_profile_payload(),
            "source_type": "local_csv",
            "strict_validation_mode": True,
            "allow_report_only_downgrade": False,
            "currency_mismatch_policy": "FAIL_CLOSED",
            "duplicate_record_policy": "FAIL_CLOSED",
            "missing_session_policy": "FAIL_CLOSED",
            "stale_batch_policy": "FAIL_CLOSED",
            "unsupported_track_policy": "FAIL_CLOSED",
            "unsafe_source_policy": "FAIL_CLOSED",
        },
        "source_descriptor": {
            "source_descriptor_id": "source-desc-1",
            "source_type": "local_csv",
            "local_file_path": "fixtures/historical/domestic_kr_ohlcv.csv",
            "declared_format": "CSV",
            "declared_content_type": "text/csv",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "source_id": "KRX_MANUAL_EXPORT",
            "source_vendor_name": "KRX Manual Export",
            "source_reliability_tier": "OFFICIAL",
            "path_safety_class": "LOCAL_RELATIVE",
            "timezone": "Asia/Seoul",
            "currency": "KRW",
            "source_symbol_namespace": "KRX",
            "contains_adjusted_prices": False,
            "contains_unadjusted_prices": True,
            "contains_turnover": True,
            "contains_trade_value": True,
            "report_only": False,
        },
        "provider_provenance": {
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
        },
        "adjustment_policy": {
            "policy_id": "adjustment-policy-1",
            "price_adjustment_mode": "UNADJUSTED",
            "split_adjustment_expected": False,
            "dividend_adjustment_expected": False,
            "corporate_action_backfill_expected": False,
            "adjusted_close_required": False,
            "mixed_adjustment_state_allowed": False,
            "report_only_if_uncertain": True,
        },
        "safety_boundary": {},
        "records": [
            {
                "symbol": "005930",
                "market": "KRX",
                "timestamp": "2026-06-18T09:00:00+09:00",
                "timezone": "Asia/Seoul",
                "open": 70000,
                "high": 71000,
                "low": 69900,
                "close": 70500,
                "volume": 1000,
                "currency": "KRW",
                "source_id": "KRX_MANUAL_EXPORT",
                "ingestion_batch_id": "batch-1",
                "turnover": 70500000,
                "trade_value": 70500000,
            }
        ],
        "validation_report": {
            "validation_report_id": "validation-1",
            "ingestion_batch_id": "batch-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "validation_status": "VALID",
            "error_count": 0,
            "warning_count": 0,
            "validation_issues": [],
        },
        "gap_report": {
            "gap_report_id": "gap-1",
            "ingestion_batch_id": "batch-1",
            "gap_status": "NO_GAPS",
            "gap_categories": [],
            "blocking_gap_count": 0,
            "report_only_gap_count": 0,
            "gaps": [],
        },
        "quality_report": {
            "quality_report_id": "quality-1",
            "ingestion_batch_id": "batch-1",
            "record_count": 1,
            "symbol_count": 1,
            "market_count": 1,
            "date_range_start": "2026-06-18T09:00:00+09:00",
            "date_range_end": "2026-06-18T09:00:00+09:00",
            "timezone_distribution": {"Asia/Seoul": 1},
            "currency_distribution": {"KRW": 1},
            "missing_value_count": 0,
            "duplicate_count": 0,
            "invalid_ohlc_count": 0,
            "invalid_volume_count": 0,
            "out_of_order_count": 0,
            "missing_session_count": 0,
            "stale_batch_marker": False,
            "adjustment_policy_summary": {"price_adjustment_mode": "UNADJUSTED"},
            "quality_bucket": "READY",
        },
        "manifest": {
            "manifest_id": "manifest-1",
            "ingestion_batch_id": "batch-1",
            "source_descriptor_id": "source-desc-1",
            "source_file_path": "fixtures/historical/domestic_kr_ohlcv.csv",
            "source_file_hash": "sha256:fixture",
            "source_provenance": {
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
            },
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "symbol_count": 1,
            "record_count": 1,
            "date_range_start": "2026-06-18T09:00:00+09:00",
            "date_range_end": "2026-06-18T09:00:00+09:00",
            "timezone": "Asia/Seoul",
            "currency": "KRW",
            "adjustment_policy": {
                "policy_id": "adjustment-policy-1",
                "price_adjustment_mode": "UNADJUSTED",
                "split_adjustment_expected": False,
                "dividend_adjustment_expected": False,
                "corporate_action_backfill_expected": False,
                "adjusted_close_required": False,
                "mixed_adjustment_state_allowed": False,
                "report_only_if_uncertain": True,
            },
            "validation_report_id": "validation-1",
            "quality_report_id": "quality-1",
            "gap_report_id": "gap-1",
            "audit_record_ids": ["audit-1"],
        },
        "audit_records": [
            {
                "audit_record_id": "audit-1",
                "ingestion_batch_id": "batch-1",
                "source_descriptor_id": "source-desc-1",
                "created_at": "2026-06-18T09:01:00+09:00",
                "operator_context": "TEST",
                "local_file_path": "fixtures/historical/domestic_kr_ohlcv.csv",
                "local_file_hash": "sha256:fixture",
                "parser_version": "fixture-only",
                "validation_report_id": "validation-1",
                "quality_report_id": "quality-1",
                "gap_report_id": "gap-1",
            }
        ],
    }


def test_historical_data_fixture_constructs_valid_domestic_kr_local_csv_snapshot():
    snapshot = HistoricalMarketDataSnapshot.model_validate(historical_snapshot_payload())

    assert snapshot.ingestion_config.strategy_track.value == "DOMESTIC_KR"
    assert snapshot.ingestion_config.market_profile.base_currency == "KRW"
    assert snapshot.source_descriptor.source_type.value == "local_csv"
    assert snapshot.records[0].currency == "KRW"
    assert isinstance(snapshot.gap_report, HistoricalDataGapReport)


def test_historical_data_fixture_constructs_valid_domestic_kr_local_jsonl_snapshot():
    payload = historical_snapshot_payload()
    payload["ingestion_config"]["source_type"] = "local_jsonl"
    payload["source_descriptor"]["source_type"] = "local_jsonl"
    payload["source_descriptor"]["local_file_path"] = "fixtures/historical/domestic_kr_ohlcv.jsonl"
    payload["source_descriptor"]["declared_format"] = "JSONL"
    payload["source_descriptor"]["declared_content_type"] = "application/x-ndjson"
    payload["manifest"]["source_file_path"] = "fixtures/historical/domestic_kr_ohlcv.jsonl"
    payload["audit_records"][0]["local_file_path"] = "fixtures/historical/domestic_kr_ohlcv.jsonl"

    snapshot = HistoricalMarketDataSnapshot.model_validate(payload)

    assert snapshot.ingestion_config.source_type.value == "local_jsonl"
    assert snapshot.source_descriptor.source_type.value == "local_jsonl"
    assert snapshot.source_descriptor.local_file_path.endswith(".jsonl")


def test_historical_data_fixture_enforces_exact_schema_version():
    payload = historical_snapshot_payload()
    payload["schema_version"] = "5.1-historical-data-fixture"

    with pytest.raises(ValueError, match="schema_version must be exactly 5.1-historical-market-data-snapshot"):
        HistoricalMarketDataSnapshot.model_validate(payload)


def test_historical_data_fixture_requires_timezone_aware_timestamps():
    payload = historical_snapshot_payload()
    payload["records"][0]["timestamp"] = "2026-06-18T09:00:00"

    with pytest.raises(ValueError, match="timestamp must include timezone"):
        HistoricalMarketDataSnapshot.model_validate(payload)


def test_historical_data_safety_boundary_defaults_deny_network_provider_order_and_runtime_paths():
    boundary = HistoricalDataSafetyBoundary()

    assert boundary.network_access_allowed is False
    assert boundary.provider_api_allowed is False
    assert boundary.account_access_allowed is False
    assert boundary.credential_access_allowed is False
    assert boundary.token_access_allowed is False
    assert boundary.order_intent_allowed is False
    assert boundary.order_draft_allowed is False
    assert boundary.execution_approval_allowed is False
    assert boundary.cloud_llm_allowed is False
    assert boundary.local_model_runtime_allowed is False
    assert boundary.ml_training_allowed is False


def test_historical_data_fixture_allows_optional_provenance_datetime_to_be_null():
    payload = historical_snapshot_payload()
    payload["provider_provenance"]["local_export_timestamp"] = None
    payload["manifest"]["source_provenance"]["local_export_timestamp"] = None
    payload["quality_report"]["date_range_start"] = None
    payload["quality_report"]["date_range_end"] = None
    payload["manifest"]["date_range_start"] = None
    payload["manifest"]["date_range_end"] = None

    snapshot = HistoricalMarketDataSnapshot.model_validate(payload)

    assert snapshot.provider_provenance.local_export_timestamp is None
    assert snapshot.manifest.source_provenance.local_export_timestamp is None
    assert snapshot.quality_report.date_range_start is None
    assert snapshot.quality_report.date_range_end is None
    assert snapshot.manifest.date_range_start is None
    assert snapshot.manifest.date_range_end is None


def test_historical_data_fixture_preserves_timezone_content_type_and_source_name_casing():
    snapshot = HistoricalMarketDataSnapshot.model_validate(historical_snapshot_payload())

    assert snapshot.source_descriptor.timezone == "Asia/Seoul"
    assert snapshot.source_descriptor.declared_content_type == "text/csv"
    assert snapshot.source_descriptor.source_vendor_name == "KRX Manual Export"
    assert snapshot.provider_provenance.source_name == "KRX Manual Export"


@pytest.mark.parametrize(
    ("source_type", "expected_message"),
    [
        ("local_parquet", "source_type must be one of local_csv or local_jsonl"),
        ("remote_url", "source_type must be one of local_csv or local_jsonl"),
        ("provider_api", "source_type must be one of local_csv or local_jsonl"),
    ],
)
def test_historical_data_fixture_rejects_unsupported_source_types(source_type, expected_message):
    payload = historical_snapshot_payload()
    payload["ingestion_config"]["source_type"] = source_type
    payload["source_descriptor"]["source_type"] = source_type

    with pytest.raises(ValueError, match=expected_message):
        HistoricalMarketDataSnapshot.model_validate(payload)


@pytest.mark.parametrize(
    "local_file_path",
    [
        "https://example.com/historical.csv",
        "s3://bucket/historical.csv",
    ],
)
def test_historical_data_fixture_rejects_non_local_file_path_patterns(local_file_path):
    payload = historical_snapshot_payload()
    payload["source_descriptor"]["local_file_path"] = local_file_path

    with pytest.raises(ValueError, match="local_file_path must be a local path"):
        HistoricalMarketDataSnapshot.model_validate(payload)


@pytest.mark.parametrize(
    ("source_type", "local_file_path", "expected_message"),
    [
        ("local_csv", "fixtures/historical/domestic_kr_ohlcv.jsonl", "local_csv sources must use a .csv local_file_path"),
        ("local_jsonl", "fixtures/historical/domestic_kr_ohlcv.csv", "local_jsonl sources must use a .jsonl local_file_path"),
    ],
)
def test_historical_data_fixture_rejects_source_type_and_extension_mismatches(
    source_type, local_file_path, expected_message
):
    payload = historical_snapshot_payload()
    payload["ingestion_config"]["source_type"] = source_type
    payload["source_descriptor"]["source_type"] = source_type
    payload["source_descriptor"]["local_file_path"] = local_file_path
    payload["manifest"]["source_file_path"] = local_file_path
    payload["audit_records"][0]["local_file_path"] = local_file_path

    with pytest.raises(ValueError, match=expected_message):
        HistoricalMarketDataSnapshot.model_validate(payload)


def test_historical_data_fixture_rejects_provider_style_local_file_path_patterns():
    payload = historical_snapshot_payload()
    payload["source_descriptor"]["local_file_path"] = "provider_api:krx_manual_export.csv"
    payload["manifest"]["source_file_path"] = "provider_api:krx_manual_export.csv"
    payload["audit_records"][0]["local_file_path"] = "provider_api:krx_manual_export.csv"

    with pytest.raises(ValueError, match="local_file_path must be a local path"):
        HistoricalMarketDataSnapshot.model_validate(payload)


def test_historical_data_fixture_rejects_required_identifier_null_instead_of_coercing_to_string():
    payload = historical_snapshot_payload()
    payload["validation_report"]["validation_report_id"] = None

    with pytest.raises(ValueError, match="validation_report_id"):
        HistoricalMarketDataSnapshot.model_validate(payload)


@pytest.mark.parametrize(
    ("field_path", "remote_path"),
    [
        (("manifest", "source_file_path"), "https://example.com/manifest.csv"),
        (("audit_records", 0, "local_file_path"), "s3://bucket/audit.csv"),
    ],
)
def test_historical_data_fixture_rejects_remote_manifest_and_audit_paths(field_path, remote_path):
    payload = historical_snapshot_payload()
    target = payload
    for key in field_path[:-1]:
        target = target[key]
    target[field_path[-1]] = remote_path

    with pytest.raises(ValueError, match="local path"):
        HistoricalMarketDataSnapshot.model_validate(payload)


@pytest.mark.parametrize(
    ("field_path", "remote_path"),
    [
        (("manifest", "source_file_path"), "https://example.com/drift.csv"),
        (("audit_records", 0, "local_file_path"), "https://example.com/drift.csv"),
    ],
)
def test_historical_data_fixture_rejects_remote_path_drift_from_descriptor(field_path, remote_path):
    payload = historical_snapshot_payload()
    payload["source_descriptor"]["local_file_path"] = "fixtures/historical/domestic_kr_ohlcv.csv"
    target = payload
    for key in field_path[:-1]:
        target = target[key]
    target[field_path[-1]] = remote_path

    with pytest.raises(ValueError, match="local path"):
        HistoricalMarketDataSnapshot.model_validate(payload)


@pytest.mark.parametrize(
    ("field_path", "value", "expected_message"),
    [
        (("records", 0, "ingestion_batch_id"), "batch-2", "record ingestion_batch_id must match"),
        (("validation_report", "ingestion_batch_id"), "batch-2", "validation_report ingestion_batch_id must match"),
        (("gap_report", "ingestion_batch_id"), "batch-2", "gap_report ingestion_batch_id must match"),
        (("quality_report", "ingestion_batch_id"), "batch-2", "quality_report ingestion_batch_id must match"),
        (("manifest", "ingestion_batch_id"), "batch-2", "manifest ingestion_batch_id must match"),
        (("audit_records", 0, "ingestion_batch_id"), "batch-2", "audit record ingestion_batch_id must match"),
    ],
)
def test_historical_data_fixture_rejects_ingestion_batch_id_mismatches(field_path, value, expected_message):
    payload = historical_snapshot_payload()
    target = payload
    for key in field_path[:-1]:
        target = target[key]
    target[field_path[-1]] = value

    with pytest.raises(ValueError, match=expected_message):
        HistoricalMarketDataSnapshot.model_validate(payload)


@pytest.mark.parametrize(
    ("field_path", "value", "expected_message"),
    [
        (("manifest", "validation_report_id"), "validation-2", "manifest validation_report_id must match"),
        (("manifest", "quality_report_id"), "quality-2", "manifest quality_report_id must match"),
        (("manifest", "gap_report_id"), "gap-2", "manifest gap_report_id must match"),
        (("manifest", "audit_record_ids"), ["audit-2"], "manifest audit_record_ids must match"),
    ],
)
def test_historical_data_fixture_rejects_manifest_link_mismatches(field_path, value, expected_message):
    payload = historical_snapshot_payload()
    target = payload
    for key in field_path[:-1]:
        target = target[key]
    target[field_path[-1]] = value

    with pytest.raises(ValueError, match=expected_message):
        HistoricalMarketDataSnapshot.model_validate(payload)


@pytest.mark.parametrize(
    ("field_path", "expected_message"),
    [
        (("validation_report", "read_only"), "validation report must remain read_only"),
        (("validation_report", "non_executable"), "validation report must remain non_executable"),
        (("gap_report", "read_only"), "gap report must remain read_only"),
        (("gap_report", "non_executable"), "gap report must remain non_executable"),
        (("quality_report", "read_only"), "quality report must remain read_only"),
        (("quality_report", "non_executable"), "quality report must remain non_executable"),
        (("manifest", "read_only"), "manifest must remain read_only"),
        (("manifest", "non_executable"), "manifest must remain non_executable"),
        (("manifest", "no_network"), "manifest must remain no_network"),
        (("manifest", "no_provider_api"), "manifest must remain no_provider_api"),
        (("manifest", "no_order"), "manifest must remain no_order"),
    ],
)
def test_historical_data_fixture_rejects_fail_open_report_and_manifest_flags(field_path, expected_message):
    payload = historical_snapshot_payload()
    target = payload
    for key in field_path[:-1]:
        target = target[key]
    target[field_path[-1]] = False if field_path[-1] in {"read_only", "non_executable", "no_network", "no_provider_api", "no_order"} else None
    if field_path[-1] in {"read_only", "non_executable"}:
        target[field_path[-1]] = False

    with pytest.raises(ValueError, match=expected_message):
        HistoricalMarketDataSnapshot.model_validate(payload)


@pytest.mark.parametrize(
    ("field_name", "value", "expected_message"),
    [
        ("network_access_allowed", True, "network_access_allowed must remain false"),
        ("provider_api_allowed", True, "provider_api_allowed must remain false"),
        ("read_only", False, "historical ingestion config must remain read_only"),
        ("non_executable", False, "historical ingestion config must remain non_executable"),
    ],
)
def test_historical_data_fixture_rejects_fail_open_ingestion_config_flags(field_name, value, expected_message):
    payload = historical_snapshot_payload()
    payload["ingestion_config"][field_name] = value

    with pytest.raises(ValueError, match=expected_message):
        HistoricalMarketDataSnapshot.model_validate(payload)


@pytest.mark.parametrize(
    ("field_name", "value", "expected_message"),
    [
        ("read_only", False, "historical source descriptor must remain read_only"),
        ("non_executable", False, "historical source descriptor must remain non_executable"),
    ],
)
def test_historical_data_fixture_rejects_fail_open_source_descriptor_flags(field_name, value, expected_message):
    payload = historical_snapshot_payload()
    payload["source_descriptor"][field_name] = value

    with pytest.raises(ValueError, match=expected_message):
        HistoricalMarketDataSnapshot.model_validate(payload)


@pytest.mark.parametrize(
    ("field_name", "value", "expected_message"),
    [
        ("read_only", False, "audit record must remain read_only"),
        ("non_executable", False, "audit record must remain non_executable"),
        ("no_network", False, "audit record must remain no_network"),
        ("no_provider_api", False, "audit record must remain no_provider_api"),
    ],
)
def test_historical_data_fixture_rejects_fail_open_audit_record_flags(field_name, value, expected_message):
    payload = historical_snapshot_payload()
    payload["audit_records"][0][field_name] = value

    with pytest.raises(ValueError, match=expected_message):
        HistoricalMarketDataSnapshot.model_validate(payload)
