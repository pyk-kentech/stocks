import json

import pytest

from stock_risk_mcp.quant_strategy_robustness_fixture import load_quant_strategy_robustness_fixture
from stock_risk_mcp.quant_strategy_robustness_guard import (
    validate_quant_strategy_robustness_metadata_safety,
)
from stock_risk_mcp.quant_strategy_robustness_models import (
    QuantStrategyRobustnessConfig,
    QuantStrategyRobustnessDecision,
    QuantStrategyRobustnessInput,
)


def quant_strategy_robustness_payload(**overrides):
    payload = {
        "input_id": "quant-robustness-input-1",
        "config": {
            "config_id": "quant-robustness-config-1",
            "fixture_format": "json",
        },
        "universe_policy": {
            "universe_mode": "POINT_IN_TIME_HISTORICAL",
            "historical_universe_snapshots_required": True,
            "historical_universe_snapshots_available": True,
            "delisted_handled": True,
            "suspended_handled": True,
            "merged_handled": True,
            "renamed_handled": True,
            "index_removed_handled": True,
        },
        "point_in_time_policy": {
            "available_at_required": True,
            "price_features_have_available_at": True,
            "fundamental_features_have_available_at": True,
            "index_features_have_available_at": True,
            "macro_features_have_available_at": True,
            "event_features_have_available_at": True,
            "future_data_leakage_blocked": True,
            "corporate_action_policy_present": True,
            "split_policy_present": True,
            "dividend_policy_present": True,
            "symbol_change_policy_present": True,
            "delisting_policy_present": True,
        },
        "walk_forward_policy": {
            "walk_forward_mode": "ROLLING",
            "train_window_count": 4,
            "validation_window_count": 2,
            "test_window_count": 1,
            "forward_paper_window_count": 1,
            "repeated_final_test_tuning_count": 0,
            "parameter_search_count": 4,
            "max_parameter_search_count": 20,
            "final_test_period_reused_for_tuning": False,
            "period_stability_metrics_present": True,
        },
        "diversification_policy": {
            "alpha_candidate_families": [
                "MOMENTUM",
                "MEAN_REVERSION",
                "BREAKOUT",
                "VOLUME_SHOCK",
            ],
            "max_pairwise_strategy_correlation": 0.45,
            "max_drawdown_comovement": 0.35,
        },
        "regime_policy": {
            "regime_buckets": [
                "INDEX_TREND",
                "VOLATILITY",
                "FX",
                "RATE_LIQUIDITY",
                "SECTOR_BREADTH",
                "MACRO_EVENT_CALENDAR",
            ],
            "required_bucket_count": 6,
            "evaluated_bucket_count": 6,
        },
        "experiment_registry_ref": "docs/superpowers/plans/2026-06-18-quant-strategy-robustness-training-readiness-foundation.md",
        "source_manifest_ids": ["MANIFEST-1"],
        "audit_records": [
            {
                "audit_record_id": "quant-robustness-audit-1",
                "created_at": "2026-06-23T00:00:00+09:00",
                "source_path": "fixtures/quant/quant_strategy_robustness_fixture.json",
                "operator_context": "offline robustness smoke",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
                "experiment_registry_ref": "docs/superpowers/plans/2026-06-18-quant-strategy-robustness-training-readiness-foundation.md",
            }
        ],
        "robustness_safety_report": {
            "safety_report_id": "quant-robustness-safety-report-1",
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


def test_default_robustness_config_is_local_offline_report_only():
    config = QuantStrategyRobustnessConfig.model_validate(
        quant_strategy_robustness_payload()["config"]
    )
    assert config.read_only is True
    assert config.report_only is True
    assert config.non_executable is True
    assert config.local_file_only is True
    assert config.offline_only is True


def test_raw_secret_token_account_markers_are_rejected():
    with pytest.raises(ValueError):
        validate_quant_strategy_robustness_metadata_safety(
            {"authorization": "Bearer abc"},
            context="quant robustness",
        )


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "quant_strategy_robustness_fixture.json"
    fixture_path.write_text(json.dumps(quant_strategy_robustness_payload()), encoding="utf-8")
    loaded = load_quant_strategy_robustness_fixture(fixture_path)
    assert isinstance(loaded, QuantStrategyRobustnessInput)
    assert loaded.config.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_quant_strategy_robustness_fixture("https://example.com/robustness.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_quant_strategy_robustness_fixture(tmp_path / "robustness.parquet")


def test_audit_record_is_redacted_and_non_secret_bearing():
    loaded = QuantStrategyRobustnessInput.model_validate(quant_strategy_robustness_payload())
    audit = loaded.audit_records[0]
    assert audit.redaction_applied is True
    assert audit.contains_secret_material is False
    assert audit.contains_token_material is False
    assert audit.contains_account_material is False


def test_decision_enum_supports_gap_and_training_ready():
    assert QuantStrategyRobustnessDecision.GAP.value == "GAP"
    assert QuantStrategyRobustnessDecision.TRAINING_READY.value == "TRAINING_READY"
