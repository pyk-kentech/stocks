from pathlib import Path

import pytest

from stock_risk_mcp.paper_evaluation_guard import (
    ensure_signal_does_not_use_labels,
    validate_paper_evaluation_input_gate,
    validate_paper_evaluation_metadata_safety,
    validate_paper_evaluation_root,
)
from stock_risk_mcp.paper_evaluation_models import PaperEvaluationPipelineInput, PaperEvaluationReadinessStatus
from tests.test_paper_evaluation_models import paper_evaluation_payload


def test_paper_evaluation_guard_blocks_forbidden_markers():
    with pytest.raises(ValueError):
        validate_paper_evaluation_metadata_safety({"authorization": "Bearer secret"}, context="paper evaluation")


def test_paper_evaluation_guard_blocks_label_derived_signal_fields():
    with pytest.raises(ValueError):
        ensure_signal_does_not_use_labels({"forward_return": 0.1})


def test_paper_evaluation_root_rejects_unsafe_path():
    safe, policy = validate_paper_evaluation_root("/etc", repo_root=Path(__file__).resolve().parents[1])
    assert safe is False
    assert policy == "REJECTED_PATH"


def test_paper_evaluation_input_gate_blocks_leakage():
    payload = paper_evaluation_payload()
    payload["leakage_report"]["readiness_status"] = "BLOCKED_LEAKAGE"
    readiness, findings, gaps = validate_paper_evaluation_input_gate(PaperEvaluationPipelineInput.model_validate(payload))
    assert readiness == PaperEvaluationReadinessStatus.LEAKAGE_BLOCKED
    assert "LEAKAGE_BLOCKED" in findings
    assert gaps
