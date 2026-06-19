import copy

import pytest

from stock_risk_mcp.historical_dataset_readiness_engine import build_historical_dataset_readiness
from stock_risk_mcp.historical_dataset_readiness_models import HistoricalDatasetReadinessInput
from tests.test_historical_dataset_readiness_models import historical_dataset_readiness_fixture_payload


def build_input(payload=None):
    return HistoricalDatasetReadinessInput.model_validate(payload or historical_dataset_readiness_fixture_payload())


def _engine_payload():
    payload = historical_dataset_readiness_fixture_payload()
    payload["readiness_report"]["record_count"] = 0
    payload["readiness_report"]["blocking_gate_count"] = 0
    payload["readiness_report"]["warning_count"] = 0
    payload["readiness_report"]["warnings"] = []
    payload["split_quality_report"]["train_record_count"] = 0
    payload["split_quality_report"]["validation_record_count"] = 0
    payload["split_quality_report"]["test_record_count"] = 0
    payload["imbalance_report"]["label_counts"] = {}
    payload["imbalance_report"]["label_percentages"] = {}
    payload["imbalance_report"]["split_label_counts"] = {}
    payload["imbalance_report"]["warning_count"] = 0
    payload["imbalance_report"]["warnings"] = []
    payload["baseline_evaluation_report"]["accuracy"] = None
    payload["baseline_evaluation_report"]["label_coverage"] = None
    payload["baseline_evaluation_report"]["confusion_matrix_counts"] = {}
    payload["baseline_evaluation_report"]["split_metric_summary"] = {}
    payload["readiness_gap_report"]["gap_status"] = "NO_GAPS"
    payload["readiness_gap_report"]["gap_categories"] = []
    payload["readiness_gap_report"]["blocking_gap_count"] = 0
    payload["readiness_gap_report"]["report_only_gap_count"] = 0
    payload["readiness_gap_report"]["gaps"] = []
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
        record["scanner_replay_candidate_seed_id"] = f"SEED-{index + 1}"
        record["outcome_observation_id"] = f"OBS-{index + 1}"
        record["feature_block"]["block_id"] = f"FEATURE-BLOCK-{index + 1}"
        record["feature_block"]["replay_context_id"] = f"REPLAY-CONTEXT-{index + 1}"
        record["feature_block"]["scanner_replay_input_id"] = f"SCANNER-REPLAY-INPUT-{index + 1}"
        record["outcome_block"]["block_id"] = f"OUTCOME-BLOCK-{index + 1}"
        record["outcome_block"]["sessions_observed"] = 5
        if index < 3:
            record["symbol"] = "005930"
        elif index < 5:
            record["symbol"] = "000660"
        else:
            record["symbol"] = "035420"
        if index in {0, 1, 2, 5}:
            record["outcome_block"]["outcome_label"] = "OUTCOME_FAVORABLE"
        elif index == 3:
            record["outcome_block"]["outcome_label"] = "OUTCOME_ADVERSE"
        else:
            record["outcome_block"]["outcome_label"] = "OUTCOME_REPORT_ONLY"
        records.append(record)
    payload["dataset_records"] = records
    return payload


def _split_refs_for_records(records):
    train = []
    validation = []
    test = []
    for index, record in enumerate(records):
        ref = {
            "record_ref_id": f"DATASET-SPLIT-RECORD-REF-{index + 1}",
            "dataset_record_id": record["record_id"],
            "split_partition": "TRAIN" if index < 4 else "VALIDATION" if index == 4 else "TEST",
            "replay_anchor_date": record["replay_session_date"],
            "symbol": record["symbol"],
            "market": record["market"],
        }
        if ref["split_partition"] == "TRAIN":
            train.append(ref)
        elif ref["split_partition"] == "VALIDATION":
            validation.append(ref)
        else:
            test.append(ref)
    return train, validation, test, train + validation + test


def _set_split_manifest_from_records(payload):
    train, validation, test, all_refs = _split_refs_for_records(payload["dataset_records"])
    payload["split_manifest"]["train_record_refs"] = train
    payload["split_manifest"]["validation_record_refs"] = validation
    payload["split_manifest"]["test_record_refs"] = test
    payload["split_manifest"]["record_refs"] = all_refs
    payload["split_manifest"]["train_record_count"] = len(train)
    payload["split_manifest"]["validation_record_count"] = len(validation)
    payload["split_manifest"]["test_record_count"] = len(test)
    payload["split_manifest"]["train_symbol_count"] = len({item["symbol"] for item in train})
    payload["split_manifest"]["validation_symbol_count"] = len({item["symbol"] for item in validation})
    payload["split_manifest"]["test_symbol_count"] = len({item["symbol"] for item in test})
    payload["split_manifest"]["train_date_range_start"] = train[0]["replay_anchor_date"] if train else None
    payload["split_manifest"]["train_date_range_end"] = train[-1]["replay_anchor_date"] if train else None
    payload["split_manifest"]["validation_date_range_start"] = validation[0]["replay_anchor_date"] if validation else None
    payload["split_manifest"]["validation_date_range_end"] = validation[-1]["replay_anchor_date"] if validation else None
    payload["split_manifest"]["test_date_range_start"] = test[0]["replay_anchor_date"] if test else None
    payload["split_manifest"]["test_date_range_end"] = test[-1]["replay_anchor_date"] if test else None
    return payload


