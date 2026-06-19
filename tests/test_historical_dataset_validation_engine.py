import copy

import pytest

from stock_risk_mcp.historical_dataset_validation_engine import build_historical_dataset_validation
from stock_risk_mcp.historical_dataset_validation_models import HistoricalDatasetValidationInput
from tests.test_historical_dataset_validation_models import historical_dataset_validation_fixture_payload


def build_input(payload=None):
    return HistoricalDatasetValidationInput.model_validate(payload or historical_dataset_validation_fixture_payload())


def _engine_payload():
    payload = historical_dataset_validation_fixture_payload()
    payload["validation_report"]["record_count"] = 0
    payload["validation_report"]["valid_record_count"] = 0
    payload["leakage_audit_report"]["audited_record_count"] = 0
    payload["leakage_audit_report"]["clean_record_count"] = 0
    payload["split_manifest"]["record_refs"] = []
    payload["split_manifest"]["train_record_refs"] = []
    payload["split_manifest"]["validation_record_refs"] = []
    payload["split_manifest"]["test_record_refs"] = []
    payload["split_manifest"]["train_record_count"] = 0
    payload["split_manifest"]["validation_record_count"] = 0
    payload["split_manifest"]["test_record_count"] = 0
    payload["coverage_report"]["record_count"] = 0
    payload["label_distribution_report"]["record_count"] = 0
    return payload


def _with_records(payload, count: int):
    base_record = payload["dataset_records"][0]
    records = []
    for index in range(count):
        record = copy.deepcopy(base_record)
        record["record_id"] = f"DATASET-RECORD-{index + 1}"
        record["replay_session_date"] = f"2026-06-{18 + index:02d}"
        record["replay_window_id"] = f"WINDOW-{index + 1}"
        record["replay_event_ids"] = [f"EVENT-{index + 1}"]
        record["source_manifest_ids"] = [f"MANIFEST-{index + 1}"]
        record["source_audit_record_ids"] = [f"AUDIT-{index + 1}"]
        record["provider_provenance_ids"] = [f"PROVENANCE-{index + 1}"]
        record["feature_block"]["block_id"] = f"FEATURE-BLOCK-{index + 1}"
        record["outcome_block"]["block_id"] = f"OUTCOME-BLOCK-{index + 1}"
        if index == 1:
            record["outcome_block"]["outcome_label"] = "OUTCOME_FAVORABLE"
        elif index == 2:
            record["outcome_block"]["outcome_label"] = "OUTCOME_ADVERSE"
        records.append(record)
    payload["dataset_records"] = records
    return payload


def test_build_historical_dataset_validation_success_path():
    payload = _with_records(_engine_payload(), 3)

    result = build_historical_dataset_validation(build_input(payload))

    assert result.validation_report.record_count == 3
    assert result.validation_report.valid_record_count == 3
    assert result.leakage_audit_report.feature_outcome_leakage_absent is True
    assert result.split_manifest.chronological is True
    assert result.coverage_report.record_count == 3
    assert result.label_distribution_report.record_count == 3


def test_build_historical_dataset_validation_reports_missing_feature_block_gap():
    validation_input = build_input(_with_records(_engine_payload(), 1))
    validation_input.dataset_records[0] = validation_input.dataset_records[0].model_copy(update={"feature_block": None})

    result = build_historical_dataset_validation(validation_input)

    assert any(gap.gap_category.value == "VALIDATION_MISSING_FEATURE_BLOCK" for gap in result.validation_gap_report.gaps)


def test_build_historical_dataset_validation_reports_missing_outcome_block_gap():
    validation_input = build_input(_with_records(_engine_payload(), 1))
    validation_input.dataset_records[0] = validation_input.dataset_records[0].model_copy(update={"outcome_block": None})

    result = build_historical_dataset_validation(validation_input)

    assert any(gap.gap_category.value == "VALIDATION_MISSING_OUTCOME_BLOCK" for gap in result.validation_gap_report.gaps)


def test_build_historical_dataset_validation_reports_missing_lineage_gap():
    payload = _with_records(_engine_payload(), 1)
    payload["dataset_records"][0]["source_manifest_ids"] = []

    result = build_historical_dataset_validation(build_input(payload))

    assert any(gap.gap_category.value == "VALIDATION_MISSING_LINEAGE" for gap in result.validation_gap_report.gaps)


@pytest.mark.parametrize(
    ("field_name", "gap_category"),
    [
        ("outcome_label", "VALIDATION_OUTCOME_LABEL_IN_FEATURES_DETECTED"),
        ("forward_return_pct", "VALIDATION_FORWARD_RETURN_IN_FEATURES_DETECTED"),
        ("max_favorable_excursion_pct", "VALIDATION_MFE_MAE_IN_FEATURES_DETECTED"),
        ("forward_close_price", "VALIDATION_POST_ANCHOR_ACTUAL_IN_FEATURES_DETECTED"),
    ],
)
def test_build_historical_dataset_validation_leakage_audit_detects_feature_leakage(field_name, gap_category):
    validation_input = build_input(_with_records(_engine_payload(), 1))
    feature_block = validation_input.dataset_records[0].feature_block.model_dump(mode="json")
    feature_block[field_name] = "OUTCOME_FAVORABLE" if field_name == "outcome_label" else 1.0
    validation_input.dataset_records[0] = validation_input.dataset_records[0].model_copy(update={"feature_block": feature_block})

    result = build_historical_dataset_validation(validation_input)

    assert result.leakage_audit_report.feature_outcome_leakage_absent is False
    assert any(gap.gap_category.value == gap_category for gap in result.validation_gap_report.gaps)


