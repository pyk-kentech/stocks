from pathlib import Path

import pytest

from stock_risk_mcp.controlled_execution_guard import (
    validate_controlled_execution_input_gate,
    validate_controlled_execution_metadata_safety,
    validate_controlled_execution_root,
)
from stock_risk_mcp.controlled_execution_models import ControlledExecutionPipelineInput, ControlledExecutionReadinessStatus
from tests.test_controlled_execution_models import controlled_execution_payload


def test_controlled_execution_guard_blocks_forbidden_markers():
    with pytest.raises(ValueError):
        validate_controlled_execution_metadata_safety({"authorization": "Bearer secret"}, context="controlled execution")


def test_controlled_execution_root_rejects_unsafe_path():
    safe, policy = validate_controlled_execution_root("/etc", repo_root=Path(__file__).resolve().parents[1])
    assert safe is False
    assert policy == "REJECTED_PATH"


def test_controlled_execution_input_gate_blocks_live_boundary_in_pytest():
    payload = controlled_execution_payload(mode="LIVE_EXECUTION_OPT_IN_BOUNDARY", provider="KIWOOM")
    readiness, findings, gaps = validate_controlled_execution_input_gate(
        ControlledExecutionPipelineInput.model_validate(payload),
        in_pytest=True,
    )
    assert readiness == ControlledExecutionReadinessStatus.BLOCKED
    assert "LIVE_BOUNDARY_BLOCKED" in findings
    assert gaps
