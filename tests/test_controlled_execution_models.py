import json

from stock_risk_mcp.controlled_execution_fixture import load_controlled_execution_fixture
from stock_risk_mcp.controlled_execution_models import ControlledExecutionPipelineInput


def controlled_execution_payload(**overrides):
    payload = {
        "pipeline_id": "controlled-execution-test",
        "dataset_id": "paper-evaluation-test",
        "mode": "MOCK_EXECUTION_ONLY",
        "provider": "LOCAL_MOCK",
        "opt_in": {
            "allow_mock_execution": True,
            "allow_dry_run": True,
            "acknowledge_readonly_only": True,
            "acknowledge_no_account_mutation": True,
            "acknowledge_manual_approval_required": True,
            "acknowledge_user_initiated": True,
        },
        "requested_by": "LOCAL_OPERATOR",
        "requested_at": "2026-06-26T16:45:00+09:00",
        "instrument_id": "005930",
        "provider_symbol": "005930.KS",
        "market": "KRX",
        "side": "BUY",
        "reference_price": 82450.0,
        "quantity_proposal": 1.0,
        "notional_proposal": 82450.0,
        "risk_budget_ref": "RISK-BUDGET-REF-1",
        "feature_store_manifest": {"dataset_id": "PAPER-EVALUATION-TEST", "ready": True},
        "leakage_report": {"readiness_status": "TRAINING_DATASET_MANIFEST_READY"},
        "paper_evaluation_report": {
            "readiness_status": "PLAN_READY",
            "signal_used_labels": False,
            "metrics_available": True,
        },
        "macro_regime_report": {"snapshot_ready": True, "stale": False},
        "domestic_snapshot_report": {"snapshot_ready": True, "liquidity_safe": True, "stale": False},
        "position_sizing_report": {"decision": "SIZE_READY", "risk_budget_ref": "RISK-BUDGET-REF-1", "unbounded_size": False},
        "event_risk_report": {"decision": "ALLOW", "stale": False},
        "breadth_routing_report": {"decision": "BROAD_MARKET_OK"},
        "controlled_mock_rehearsal_report": {"decision": "MOCK_EXECUTION_REVIEW_READY"},
        "account_read_report": {"read_only": True, "account_ref_redacted": True, "stale": False},
        "reconciliation_report": {
            "readiness_status": "RECONCILIATION_REPORT_READY",
            "instrument_mapping_unambiguous": True,
            "cash_position_mismatch_classified": True,
        },
        "adapter_evidence": {
            "mock_ready": True,
            "dry_run_ready": True,
            "kiwoom_exact_schema": True,
            "kiwoom_allowlisted": True,
            "ls_exact_schema": False,
            "ls_allowlisted": False,
        },
        "manual_approval_fixture": {
            "approval_ref": "fake-approval-controlled-execution-test",
            "order_draft_hash": "DRAFT-CONTROLLED-EXECUTION-TEST-005930-BUY",
            "already_used": False,
            "expiry_at": "2026-06-26T17:15:00+09:00",
        },
        "live_boundary_evidence_ref": "fixtures/controlled_execution/live_boundary_evidence.json",
        "global_kill_switch_active": False,
        "market_kill_switch_active": False,
        "instrument_kill_switch_active": False,
        "daily_loss_breached": False,
        "max_order_count_breached": False,
        "max_exposure_breached": False,
        "stale_data_blocked": False,
        "cooldown_active": False,
        "prior_open_intent_exists": False,
        "prior_pending_draft_exists": False,
        "same_instrument_side_collision": False,
        "prior_pending_audit_unresolved": False,
        "approval_reuse_detected": False,
        "idempotency_key": "IDEMPOTENCY-KEY-1",
        "prior_audit_records": [],
        "audit_records": [
            {
                "audit_record_id": "controlled-execution-audit-test",
                "created_at": "2026-06-26T16:44:00+09:00",
                "source_path": "fixtures/controlled_execution/controlled_execution_fixture.json",
                "operator_context": "offline controlled execution unit test",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_controlled_execution_pipeline_input_is_safe():
    loaded = ControlledExecutionPipelineInput.model_validate(controlled_execution_payload())
    assert loaded.no_network is True
    assert loaded.no_env_read is True
    assert loaded.no_account_mutation is True


def test_controlled_execution_fixture_loader_reads_local_json(tmp_path):
    fixture_file = tmp_path / "controlled_execution_fixture.json"
    fixture_file.write_text(json.dumps(controlled_execution_payload()), encoding="utf-8")
    loaded = load_controlled_execution_fixture(fixture_file)
    assert loaded.pipeline_id == "CONTROLLED-EXECUTION-TEST"