def test_build_historical_dataset_readiness_success_path():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))

    result = build_historical_dataset_readiness(build_input(payload))

    assert result.readiness_report.record_count == 6
    assert result.readiness_report.blocking_gate_count == 0
    assert result.split_quality_report.train_record_count == 4
    assert result.imbalance_report.label_counts["OUTCOME_FAVORABLE"] == 4
    assert result.baseline_evaluation_report.accuracy is not None
    assert any(gap.gap_category.value == "READINESS_REPORT_GENERATED" for gap in result.readiness_gap_report.gaps)


def test_build_historical_dataset_readiness_reports_missing_validation_report_gap():
    readiness_input = build_input(_set_split_manifest_from_records(_with_records(_engine_payload(), 1)))
    readiness_input = readiness_input.model_copy(update={"validation_report": None})

    result = build_historical_dataset_readiness(readiness_input)

    assert any(gap.gap_category.value == "READINESS_MISSING_VALIDATION_REPORT" for gap in result.readiness_gap_report.gaps)


def test_build_historical_dataset_readiness_reports_missing_leakage_audit_gap():
    readiness_input = build_input(_set_split_manifest_from_records(_with_records(_engine_payload(), 1)))
    readiness_input = readiness_input.model_copy(update={"leakage_audit_report": None})

    result = build_historical_dataset_readiness(readiness_input)

    assert any(gap.gap_category.value == "READINESS_MISSING_LEAKAGE_AUDIT" for gap in result.readiness_gap_report.gaps)


def test_build_historical_dataset_readiness_reports_missing_split_manifest_gap():
    readiness_input = build_input(_with_records(_engine_payload(), 1))
    readiness_input = readiness_input.model_copy(update={"split_manifest": None})

    result = build_historical_dataset_readiness(readiness_input)

    assert any(gap.gap_category.value == "READINESS_MISSING_SPLIT_MANIFEST" for gap in result.readiness_gap_report.gaps)


def test_build_historical_dataset_readiness_reports_validation_not_clean_gap():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 2))
    payload["validation_report"]["blocked_count"] = 1

    result = build_historical_dataset_readiness(build_input(payload))

    assert any(gap.gap_category.value == "READINESS_VALIDATION_NOT_CLEAN" for gap in result.readiness_gap_report.gaps)


def test_build_historical_dataset_readiness_reports_leakage_audit_not_clean_gap():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 2))
    payload["leakage_audit_report"]["feature_outcome_leakage_absent"] = False
    payload["leakage_audit_report"]["blocked_record_count"] = 1

    result = build_historical_dataset_readiness(build_input(payload))

    assert any(gap.gap_category.value == "READINESS_LEAKAGE_AUDIT_NOT_CLEAN" for gap in result.readiness_gap_report.gaps)


def test_build_historical_dataset_readiness_generates_split_quality_report():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))

    result = build_historical_dataset_readiness(build_input(payload))

    assert result.split_quality_report.chronological_split is True
    assert result.split_quality_report.train_record_count == 4
    assert result.split_quality_report.validation_record_count == 1
    assert result.split_quality_report.test_record_count == 1
    assert result.split_quality_report.train_symbol_count == 2
    assert result.split_quality_report.train_label_distribution["OUTCOME_FAVORABLE"] == 3


def test_build_historical_dataset_readiness_detects_random_shuffle():
    readiness_input = build_input(_set_split_manifest_from_records(_with_records(_engine_payload(), 6)))
    readiness_input = readiness_input.model_copy(
        update={"split_manifest": readiness_input.split_manifest.model_copy(update={"random_shuffle_used": True})}
    )

    result = build_historical_dataset_readiness(readiness_input)

    assert any(gap.gap_category.value == "READINESS_SPLIT_RANDOM_SHUFFLE_DETECTED" for gap in result.readiness_gap_report.gaps)


def test_build_historical_dataset_readiness_detects_split_overlap():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))
    overlapping = copy.deepcopy(payload["split_manifest"]["record_refs"][0])
    overlapping["record_ref_id"] = "DATASET-SPLIT-RECORD-REF-X"
    overlapping["split_partition"] = "TEST"
    payload["split_manifest"]["record_refs"].append(overlapping)
    payload["split_manifest"]["test_record_refs"].append(overlapping)
    payload["split_manifest"]["test_record_count"] = len(payload["split_manifest"]["test_record_refs"])

    result = build_historical_dataset_readiness(build_input(payload))

    assert any(gap.gap_category.value == "READINESS_SPLIT_PARTITION_OVERLAP" for gap in result.readiness_gap_report.gaps)


