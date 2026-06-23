import json

import pytest

from stock_risk_mcp.training_pipeline_promotion_fixture import load_training_pipeline_promotion_fixture
from stock_risk_mcp.training_pipeline_promotion_guard import (
    validate_training_pipeline_promotion_metadata_safety,
)
from stock_risk_mcp.training_pipeline_promotion_models import (
    TrainingPipelinePromotionDecision,
    TrainingPipelinePromotionInput,
)


def training_pipeline_promotion_payload(**overrides):
    payload = {
        "input_id": "training-promotion-input-1",
        "dataset_eligibility": {
            "dataset_id": "dataset-1",
            "point_in_time_gate_decision": "TRAINING_READY",
            "survivorship_safety_ref": "pit-report-1",
            "available_at_discipline_ref": "available-at-ref-1",
            "leakage_audit_ref": "leakage-audit-ref-1",
            "feature_set_id": "feature-set-1",
            "label_horizon": "5D",
            "target_type": "OUTCOME_LABEL",
            "train_split_ref": "TRAIN-SPLIT-1",
            "validation_split_ref": "VALIDATION-SPLIT-1",
            "test_split_ref": "TEST-SPLIT-1",
            "forward_paper_split_ref": "FORWARD-PAPER-SPLIT-1",
            "label_leakage_detected": False,
        },
        "training_run_candidate": {
            "training_run_id": "training-run-1",
            "model_family": "DUMMY_MAJORITY",
            "hyperparameter_set_id": "hyperparam-1",
            "feature_set_id": "feature-set-1",
            "dataset_id": "dataset-1",
            "experiment_id": "experiment-1",
            "random_seed_policy_present": True,
            "reproducibility_hash": "repro-hash-1",
            "training_window_refs": ["TRAIN-WINDOW-1"],
            "validation_window_refs": ["VALIDATION-WINDOW-1"],
            "test_window_refs": ["TEST-WINDOW-1"],
            "forward_paper_window_refs": ["FORWARD-PAPER-WINDOW-1"],
        },
        "v71_dataset_decision": "TRAINING_READY",
        "v72_validation_decision": "PAPER_READY",
        "v70_robustness_decision": "TRAINING_READY",
        "excessive_parameter_search_flagged": False,
        "final_test_contamination_detected": False,
        "leakage_detected": False,
        "snooping_detected": False,
        "model_artifact_metadata_reproducible": True,
        "config_read_only_flags": {"report_only": True},
        "source_manifest_ids": ["MANIFEST-1"],
        "audit_records": [
            {
                "audit_record_id": "training-promotion-audit-1",
                "created_at": "2026-06-24T00:00:00+09:00",
                "source_path": "fixtures/quant/training_pipeline_promotion_fixture.json",
                "operator_context": "offline training pipeline promotion gate",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
        "safety_report": {
            "safety_report_id": "training-promotion-safety-1",
            "blocked_capabilities": [
                "LIVE_TRADING_BLOCKED",
                "REAL_ORDER_BLOCKED",
                "ACCOUNT_MUTATION_BLOCKED",
                "BROKER_API_BLOCKED",
                "NETWORK_BLOCKED",
                "AUTONOMOUS_TRADING_BLOCKED",
            ],
            "findings": [],
        },
    }
    payload.update(overrides)
    return payload


def test_default_promotion_gate_is_local_offline_report_only():
    loaded = TrainingPipelinePromotionInput.model_validate(training_pipeline_promotion_payload())
    assert loaded.audit_records[0].redaction_applied is True
    assert loaded.safety_report.report_only is True
    assert loaded.safety_report.local_file_only is True
    assert loaded.safety_report.offline_only is True


def test_audit_report_is_redacted():
    loaded = TrainingPipelinePromotionInput.model_validate(training_pipeline_promotion_payload())
    audit = loaded.audit_records[0]
    assert audit.redaction_applied is True
    assert audit.contains_secret_material is False
    assert audit.contains_token_material is False
    assert audit.contains_account_material is False


def test_guard_rejects_raw_secret_token_account_markers():
    with pytest.raises(ValueError):
        validate_training_pipeline_promotion_metadata_safety(
            {"authorization": "Bearer abc"},
            context="training promotion",
        )


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "training_pipeline_promotion_fixture.json"
    fixture_path.write_text(json.dumps(training_pipeline_promotion_payload()), encoding="utf-8")
    loaded = load_training_pipeline_promotion_fixture(fixture_path)
    assert isinstance(loaded, TrainingPipelinePromotionInput)
    assert loaded.safety_report.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_training_pipeline_promotion_fixture("https://example.com/training.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_training_pipeline_promotion_fixture(tmp_path / "training.parquet")


def test_decision_enum_supports_training_and_paper_candidate():
    assert TrainingPipelinePromotionDecision.TRAINING_READY.value == "TRAINING_READY"
    assert TrainingPipelinePromotionDecision.PAPER_CANDIDATE.value == "PAPER_CANDIDATE"
