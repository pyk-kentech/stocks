import json

import pytest

from stock_risk_mcp.controlled_mock_dry_run_fixture import load_controlled_mock_dry_run_fixture
from stock_risk_mcp.controlled_mock_dry_run_guard import validate_controlled_mock_dry_run_metadata_safety
from stock_risk_mcp.controlled_mock_dry_run_models import (
    ControlledMockDryRunDecision,
    ControlledMockDryRunInput,
    MockIntentRouteType,
)


def controlled_mock_dry_run_payload(**overrides):
    payload = {
        "dry_run_id": "controlled-mock-dry-run-1",
        "candidate_symbol": "NVDA",
        "candidate_market": "NASDAQ",
        "candidate_side": "BUY",
        "candidate_action_type": "NEW_ENTRY",
        "candidate_is_leadership": True,
        "candidate_is_outlier": False,
        "candidate_is_exposure_reducing": False,
        "candidate_is_inverse_or_hedge": False,
        "route_hint": "CORE_STRATEGY",
        "paper_evaluation_ref": "fixtures/paper/paper_eval_report.json",
        "paper_evaluation_decision": "PAPER_PASS",
        "mock_readiness_ref": "fixtures/mock/mock_readiness_report.json",
        "mock_readiness_decision": "MOCK_DRY_RUN_READY",
        "market_regime_ref": "fixtures/regime/market_regime_report.json",
        "market_regime_decision": "TRAINING_FEATURE_READY",
        "market_regime_label": "RISK_ON",
        "provider_registry_ref": "fixtures/provider/provider_registry_report.json",
        "provider_registry_decision": "PAPER_READY",
        "position_sizing_ref": "fixtures/position_sizing/position_sizing_review.json",
        "position_sizing_decision": "SIZE_READY",
        "quantity_preview": 50,
        "notional_preview": 25000.0,
        "event_risk_ref": "fixtures/event_risk/event_risk_review.json",
        "event_risk_decision": "ALLOW",
        "breadth_routing_ref": "fixtures/breadth/breadth_routing_review.json",
        "breadth_routing_decision": "BROAD_MARKET_OK",
        "breadth_constraints": [],
        "strategy_ensemble_ref": "fixtures/ensemble/strategy_ensemble_report.json",
        "risk_policy_ref": "fixtures/risk/risk_policy_report.json",
        "mock_market_data_readiness_ref": "fixtures/mock/mock_market_data_readiness.json",
        "mock_market_data_readiness_status": "AVAILABLE",
        "mock_oauth_readiness_ref": "fixtures/mock/mock_oauth_readiness.json",
        "mock_oauth_readiness_status": "AVAILABLE",
        "order_gate_boundary_ref": "fixtures/mock/order_gate_boundary.json",
        "kill_switch_policy_ref": "fixtures/mock/kill_switch_policy.json",
        "opt_in_policy_ref": "fixtures/mock/opt_in_policy.json",
        "audit_policy_ref": "fixtures/mock/audit_policy.json",
        "rollback_policy_ref": "fixtures/mock/rollback_policy.json",
        "stop_discipline_ref": "fixtures/risk/stop_discipline.json",
        "liquidity_evidence_ref": "fixtures/liquidity/liquidity_evidence.json",
        "slippage_risk_note": "MANAGEABLE",
        "outlier_max_sleeve_allocation": 0.10,
        "outlier_max_per_name_risk": 0.0075,
        "candidate_requested_sleeve_allocation": 0.03,
        "candidate_requested_per_name_risk": 0.004,
        "current_order_count": 1,
        "max_order_count_limit": 5,
        "projected_total_exposure": 0.25,
        "max_total_exposure": 0.50,
        "projected_inverse_hedge_exposure": 0.05,
        "max_inverse_hedge_exposure": 0.20,
        "available_at": "2026-06-25T09:35:00+09:00",
        "source_refs": [
            "fixtures/paper/paper_eval_report.json",
            "fixtures/mock/mock_readiness_report.json",
            "fixtures/regime/market_regime_report.json",
            "fixtures/provider/provider_registry_report.json",
            "fixtures/position_sizing/position_sizing_review.json",
            "fixtures/event_risk/event_risk_review.json",
            "fixtures/breadth/breadth_routing_review.json",
        ],
        "live_prod_path_attempt": False,
        "real_broker_dependency": False,
        "kiwoom_dependency": False,
        "kiwoom_mock_order_execution_dependency": False,
        "provider_network_dependency": False,
        "websocket_dependency": False,
        "autonomous_execution_path": False,
        "executable_order_object_present": False,
        "real_order_id_present": False,
        "raw_account_output_present": False,
        "credential_token_output_present": False,
        "missing_fail_closed_behavior": False,
        "safety_report": {
            "safety_report_id": "controlled-mock-dry-run-safety-1",
            "blocked_capabilities": [
                "LIVE_TRADING_BLOCKED",
                "REAL_ORDER_BLOCKED",
                "ACCOUNT_MUTATION_BLOCKED",
                "BROKER_API_BLOCKED",
                "KIWOOM_API_BLOCKED",
                "WEBSOCKET_BLOCKED",
                "NETWORK_BLOCKED",
                "AUTONOMOUS_TRADING_BLOCKED",
                "MOCK_ORDER_EXECUTION_BLOCKED",
            ],
            "findings": [],
        },
        "audit_records": [
            {
                "audit_record_id": "controlled-mock-dry-run-audit-1",
                "created_at": "2026-06-25T09:36:00+09:00",
                "source_path": "fixtures/mock/controlled_mock_dry_run_fixture.json",
                "operator_context": "offline controlled mock dry-run review",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_default_controlled_mock_dry_run_layer_is_local_offline_report_only():
    loaded = ControlledMockDryRunInput.model_validate(controlled_mock_dry_run_payload())
    assert loaded.report_only is True
    assert loaded.offline_only is True
    assert loaded.no_mock_order_execution is True


def test_guard_rejects_secret_token_account_markers():
    with pytest.raises(ValueError):
        validate_controlled_mock_dry_run_metadata_safety({"authorization": "Bearer abc"}, context="controlled mock dry run")


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "controlled_mock_dry_run_fixture.json"
    fixture_path.write_text(json.dumps(controlled_mock_dry_run_payload()), encoding="utf-8")
    loaded = load_controlled_mock_dry_run_fixture(fixture_path)
    assert isinstance(loaded, ControlledMockDryRunInput)
    assert loaded.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_controlled_mock_dry_run_fixture("https://example.com/mock_dry_run.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_controlled_mock_dry_run_fixture(tmp_path / "mock_dry_run.parquet")


def test_decision_and_route_surface():
    assert ControlledMockDryRunDecision.MOCK_EXECUTION_REVIEW_READY.value == "MOCK_EXECUTION_REVIEW_READY"
    assert ControlledMockDryRunDecision.DRY_RUN_REHEARSED.value == "DRY_RUN_REHEARSED"
    assert MockIntentRouteType.OUTLIER_MOMENTUM_SLEEVE.value == "OUTLIER_MOMENTUM_SLEEVE"