def test_build_historical_dataset_readiness_detects_duplicated_record_ids():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))
    payload["split_manifest"]["record_refs"][1]["dataset_record_id"] = payload["split_manifest"]["record_refs"][0]["dataset_record_id"]
    payload["split_manifest"]["train_record_refs"][1]["dataset_record_id"] = payload["split_manifest"]["train_record_refs"][0]["dataset_record_id"]

    result = build_historical_dataset_readiness(build_input(payload))

    assert any(gap.gap_category.value == "READINESS_SPLIT_DUPLICATED_RECORD_ID" for gap in result.readiness_gap_report.gaps)


def test_build_historical_dataset_readiness_generates_imbalance_report():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))

    result = build_historical_dataset_readiness(build_input(payload))

    assert result.imbalance_report.label_counts["OUTCOME_FAVORABLE"] == 4
    assert result.imbalance_report.split_label_counts["TRAIN"]["OUTCOME_FAVORABLE"] == 3
    assert result.imbalance_report.split_label_percentages["TRAIN"]["OUTCOME_FAVORABLE"] == pytest.approx(0.75)


def test_build_historical_dataset_readiness_warns_on_severe_imbalance():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 5))
    for record in payload["dataset_records"]:
        record["outcome_block"]["outcome_label"] = "OUTCOME_FAVORABLE"

    result = build_historical_dataset_readiness(build_input(payload))

    assert result.imbalance_report.severe_imbalance_warning is True
    assert any(gap.gap_category.value == "READINESS_LABEL_IMBALANCE_WARNING" for gap in result.readiness_gap_report.gaps)


def test_build_historical_dataset_readiness_warns_on_low_label_coverage():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 2))
    payload["readiness_config"]["minimum_label_coverage"] = 3

    result = build_historical_dataset_readiness(build_input(payload))

    assert result.imbalance_report.low_label_coverage_warning is True
    assert any(gap.gap_category.value == "READINESS_LABEL_COVERAGE_TOO_LOW" for gap in result.readiness_gap_report.gaps)


def test_build_historical_dataset_readiness_evaluates_majority_label_baseline():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))

    result = build_historical_dataset_readiness(build_input(payload))

    assert "MAJORITY_LABEL_BASELINE" in result.baseline_evaluation_report.baseline_names
    assert result.baseline_evaluation_report.confusion_matrix_counts["OUTCOME_FAVORABLE->OUTCOME_FAVORABLE"] >= 1


def test_build_historical_dataset_readiness_evaluates_per_symbol_majority_baseline():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))

    result = build_historical_dataset_readiness(build_input(payload))

    assert result.baseline_evaluation_report.split_metric_summary["TEST:PER_SYMBOL_MAJORITY_LABEL_BASELINE"]["accuracy"] >= 0.0


def test_build_historical_dataset_readiness_keeps_prior_distribution_and_no_skill_report_only():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))

    result = build_historical_dataset_readiness(build_input(payload))

    assert result.baseline_evaluation_report.split_metric_summary["TEST:PRIOR_DISTRIBUTION_BASELINE"]["label_coverage"] == pytest.approx(1.0)
    assert result.baseline_evaluation_report.split_metric_summary["TEST:NO_SKILL_BASELINE"]["label_coverage"] == pytest.approx(1.0)


def test_build_historical_dataset_readiness_baseline_report_has_no_learned_artifact_or_model_weights():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))

    result = build_historical_dataset_readiness(build_input(payload))

    assert result.baseline_evaluation_report.trained_model_artifact_present is False
    assert result.baseline_evaluation_report.model_weights_present is False


def test_build_historical_dataset_readiness_rejects_ml_training_trigger():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))
    payload["audit_records"][0]["operator_context"] = "training-run"

    result = build_historical_dataset_readiness(build_input(payload))

    assert any(gap.gap_category.value == "READINESS_ML_TRAINING_TRIGGER_NOT_ALLOWED" for gap in result.readiness_gap_report.gaps)


def test_build_historical_dataset_readiness_rejects_ml_ready_tensor_export_marker():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))
    payload["audit_records"][0]["source_path"] = "fixtures/tensor_export.npy"

    result = build_historical_dataset_readiness(build_input(payload))

    assert any(gap.gap_category.value == "READINESS_ML_READY_TENSOR_EXPORT_NOT_ALLOWED" for gap in result.readiness_gap_report.gaps)


def test_build_historical_dataset_readiness_rejects_unsafe_marker():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))
    payload["audit_records"][0]["operator_context"] = "BUY NOW"

    result = build_historical_dataset_readiness(build_input(payload))

    assert any(gap.gap_category.value == "READINESS_BUY_SELL_WORDING_DETECTED" for gap in result.readiness_gap_report.gaps)


def test_build_historical_dataset_readiness_rejects_parquet():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))
    payload["validation_report"]["source_manifest_ids"] = ["PARQUET"]

    with pytest.raises(ValueError, match="parquet"):
        build_historical_dataset_readiness(build_input(payload))
