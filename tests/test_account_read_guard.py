from pathlib import Path

import pytest

from stock_risk_mcp.account_read_guard import (
    validate_account_read_input_gate,
    validate_account_read_metadata_safety,
    validate_account_read_root,
)
from stock_risk_mcp.account_read_models import AccountReadPipelineInput, AccountReadReadinessStatus
from tests.test_account_read_models import account_read_payload


def test_account_read_guard_blocks_forbidden_markers():
    with pytest.raises(ValueError):
        validate_account_read_metadata_safety({"authorization": "Bearer secret"}, context="account read")


def test_account_read_root_rejects_unsafe_path():
    safe, policy = validate_account_read_root("/etc", repo_root=Path(__file__).resolve().parents[1])
    assert safe is False
    assert policy == "REJECTED_PATH"


def test_account_read_input_gate_blocks_real_boundary_in_pytest():
    payload = account_read_payload()
    payload["provider"] = "KIWOOM"
    payload["mode"] = "OPT_IN_REAL_READONLY_BOUNDARY"
    payload["snapshot_fixture"] = None
    payload["opt_in"] = {
        "allow_real_account_read": True,
        "acknowledge_readonly_only": True,
        "acknowledge_no_orders": True,
        "acknowledge_no_account_mutation": True,
        "acknowledge_user_initiated": True,
    }
    readiness, findings, gaps = validate_account_read_input_gate(
        AccountReadPipelineInput.model_validate(payload),
        in_pytest=True,
    )
    assert readiness == AccountReadReadinessStatus.BLOCKED_NETWORK_IN_TEST
    assert "OPT_IN_BOUNDARY_ONLY" in findings
    assert gaps
