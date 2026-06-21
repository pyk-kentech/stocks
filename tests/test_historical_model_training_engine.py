import copy

import pytest

from stock_risk_mcp.historical_model_training_engine import (
    build_historical_model_training_plan_check,
    extract_historical_model_training_feature_rows,
    extract_historical_model_training_labels,
    prepare_historical_model_training_splits,
    run_historical_model_training_sandbox,
)
from stock_risk_mcp.historical_model_training_models import HistoricalModelTrainingInput
from tests.test_historical_model_training_models import historical_model_training_fixture_payload


def build_input(payload=None):
    return HistoricalModelTrainingInput.model_validate(payload or historical_model_training_fixture_payload())


def _engine_payload():
    payload = historical_model_training_fixture_payload()
    payload["plan_check_report"]["warning_count"] = 0
    payload["plan_check_report"]["warnings"] = []
    payload["plan_check_report"]["blocking_issue_count"] = 0
    payload["plan_check_report"]["eligible_for_sandbox_training"] = False
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
        record["feature_block"]["replay_context_id"] = f"REPLAY-CONTEXT-{index + 1}"
        record["feature_block"]["scanner_replay_input_id"] = f"SCANNER-REPLAY-INPUT-{index + 1}"
        record["outcome_block"]["block_id"] = f"OUTCOME-BLOCK-{index + 1}"
        if index in {0, 1, 2, 5}:
            record["outcome_block"]["outcome_label"] = "OUTCOME_FAVORABLE"
        elif index == 3:
            record["outcome_block"]["outcome_label"] = "OUTCOME_ADVERSE"
        else:
            record["outcome_block"]["outcome_label"] = "OUTCOME_REPORT_ONLY"
        records.append(record)
    payload["dataset_records"] = records
    return payload


def _set_split_manifest_from_records(payload):
    train = []
    validation = []
    test = []
    for index, record in enumerate(payload["dataset_records"]):
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
    payload["split_manifest"]["train_record_refs"] = train
    payload["split_manifest"]["validation_record_refs"] = validation
    payload["split_manifest"]["test_record_refs"] = test
    payload["split_manifest"]["record_refs"] = train + validation + test
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


def test_build_historical_model_training_plan_check_success_path():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))

    result = build_historical_model_training_plan_check(build_input(payload))

    assert result.plan_check_report.eligible_for_sandbox_training is True
    assert result.plan_check_report.blocking_issue_count == 0


def test_build_historical_model_training_plan_check_reports_missing_readiness_report_gap():
    training_input = build_input(_set_split_manifest_from_records(_with_records(_engine_payload(), 6)))
    training_input = training_input.model_copy(update={"readiness_report": None})

    result = build_historical_model_training_plan_check(training_input)

    assert result.plan_check_report.blocking_issue_count >= 1
    assert any(item["gap_category"] == "TRAINING_MISSING_READINESS_REPORT" for item in result.gap_report.gaps)


def test_build_historical_model_training_plan_check_reports_missing_validation_report_gap():
    training_input = build_input(_set_split_manifest_from_records(_with_records(_engine_payload(), 6)))
    training_input = training_input.model_copy(update={"validation_report": None})

    result = build_historical_model_training_plan_check(training_input)

    assert any(item["gap_category"] == "TRAINING_MISSING_VALIDATION_REPORT" for item in result.gap_report.gaps)


def test_build_historical_model_training_plan_check_reports_missing_leakage_audit_gap():
    training_input = build_input(_set_split_manifest_from_records(_with_records(_engine_payload(), 6)))
    training_input = training_input.model_copy(update={"leakage_audit_report": None})

    result = build_historical_model_training_plan_check(training_input)

    assert any(item["gap_category"] == "TRAINING_MISSING_LEAKAGE_AUDIT" for item in result.gap_report.gaps)


def test_build_historical_model_training_plan_check_reports_missing_split_manifest_gap():
    training_input = build_input(_with_records(_engine_payload(), 6))
    training_input = training_input.model_copy(update={"split_manifest": None})

    result = build_historical_model_training_plan_check(training_input)

    assert any(item["gap_category"] == "TRAINING_MISSING_SPLIT_REF" for item in result.gap_report.gaps)


def test_build_historical_model_training_plan_check_reports_readiness_not_clean_gap():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))
    payload["readiness_report"]["blocking_gate_count"] = 1

    result = build_historical_model_training_plan_check(build_input(payload))

    assert any(item["gap_category"] == "TRAINING_READINESS_NOT_CLEAN" for item in result.gap_report.gaps)


