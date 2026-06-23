import json

import pytest

from stock_risk_mcp.regime_allocation_learning_fixture import load_regime_allocation_learning_fixture
from stock_risk_mcp.regime_allocation_learning_guard import (
    validate_regime_allocation_learning_metadata_safety,
)
from stock_risk_mcp.regime_allocation_learning_models import (
    AllocationActionType,
    LearningDatasetReadinessDecision,
    RegimeAllocationLearningInput,
)


def regime_allocation_learning_payload(**overrides):
    payload = {
        "input_id": "regime-allocation-learning-input-1",
        "dependency_status": {
            "point_in_time_dataset_decision": "TRAINING_READY",
            "walk_forward_validation_decision": "PAPER_READY",
            "ensemble_promotion_refs_present": True,
            "current_survivors_only_dependency": False,
        },
        "regime_feature_snapshot": {
            "snapshot_id": "regime-snapshot-1",
            "market": "KRX",
            "trading_timestamp": "2026-06-24T09:00:00+09:00",
            "available_at": "2026-06-24T09:00:00+09:00",
            "index_trend": "UPTREND",
            "realized_volatility_bucket": "MEDIUM",
            "drawdown_bucket": "LOW",
            "fx_regime": "STABLE",
            "rate_liquidity_regime": "NEUTRAL",
            "sector_breadth": "BROAD",
            "macro_event_pressure": "MODERATE",
            "risk_state": "RISK_OFF",
        },
        "action_candidates": [
            {
                "action_type": "KEEP_LONG",
                "target_strategy_family_or_instrument_class": "MOMENTUM",
                "max_allocation_multiplier": 1.0,
                "expected_holding_period_constraint": "5D",
                "liquidity_evidence_ref": "liquidity-ref-1",
                "eligibility_ref": "eligibility-ref-1",
                "risk_note": "report only learning action",
                "no_execution": True,
            },
            {
                "action_type": "ROTATE_DEFENSIVE",
                "target_strategy_family_or_instrument_class": "DEFENSIVE_CASH_RISK_CONTROL",
                "max_allocation_multiplier": 0.6,
                "expected_holding_period_constraint": "5D",
                "liquidity_evidence_ref": "liquidity-ref-2",
                "eligibility_ref": "eligibility-ref-2",
                "risk_note": "defensive rotation candidate",
                "no_execution": True,
            },
            {
                "action_type": "INVERSE_CANDIDATE",
                "target_strategy_family_or_instrument_class": "INDEX_INVERSE_ETF",
                "max_allocation_multiplier": 0.2,
                "expected_holding_period_constraint": "2D",
                "liquidity_evidence_ref": "liquidity-ref-3",
                "eligibility_ref": "eligibility-ref-3",
                "risk_note": "basis risk tracked",
                "no_execution": True,
                "instrument_eligibility_ref": "instrument-eligibility-ref-1",
                "leverage_flag": True,
                "daily_reset_warning": True,
                "max_allocation_cap": 0.2,
                "short_holding_period_warning": True,
                "tracking_error_basis_risk_note": "daily reset and tracking error risk",
            },
        ],
        "forward_outcome_label": {
            "label_id": "forward-outcome-label-1",
            "forward_return": 0.04,
            "forward_drawdown": 0.02,
            "volatility": 0.15,
            "turnover": 0.10,
            "slippage_estimate_ref": "slippage-ref-1",
            "risk_adjusted_score": 0.60,
            "benchmark_relative_score": 0.03,
            "action_label_horizon": "5D",
            "available_at_safe_label_boundary": True,
        },
        "reward_scoring_policy": {
            "risk_adjusted_return": 0.60,
            "max_drawdown_penalty": 0.10,
            "turnover_penalty": 0.05,
            "volatility_penalty": 0.04,
            "benchmark_relative_performance": 0.03,
            "tail_risk_penalty": 0.02,
            "action_feasibility_penalty": 0.01,
        },
        "regime_event_leakage_detected": False,
        "future_outcome_leakage_detected": False,
        "source_manifest_ids": ["MANIFEST-1"],
        "audit_records": [
            {
                "audit_record_id": "regime-allocation-audit-1",
                "created_at": "2026-06-24T00:00:00+09:00",
                "source_path": "fixtures/quant/regime_allocation_learning_fixture.json",
                "operator_context": "offline regime allocation learning dataset gate",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
        "safety_report": {
            "safety_report_id": "regime-allocation-safety-1",
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


def test_default_layer_is_local_offline_report_only():
    loaded = RegimeAllocationLearningInput.model_validate(regime_allocation_learning_payload())
    assert loaded.audit_records[0].redaction_applied is True
    assert loaded.safety_report.report_only is True
    assert loaded.safety_report.local_file_only is True
    assert loaded.safety_report.offline_only is True


def test_audit_report_is_redacted():
    loaded = RegimeAllocationLearningInput.model_validate(regime_allocation_learning_payload())
    audit = loaded.audit_records[0]
    assert audit.redaction_applied is True
    assert audit.contains_secret_material is False
    assert audit.contains_token_material is False
    assert audit.contains_account_material is False


def test_guard_rejects_raw_secret_token_account_markers():
    with pytest.raises(ValueError):
        validate_regime_allocation_learning_metadata_safety(
            {"authorization": "Bearer abc"},
            context="regime allocation learning",
        )


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "regime_allocation_learning_fixture.json"
    fixture_path.write_text(json.dumps(regime_allocation_learning_payload()), encoding="utf-8")
    loaded = load_regime_allocation_learning_fixture(fixture_path)
    assert isinstance(loaded, RegimeAllocationLearningInput)
    assert loaded.safety_report.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_regime_allocation_learning_fixture("https://example.com/regime.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_regime_allocation_learning_fixture(tmp_path / "regime.parquet")


def test_action_enum_and_decision_enum_surface():
    assert AllocationActionType.KEEP_LONG.value == "KEEP_LONG"
    assert AllocationActionType.INVERSE_CANDIDATE.value == "INVERSE_CANDIDATE"
    assert LearningDatasetReadinessDecision.TRAINING_READY.value == "TRAINING_READY"