def test_build_historical_dataset_validation_split_success_path_and_chronology():
    payload = _with_records(_engine_payload(), 10)

    result = build_historical_dataset_validation(build_input(payload))

    assert result.split_manifest.train_record_count == 7
    assert result.split_manifest.validation_record_count == 1
    assert result.split_manifest.test_record_count == 2
    train_end = result.split_manifest.train_date_range_end
    validation_start = result.split_manifest.validation_date_range_start
    validation_end = result.split_manifest.validation_date_range_end
    test_start = result.split_manifest.test_date_range_start
    assert train_end <= validation_start
    assert validation_end <= test_start


def test_build_historical_dataset_validation_detects_duplicated_split_record():
    payload = _with_records(_engine_payload(), 3)
    payload["dataset_records"][1]["record_id"] = payload["dataset_records"][0]["record_id"]

    result = build_historical_dataset_validation(build_input(payload))

    assert any(gap.gap_category.value == "VALIDATION_SPLIT_RECORD_DUPLICATED" for gap in result.validation_gap_report.gaps)


def test_build_historical_dataset_validation_detects_split_partition_overlap():
    payload = _with_records(_engine_payload(), 3)
    payload["split_manifest"]["record_refs"] = [
        {
            "record_ref_id": "DATASET-SPLIT-RECORD-REF-1",
            "dataset_record_id": "DATASET-RECORD-1",
            "split_partition": "TRAIN",
            "replay_anchor_date": "2026-06-18",
            "symbol": "005930",
            "market": "KRX",
        },
        {
            "record_ref_id": "DATASET-SPLIT-RECORD-REF-2",
            "dataset_record_id": "DATASET-RECORD-1",
            "split_partition": "TEST",
            "replay_anchor_date": "2026-06-18",
            "symbol": "005930",
            "market": "KRX",
        },
    ]
    payload["split_manifest"]["train_record_refs"] = [payload["split_manifest"]["record_refs"][0]]
    payload["split_manifest"]["validation_record_refs"] = []
    payload["split_manifest"]["test_record_refs"] = [payload["split_manifest"]["record_refs"][1]]
    payload["split_manifest"]["train_record_count"] = 1
    payload["split_manifest"]["validation_record_count"] = 0
    payload["split_manifest"]["test_record_count"] = 1

    result = build_historical_dataset_validation(build_input(payload))

    assert any(gap.gap_category.value == "VALIDATION_SPLIT_PARTITION_OVERLAP" for gap in result.validation_gap_report.gaps)


def test_build_historical_dataset_validation_too_few_records_fail_closed():
    payload = _with_records(_engine_payload(), 2)

    result = build_historical_dataset_validation(build_input(payload))

    assert any(gap.gap_category.value == "VALIDATION_SPLIT_NOT_CHRONOLOGICAL" for gap in result.validation_gap_report.gaps)
    assert result.split_manifest.record_refs == []


def test_build_historical_dataset_validation_generates_coverage_report():
    payload = _with_records(_engine_payload(), 3)

    result = build_historical_dataset_validation(build_input(payload))

    assert result.coverage_report.records_by_symbol["005930"] == 3
    assert result.coverage_report.records_by_market["KRX"] == 3
    assert result.coverage_report.records_by_strategy_track["DOMESTIC_KR"] == 3


def test_build_historical_dataset_validation_generates_label_distribution_report():
    payload = _with_records(_engine_payload(), 3)

    result = build_historical_dataset_validation(build_input(payload))

    assert result.label_distribution_report.label_counts["OUTCOME_REPORT_ONLY"] == 1
    assert result.label_distribution_report.label_counts["OUTCOME_FAVORABLE"] == 1
    assert result.label_distribution_report.label_counts["OUTCOME_ADVERSE"] == 1
    assert result.label_distribution_report.label_percentages["OUTCOME_REPORT_ONLY"] == pytest.approx(1 / 3)


def test_build_historical_dataset_validation_rejects_unsafe_markers():
    payload = _with_records(_engine_payload(), 1)
    payload["audit_records"][0]["operator_context"] = "BUY NOW"

    result = build_historical_dataset_validation(build_input(payload))

    assert any(gap.gap_category.value == "VALIDATION_BUY_SELL_WORDING_DETECTED" for gap in result.validation_gap_report.gaps)


def test_build_historical_dataset_validation_rejects_parquet():
    payload = _with_records(_engine_payload(), 1)
    payload["dataset_export_manifest"]["export_formats"] = ["PARQUET"]

    with pytest.raises(ValueError, match="parquet"):
        build_historical_dataset_validation(build_input(payload))