def test_build_historical_model_training_plan_check_reports_leakage_audit_not_clean_gap():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))
    payload["leakage_audit_report"]["feature_outcome_leakage_absent"] = False

    result = build_historical_model_training_plan_check(build_input(payload))

    assert any(item["gap_category"] == "TRAINING_LEAKAGE_AUDIT_NOT_CLEAN" for item in result.gap_report.gaps)


def test_build_historical_model_training_plan_check_reports_split_not_chronological_gap():
    training_input = build_input(_set_split_manifest_from_records(_with_records(_engine_payload(), 6)))
    training_input = training_input.model_copy(
        update={"split_manifest": training_input.split_manifest.model_copy(update={"chronological": False})}
    )

    result = build_historical_model_training_plan_check(training_input)

    assert any(item["gap_category"] == "TRAINING_SPLIT_NOT_CHRONOLOGICAL" for item in result.gap_report.gaps)


def test_build_historical_model_training_plan_check_rejects_random_shuffle():
    training_input = build_input(_set_split_manifest_from_records(_with_records(_engine_payload(), 6)))
    training_input = training_input.model_copy(
        update={"split_manifest": training_input.split_manifest.model_copy(update={"random_shuffle_used": True})}
    )

    result = build_historical_model_training_plan_check(training_input)

    assert any(item["gap_category"] == "TRAINING_RANDOM_SHUFFLE_DETECTED" for item in result.gap_report.gaps)


def test_build_historical_model_training_plan_check_rejects_partition_overlap():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))
    overlap = copy.deepcopy(payload["split_manifest"]["record_refs"][0])
    overlap["record_ref_id"] = "DATASET-SPLIT-RECORD-REF-X"
    overlap["split_partition"] = "TEST"
    payload["split_manifest"]["record_refs"].append(overlap)
    payload["split_manifest"]["test_record_refs"].append(overlap)
    payload["split_manifest"]["test_record_count"] = len(payload["split_manifest"]["test_record_refs"])

    result = build_historical_model_training_plan_check(build_input(payload))

    assert any(item["gap_category"] == "TRAINING_SPLIT_NOT_CHRONOLOGICAL" for item in result.gap_report.gaps)


def test_build_historical_model_training_plan_check_rejects_duplicated_record_id():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))
    duplicate_id = payload["split_manifest"]["record_refs"][0]["dataset_record_id"]
    payload["split_manifest"]["record_refs"][1]["dataset_record_id"] = duplicate_id
    payload["split_manifest"]["train_record_refs"][1]["dataset_record_id"] = duplicate_id

    result = build_historical_model_training_plan_check(build_input(payload))

    assert any(item["gap_category"] == "TRAINING_SPLIT_NOT_CHRONOLOGICAL" for item in result.gap_report.gaps)


def test_extract_historical_model_training_feature_rows_success_path():
    training_input = build_input(_set_split_manifest_from_records(_with_records(_engine_payload(), 3)))

    rows = extract_historical_model_training_feature_rows(training_input)

    assert len(rows) == 3
    assert rows[0]["record_id"] == "DATASET-RECORD-1"
    assert "outcome_label" not in {key.lower() for key in rows[0].keys()}


@pytest.mark.parametrize("field_name", ["outcome_label", "forward_return_pct", "max_favorable_excursion_pct", "actual_forward_value"])
def test_extract_historical_model_training_feature_rows_rejects_leakage_fields(field_name):
    training_input = build_input(_set_split_manifest_from_records(_with_records(_engine_payload(), 1)))
    feature_block = training_input.dataset_records[0].feature_block.model_dump(mode="json")
    feature_block[field_name] = 1 if field_name != "outcome_label" else "OUTCOME_FAVORABLE"
    training_input.dataset_records[0] = training_input.dataset_records[0].model_copy(update={"feature_block": feature_block})

    with pytest.raises(ValueError):
        extract_historical_model_training_feature_rows(training_input)


def test_extract_historical_model_training_labels_success_path_from_outcome_side():
    training_input = build_input(_set_split_manifest_from_records(_with_records(_engine_payload(), 3)))

    labels = extract_historical_model_training_labels(training_input)

    assert labels["DATASET-RECORD-1"] == "OUTCOME_FAVORABLE"
    assert labels["DATASET-RECORD-3"] == "OUTCOME_FAVORABLE"


