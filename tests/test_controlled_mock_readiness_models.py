import json

import pytest

from stock_risk_mcp.controlled_mock_readiness_fixture import load_controlled_mock_readiness_fixture
from stock_risk_mcp.controlled_mock_readiness_guard import validate_controlled_mock_readiness_metadata_safety
from stock_risk_mcp.controlled_mock_readiness_models import (
    ControlledMockReadinessDecision,
    ControlledMockReadinessGapCategory,
    ControlledMockReadinessInput,
)


def controlled_mock_readiness_payload(**overrides):
    payload = {
        "readiness_review_id": "controlled-mock-readiness-1",
        "paper_evaluation_ref": "paper-eval-ref-1",
        "paper_evaluation_decision": "PAPER_PASS",
        "allocation_policy_ref": "allocation-policy-ref-1",
        "allocation_policy_decision": "PAPER_CANDIDATE",
        "strategy_ensemble_ref": "ensemble-ref-1",
        "risk_control_ref": "risk-control-ref-1",
        "mock_oauth_readiness_ref": "oauth-ref-1",
        "mock_oauth_readiness_status": "MOCK_ONLY",
        "mock_market_data_readiness_ref": "market-data-ref-1",
        "mock_market_data_readiness_status": "AVAILABLE",
        "broker_adapter_boundary_ref": "broker-boundary-ref-1",
        "order_gate_boundary_ref": "order-gate-ref-1",
        "kill_switch_policy_ref": "kill-switch-ref-1",
        "user_opt_in_policy_ref": "opt-in-ref-1",
        "audit_policy_ref": "audit-ref-1",
        "rollback_policy_ref": "rollback-ref-1",
        "point_in_time_evidence_present": True,
        "walk_forward_evidence_present": True,
        "costs_present": True,
        "cnn_feature_gap_noted": False,
        "drawdown_limit_passed": True,
        "exposure_limit_passed": True,
        "turnover_limit_passed": True,
        "live_prod_path_attempt": False,
        "real_broker_dependency": False,
        "real_account_dependency": False,
        "real_order_dependency": False,
        "websocket_dependency": False,
        "autonomous_execution_path": False,
        "safety_policy": {
            "policy_id": "controlled-mock-safety-policy-1",
            "explicit_user_opt_in_required": True,
            "maximum_simulated_exposure": 1.0,
            "maximum_mock_exposure": 0.3,
            "maximum_inverse_hedge_exposure": 0.2,
            "daily_loss_limit": 0.05,
            "maximum_drawdown_limit": 0.15,
            "order_count_limit": 5,
            "cool_down_policy_present": True,
            "kill_switch_policy_present": True,
            "fail_closed_policy_present": True,
            "audit_requirement_present": True,
            "rollback_requirement_present": True,
        },
        "audit_records": [
            {
                "audit_record_id": "controlled-mock-readiness-audit-1",
                "created_at": "2026-06-24T17:00:00+09:00",
                "source_path": "fixtures/mock/controlled_mock_readiness_fixture.json",
                "operator_context": "offline controlled mock readiness review",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_default_controlled_mock_readiness_layer_is_local_offline_report_only():
    loaded = ControlledMockReadinessInput.model_validate(controlled_mock_readiness_payload())
    assert loaded.report_only is True
    assert loaded.offline_only is True
    assert loaded.no_mock_order_execution is True


def test_guard_rejects_secret_token_account_markers():
    with pytest.raises(ValueError):
        validate_controlled_mock_readiness_metadata_safety({"authorization": "Bearer abc"}, context="controlled mock")


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "controlled_mock_readiness_fixture.json"
    fixture_path.write_text(json.dumps(controlled_mock_readiness_payload()), encoding="utf-8")
    loaded = load_controlled_mock_readiness_fixture(fixture_path)
    assert isinstance(loaded, ControlledMockReadinessInput)
    assert loaded.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_controlled_mock_readiness_fixture("https://example.com/mock.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_controlled_mock_readiness_fixture(tmp_path / "mock.parquet")


def test_decision_enum_surface():
    assert ControlledMockReadinessDecision.MOCK_REVIEW_READY.value == "MOCK_REVIEW_READY"
    assert ControlledMockReadinessDecision.MOCK_DRY_RUN_READY.value == "MOCK_DRY_RUN_READY"


def test_gap_category_surface():
    categories = {item.value for item in ControlledMockReadinessGapCategory}
    assert "MISSING_KILL_SWITCH" in categories
    assert "CNN_FEATURE_GAP_NOTED" in categories
