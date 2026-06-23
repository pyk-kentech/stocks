import json

import pytest

from stock_risk_mcp.walk_forward_validation_fixture import load_walk_forward_validation_fixture
from stock_risk_mcp.walk_forward_validation_guard import (
    validate_walk_forward_validation_metadata_safety,
)
from stock_risk_mcp.walk_forward_validation_models import (
    WalkForwardValidationConfig,
    WalkForwardValidationDecision,
    WalkForwardValidationInput,
)


def walk_forward_validation_payload(**overrides):
    payload = {
        "input_id": "wf-validation-input-1",
        "config": {
            "config_id": "wf-validation-config-1",
            "fixture_format": "json",
            "max_parameter_search_count": 20,
            "max_hidden_failed_trials": 10,
            "paper_ready_requires_forward_window": True,
        },
        "split": {
            "split_id": "wf-split-1",
            "mode": "ROLLING",
            "train_window": {
                "start_at": "2024-01-01T00:00:00+09:00",
                "end_at": "2024-06-30T00:00:00+09:00",
            },
            "validation_window": {
                "start_at": "2024-07-01T00:00:00+09:00",
                "end_at": "2024-09-30T00:00:00+09:00",
            },
            "test_window": {
                "start_at": "2024-10-01T00:00:00+09:00",
                "end_at": "2024-12-31T00:00:00+09:00",
            },
            "forward_paper_window": {
                "start_at": "2025-01-01T00:00:00+09:00",
                "end_at": "2025-03-31T00:00:00+09:00",
            },
        },
        "experiment_lineage": {
            "experiment_id": "exp-1",
            "dataset_id": "dataset-1",
            "feature_set_id": "feature-set-1",
            "strategy_id": "strategy-1",
            "parameter_set_id": "param-set-1",
            "search_run_id": "search-run-1",
            "parent_experiment_refs": ["EXP-0"],
            "final_test_access_count": 1,
            "validation_reuse_count": 1,
            "registered_parameter_mutations": ["MUT-1"],
            "unregistered_parameter_mutation_detected": False,
        },
        "stability_evidence": {
            "fold_count": 4,
            "stable_fold_count": 3,
            "drawdown_stable": True,
            "hit_rate_stable": True,
            "return_stable": True,
            "risk_adjusted_metric_stable": True,
            "single_period_only_success": False,
            "regime_bucket_reference_present": True,
        },
        "parameter_search_count": 6,
        "hidden_failed_trial_count": 2,
        "test_period_cherry_picking_detected": False,
        "regime_bucket_reference_present": True,
        "source_manifest_ids": ["MANIFEST-1"],
        "audit_records": [
            {
                "audit_record_id": "wf-audit-1",
                "created_at": "2026-06-24T00:00:00+09:00",
                "source_path": "fixtures/quant/walk_forward_validation_fixture.json",
                "operator_context": "offline walk forward validation gate",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
        "safety_report": {
            "safety_report_id": "wf-validation-safety-1",
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


def test_default_validation_gate_is_local_offline_report_only():
    config = WalkForwardValidationConfig.model_validate(walk_forward_validation_payload()["config"])
    assert config.read_only is True
    assert config.report_only is True
    assert config.non_executable is True
    assert config.local_file_only is True
    assert config.offline_only is True


def test_audit_report_is_redacted():
    loaded = WalkForwardValidationInput.model_validate(walk_forward_validation_payload())
    audit = loaded.audit_records[0]
    assert audit.redaction_applied is True
    assert audit.contains_secret_material is False
    assert audit.contains_token_material is False
    assert audit.contains_account_material is False


def test_guard_rejects_raw_secret_token_account_markers():
    with pytest.raises(ValueError):
        validate_walk_forward_validation_metadata_safety(
            {"authorization": "Bearer abc"},
            context="walk forward validation",
        )


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "walk_forward_validation_fixture.json"
    fixture_path.write_text(json.dumps(walk_forward_validation_payload()), encoding="utf-8")
    loaded = load_walk_forward_validation_fixture(fixture_path)
    assert isinstance(loaded, WalkForwardValidationInput)
    assert loaded.config.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_walk_forward_validation_fixture("https://example.com/wf.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_walk_forward_validation_fixture(tmp_path / "wf.parquet")


def test_decision_enum_supports_validation_and_paper_ready():
    assert WalkForwardValidationDecision.VALIDATION_READY.value == "VALIDATION_READY"
    assert WalkForwardValidationDecision.PAPER_READY.value == "PAPER_READY"