def test_extract_historical_model_training_labels_rejects_non_outcome_side_label_schema():
    training_input = build_input(_set_split_manifest_from_records(_with_records(_engine_payload(), 3)))
    training_input = training_input.model_copy(
        update={"label_schema": training_input.label_schema.model_copy(update={"label_source": "FEATURE_BLOCK"})}
    )

    with pytest.raises(ValueError):
        extract_historical_model_training_labels(training_input)


def test_build_historical_model_training_helpers_do_not_mutate_source_dataset_records():
    training_input = build_input(_set_split_manifest_from_records(_with_records(_engine_payload(), 3)))
    before = training_input.dataset_records[0].model_dump(mode="json")

    extract_historical_model_training_feature_rows(training_input)
    extract_historical_model_training_labels(training_input)

    after = training_input.dataset_records[0].model_dump(mode="json")
    assert before == after


def test_extract_historical_model_training_feature_rows_rejects_runtime_signal_and_order_candidate():
    training_input = build_input(_set_split_manifest_from_records(_with_records(_engine_payload(), 1)))
    feature_block = training_input.dataset_records[0].feature_block.model_dump(mode="json")
    feature_block["runtime_signal"] = "GO"

    training_input.dataset_records[0] = training_input.dataset_records[0].model_copy(update={"feature_block": feature_block})
    with pytest.raises(ValueError):
        extract_historical_model_training_feature_rows(training_input)

    feature_block = dict(training_input.dataset_records[0].feature_block)
    feature_block.pop("runtime_signal", None)
    feature_block["order_candidate"] = "X"
    training_input.dataset_records[0] = training_input.dataset_records[0].model_copy(update={"feature_block": feature_block})
    with pytest.raises(ValueError):
        extract_historical_model_training_feature_rows(training_input)


def test_build_historical_model_training_plan_check_rejects_unsafe_markers():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))
    payload["audit_records"][0]["operator_context"] = "BUY NOW"

    result = build_historical_model_training_plan_check(build_input(payload))

    assert any(item["gap_category"] == "TRAINING_BUY_SELL_WORDING_DETECTED" for item in result.gap_report.gaps)


def test_build_historical_model_training_plan_check_rejects_parquet():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))
    payload["artifact_manifest"]["local_artifact_path"] = "artifacts/model.parquet"

    with pytest.raises(ValueError, match="parquet"):
        build_input(payload)


def test_prepare_historical_model_training_splits_success_path():
    training_input = build_input(_set_split_manifest_from_records(_with_records(_engine_payload(), 6)))

    splits = prepare_historical_model_training_splits(training_input)

    assert [item.record_id for item in splits["TRAIN"]] == [
        "DATASET-RECORD-1",
        "DATASET-RECORD-2",
        "DATASET-RECORD-3",
        "DATASET-RECORD-4",
    ]
    assert [item.record_id for item in splits["VALIDATION"]] == ["DATASET-RECORD-5"]
    assert [item.record_id for item in splits["TEST"]] == ["DATASET-RECORD-6"]


def test_run_historical_model_training_sandbox_dummy_majority_success_path():
    training_input = build_input(_set_split_manifest_from_records(_with_records(_engine_payload(), 6)))

    result = run_historical_model_training_sandbox(training_input)

    assert result.run_report.training_executed is True
    assert result.run_report.model_type.value == "DUMMY_MAJORITY"
    assert result.evaluation_report.report_only_prediction_count == 6
    assert result.evaluation_report.runtime_trading_signal_present is False
    assert result.evaluation_report.order_candidate_present is False
    assert result.metrics_report.train_accuracy == pytest.approx(0.75)
    assert result.metrics_report.validation_accuracy == pytest.approx(0.0)
    assert result.metrics_report.test_accuracy == pytest.approx(1.0)
    assert result.metrics_report.confusion_matrix_counts["TEST|OUTCOME_FAVORABLE|OUTCOME_FAVORABLE"] == 1
    assert result.artifact_manifest.metrics_report_id == result.metrics_report.metrics_report_id
    assert result.artifact_manifest.local_artifact_path.endswith(".json")
    assert result.gap_report.blocking_gap_count == 0


