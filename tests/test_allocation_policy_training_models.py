import json

import pytest

from stock_risk_mcp.allocation_policy_training_fixture import load_allocation_policy_training_fixture
from stock_risk_mcp.allocation_policy_training_guard import (
    validate_allocation_policy_training_metadata_safety,
)
from stock_risk_mcp.allocation_policy_training_models import (
    AllocationPolicyCandidateInput,
    AllocationPolicyPromotionDecision,
)


def allocation_policy_training_payload(**overrides):
    payload = {
        "input_id": "allocation-policy-training-input-1",
        "training_input": {
            "learning_dataset_readiness_ref": "dataset-readiness-ref-1",
            "learning_dataset_readiness_decision": "TRAINING_READY",
            "regime_feature_snapshot_refs": ["REGIME-SNAPSHOT-1", "REGIME-SNAPSHOT-2"],
            "action_candidate_refs": ["ACTION-REF-1", "ACTION-REF-2"],
            "forward_outcome_label_refs": ["OUTCOME-REF-1", "OUTCOME-REF-2"],
            "reward_scoring_refs": ["REWARD-REF-1"],
            "point_in_time_safety_ref": "pit-safety-ref-1",
            "leakage_guard_ref": "leakage-guard-ref-1",
            "walk_forward_split_ref": "walk-forward-split-ref-1",
        },
        "policy_candidate": {
            "policy_id": "allocation-policy-1",
            "policy_family": "RULE_BASELINE",
            "action_space": [
                "KEEP_LONG",
                "REDUCE_SIZE",
                "ROTATE_DEFENSIVE",
                "WATCH_ONLY",
            ],
            "regime_feature_set_id": "regime-feature-set-1",
            "training_dataset_ref": "training-dataset-ref-1",
            "walk_forward_validation_ref": "walk-forward-validation-ref-1",
            "strategy_ensemble_ref": "strategy-ensemble-ref-1",
            "reward_scoring_ref": "reward-scoring-ref-1",
            "random_seed_policy_present": True,
            "reproducibility_hash": "repro-hash-1",
            "artifact_metadata": {
                "artifact_id": "artifact-1",
                "local_only": True,
                "offline_only": True,
                "non_production": True,
            },
        },
        "training_evaluation_input": {
            "policy_scores_by_action": {
                "KEEP_LONG": 0.63,
                "REDUCE_SIZE": 0.55,
                "ROTATE_DEFENSIVE": 0.71,
                "WATCH_ONLY": 0.42,
            },
            "selected_action_distribution_by_regime": {
                "RISK_ON": {"KEEP_LONG": 0.7, "ROTATE_DEFENSIVE": 0.3},
                "RISK_OFF": {"ROTATE_DEFENSIVE": 0.6, "REDUCE_SIZE": 0.4},
            },
            "train_score": 0.66,
            "validation_score": 0.64,
            "test_score": 0.62,
            "forward_paper_score": 0.61,
            "risk_adjusted_score": 0.58,
            "turnover_score": 0.12,
            "slippage_score": 0.03,
            "max_drawdown_score": 0.08,
            "stable_fold_count": 3,
            "fold_count": 4,
        },
        "dependency_status": {
            "walk_forward_validation_decision": "PAPER_READY",
            "training_promotion_dependency_decision": "PAPER_CANDIDATE",
            "ensemble_dependency_decision": "PAPER_CANDIDATE",
            "point_in_time_evidence_present": True,
            "available_at_evidence_present": True,
            "leakage_evidence_present": True,
        },
        "future_outcome_leakage_detected": False,
        "source_manifest_ids": ["MANIFEST-1"],
        "audit_records": [
            {
                "audit_record_id": "allocation-policy-training-audit-1",
                "created_at": "2026-06-24T00:00:00+09:00",
                "source_path": "fixtures/quant/allocation_policy_training_fixture.json",
                "operator_context": "offline allocation policy training sandbox",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
        "safety_report": {
            "safety_report_id": "allocation-policy-training-safety-1",
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


def test_default_training_layer_is_local_offline_report_only():
    loaded = AllocationPolicyCandidateInput.model_validate(allocation_policy_training_payload())
    assert loaded.audit_records[0].redaction_applied is True
    assert loaded.safety_report.report_only is True
    assert loaded.safety_report.local_file_only is True
    assert loaded.safety_report.offline_only is True


def test_audit_report_is_redacted():
    loaded = AllocationPolicyCandidateInput.model_validate(allocation_policy_training_payload())
    audit = loaded.audit_records[0]
    assert audit.redaction_applied is True
    assert audit.contains_secret_material is False
    assert audit.contains_token_material is False
    assert audit.contains_account_material is False


def test_guard_rejects_raw_secret_token_account_markers():
    with pytest.raises(ValueError):
        validate_allocation_policy_training_metadata_safety(
            {"authorization": "Bearer abc"},
            context="allocation policy training",
        )


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "allocation_policy_training_fixture.json"
    fixture_path.write_text(json.dumps(allocation_policy_training_payload()), encoding="utf-8")
    loaded = load_allocation_policy_training_fixture(fixture_path)
    assert isinstance(loaded, AllocationPolicyCandidateInput)
    assert loaded.safety_report.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_allocation_policy_training_fixture("https://example.com/policy.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_allocation_policy_training_fixture(tmp_path / "policy.parquet")


def test_decision_enum_surface():
    assert AllocationPolicyPromotionDecision.TRAINED_OFFLINE.value == "TRAINED_OFFLINE"
    assert AllocationPolicyPromotionDecision.PAPER_CANDIDATE.value == "PAPER_CANDIDATE"
