import json

import pytest

from stock_risk_mcp.strategy_ensemble_alpha_fixture import load_strategy_ensemble_alpha_fixture
from stock_risk_mcp.strategy_ensemble_alpha_guard import (
    validate_strategy_ensemble_alpha_metadata_safety,
)
from stock_risk_mcp.strategy_ensemble_alpha_models import (
    EnsemblePromotionDecision,
    StrategyEnsembleAlphaInput,
)


def strategy_ensemble_alpha_payload(**overrides):
    payload = {
        "input_id": "strategy-ensemble-input-1",
        "portfolio": {
            "portfolio_id": "alpha-portfolio-1",
            "rebalance_policy": "WEEKLY",
            "risk_budget_policy": "BALANCED",
            "min_alpha_count": 3,
            "min_strategy_family_count": 3,
            "max_family_concentration": 0.45,
            "max_single_alpha_concentration": 0.40,
            "allocations": [
                {"alpha_id": "alpha-1", "proposed_weight": 0.34},
                {"alpha_id": "alpha-2", "proposed_weight": 0.33},
                {"alpha_id": "alpha-3", "proposed_weight": 0.33},
            ],
        },
        "alpha_candidates": [
            {
                "alpha_id": "alpha-1",
                "strategy_family": "MOMENTUM",
                "feature_set_id": "feature-set-1",
                "signal_source": "SIGNAL-CANDIDATE",
                "horizon": "5D",
                "market": "KRX",
                "expected_holding_period": "3D",
                "training_promotion_ref": "promotion-ref-1",
                "training_promotion_decision": "PAPER_CANDIDATE",
                "robustness_ref": "robustness-ref-1",
                "robustness_decision": "TRAINING_READY",
                "paper_candidate_eligibility_ref": "paper-ref-1",
            },
            {
                "alpha_id": "alpha-2",
                "strategy_family": "MEAN_REVERSION",
                "feature_set_id": "feature-set-2",
                "signal_source": "SIGNAL-CANDIDATE",
                "horizon": "10D",
                "market": "KRX",
                "expected_holding_period": "5D",
                "training_promotion_ref": "promotion-ref-2",
                "training_promotion_decision": "TRAINING_READY",
                "robustness_ref": "robustness-ref-2",
                "robustness_decision": "TRAINING_READY",
                "paper_candidate_eligibility_ref": "paper-ref-2",
            },
            {
                "alpha_id": "alpha-3",
                "strategy_family": "SECTOR_ROTATION",
                "feature_set_id": "feature-set-3",
                "signal_source": "SIGNAL-CANDIDATE",
                "horizon": "15D",
                "market": "KRX",
                "expected_holding_period": "7D",
                "training_promotion_ref": "promotion-ref-3",
                "training_promotion_decision": "TRAINING_READY",
                "robustness_ref": "robustness-ref-3",
                "robustness_decision": "TRAINING_READY",
                "paper_candidate_eligibility_ref": "paper-ref-3",
            },
        ],
        "correlation_matrix_summary": {
            "max_pair_correlation": 0.35,
            "high_correlation_pairs": [],
        },
        "drawdown_summary": {
            "max_drawdown_co_movement": 0.30,
            "high_drawdown_pairs": [],
        },
        "regime_overlap_summary": {
            "regime_coverage_complete": True,
            "overlap_ratio": 0.35,
            "covered_regimes": ["RISK_ON", "RISK_OFF", "DEFENSIVE"],
        },
        "duplicate_signal_detected": False,
        "source_manifest_ids": ["MANIFEST-1"],
        "audit_records": [
            {
                "audit_record_id": "strategy-ensemble-audit-1",
                "created_at": "2026-06-24T00:00:00+09:00",
                "source_path": "fixtures/quant/strategy_ensemble_alpha_fixture.json",
                "operator_context": "offline strategy ensemble alpha gate",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
        "safety_report": {
            "safety_report_id": "strategy-ensemble-safety-1",
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


def test_default_ensemble_gate_is_local_offline_report_only():
    loaded = StrategyEnsembleAlphaInput.model_validate(strategy_ensemble_alpha_payload())
    assert loaded.audit_records[0].redaction_applied is True
    assert loaded.safety_report.report_only is True
    assert loaded.safety_report.local_file_only is True
    assert loaded.safety_report.offline_only is True


def test_audit_report_is_redacted():
    loaded = StrategyEnsembleAlphaInput.model_validate(strategy_ensemble_alpha_payload())
    audit = loaded.audit_records[0]
    assert audit.redaction_applied is True
    assert audit.contains_secret_material is False
    assert audit.contains_token_material is False
    assert audit.contains_account_material is False


def test_guard_rejects_raw_secret_token_account_markers():
    with pytest.raises(ValueError):
        validate_strategy_ensemble_alpha_metadata_safety(
            {"authorization": "Bearer abc"},
            context="strategy ensemble alpha",
        )


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "strategy_ensemble_alpha_fixture.json"
    fixture_path.write_text(json.dumps(strategy_ensemble_alpha_payload()), encoding="utf-8")
    loaded = load_strategy_ensemble_alpha_fixture(fixture_path)
    assert isinstance(loaded, StrategyEnsembleAlphaInput)
    assert loaded.safety_report.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_strategy_ensemble_alpha_fixture("https://example.com/ensemble.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_strategy_ensemble_alpha_fixture(tmp_path / "ensemble.parquet")


def test_decision_enum_supports_ensemble_and_paper_candidate():
    assert EnsemblePromotionDecision.ENSEMBLE_READY.value == "ENSEMBLE_READY"
    assert EnsemblePromotionDecision.PAPER_CANDIDATE.value == "PAPER_CANDIDATE"