def test_run_historical_model_training_sandbox_dummy_prior_success_path():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))
    payload["run_config"]["requested_model_type"] = "DUMMY_PRIOR"
    payload["run_report"]["model_type"] = "DUMMY_PRIOR"
    payload["evaluation_report"]["model_type"] = "DUMMY_PRIOR"
    payload["metrics_report"]["model_type"] = "DUMMY_PRIOR"
    payload["artifact_manifest"]["model_type"] = "DUMMY_PRIOR"

    result = run_historical_model_training_sandbox(build_input(payload))

    assert result.run_report.training_executed is True
    assert result.run_report.model_type.value == "DUMMY_PRIOR"
    assert result.metrics_report.train_accuracy == pytest.approx(0.75)
    assert result.metrics_report.validation_accuracy == pytest.approx(0.0)
    assert result.metrics_report.test_accuracy == pytest.approx(1.0)


def test_run_historical_model_training_sandbox_uses_train_split_only_for_dummy_fit():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))
    payload["dataset_records"][0]["outcome_block"]["outcome_label"] = "OUTCOME_ADVERSE"
    payload["dataset_records"][1]["outcome_block"]["outcome_label"] = "OUTCOME_ADVERSE"
    payload["dataset_records"][2]["outcome_block"]["outcome_label"] = "OUTCOME_FAVORABLE"
    payload["dataset_records"][3]["outcome_block"]["outcome_label"] = "OUTCOME_ADVERSE"
    payload["dataset_records"][4]["outcome_block"]["outcome_label"] = "OUTCOME_FAVORABLE"
    payload["dataset_records"][5]["outcome_block"]["outcome_label"] = "OUTCOME_FAVORABLE"

    result = run_historical_model_training_sandbox(build_input(payload))

    assert result.metrics_report.train_accuracy == pytest.approx(0.75)
    assert result.metrics_report.validation_accuracy == pytest.approx(0.0)
    assert result.metrics_report.test_accuracy == pytest.approx(0.0)
    assert result.metrics_report.confusion_matrix_counts["VALIDATION|OUTCOME_FAVORABLE|OUTCOME_ADVERSE"] == 1
    assert result.metrics_report.confusion_matrix_counts["TEST|OUTCOME_FAVORABLE|OUTCOME_ADVERSE"] == 1


def test_run_historical_model_training_sandbox_reports_sklearn_unavailable(monkeypatch):
    import importlib

    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))
    payload["run_config"]["requested_model_type"] = "LOGISTIC_REGRESSION_OPTIONAL_SKLEARN"
    payload["run_report"]["model_type"] = "LOGISTIC_REGRESSION_OPTIONAL_SKLEARN"
    payload["evaluation_report"]["model_type"] = "LOGISTIC_REGRESSION_OPTIONAL_SKLEARN"
    payload["metrics_report"]["model_type"] = "LOGISTIC_REGRESSION_OPTIONAL_SKLEARN"
    payload["artifact_manifest"]["model_type"] = "LOGISTIC_REGRESSION_OPTIONAL_SKLEARN"
    original_import_module = importlib.import_module

    def fake_import_module(name, package=None):
        if name.startswith("sklearn"):
            raise ImportError("sklearn unavailable for test")
        return original_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    result = run_historical_model_training_sandbox(build_input(payload))

    assert result.run_report.training_executed is False
    assert any(item["gap_category"] == "TRAINING_SKLEARN_UNAVAILABLE" for item in result.gap_report.gaps)


def test_run_historical_model_training_sandbox_reports_overfit_and_low_support_warnings():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))
    payload["dataset_records"][3]["outcome_block"]["outcome_label"] = "OUTCOME_FAVORABLE"
    payload["dataset_records"][4]["outcome_block"]["outcome_label"] = "OUTCOME_ADVERSE"
    payload["dataset_records"][5]["outcome_block"]["outcome_label"] = "OUTCOME_ADVERSE"

    result = run_historical_model_training_sandbox(build_input(payload))

    assert "OVERFIT_WARNING" in result.metrics_report.warnings
    assert "LOW_SUPPORT_LABEL_WARNING" in result.metrics_report.warnings


def test_run_historical_model_training_sandbox_rejects_runtime_signal_and_order_candidate_markers():
    payload = _set_split_manifest_from_records(_with_records(_engine_payload(), 6))
    payload["audit_records"][0]["operator_context"] = "runtime signal"

    result = run_historical_model_training_sandbox(build_input(payload))

    assert result.run_report.training_executed is False
    assert any(
        item["gap_category"] in {"TRAINING_RUNTIME_SIGNAL_DETECTED", "TRAINING_MODEL_WEIGHT_DETECTED_UNSAFE"}
        for item in result.gap_report.gaps
    )
