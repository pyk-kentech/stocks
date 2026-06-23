from stock_risk_mcp.point_in_time_universe_engine import build_point_in_time_universe_gate
from stock_risk_mcp.point_in_time_universe_models import PointInTimeUniverseDecision, PointInTimeUniverseInput
from tests.test_point_in_time_universe_models import point_in_time_universe_payload


def _evaluate(**overrides):
    payload = point_in_time_universe_payload()
    payload.update(overrides)
    return build_point_in_time_universe_gate(PointInTimeUniverseInput.model_validate(payload))


def test_current_survivors_only_dataset_is_blocked_from_training_grade_use():
    result = _evaluate(universe_source="CURRENT_SURVIVORS_ONLY")
    assert result.dataset_promotion_readiness_report.decision in {
        PointInTimeUniverseDecision.BLOCKED,
        PointInTimeUniverseDecision.RESEARCH_ONLY,
    }


def test_point_in_time_universe_dataset_can_become_training_ready():
    result = _evaluate()
    assert result.dataset_promotion_readiness_report.decision == PointInTimeUniverseDecision.TRAINING_READY


def test_missing_available_at_causes_gap():
    result = _evaluate(
        available_at_coverage_complete=False,
        universe_snapshots=[
            {
                **point_in_time_universe_payload()["universe_snapshots"][0],
                "available_at": "2026-06-20T08:00:00+09:00",
            }
        ],
    )
    assert result.dataset_promotion_readiness_report.decision == PointInTimeUniverseDecision.GAP


def test_missing_delisting_coverage_causes_gap():
    result = _evaluate(
        security_lifecycle_records=[
            record
            for record in point_in_time_universe_payload()["security_lifecycle_records"]
            if record["status"] != "DELISTED"
        ]
    )
    assert result.dataset_promotion_readiness_report.decision == PointInTimeUniverseDecision.GAP


def test_missing_rename_or_corporate_action_coverage_causes_gap():
    result = _evaluate(
        corporate_action_coverage_complete=False,
        security_lifecycle_records=[
            record
            for record in point_in_time_universe_payload()["security_lifecycle_records"]
            if record["status"] != "RENAMED"
        ],
    )
    assert result.dataset_promotion_readiness_report.decision == PointInTimeUniverseDecision.GAP


def test_future_index_membership_leakage_is_blocked():
    result = _evaluate(future_index_membership_leakage_detected=True)
    assert result.dataset_promotion_readiness_report.decision == PointInTimeUniverseDecision.BLOCKED


def test_future_delisting_knowledge_leakage_is_blocked():
    result = _evaluate(future_delisting_knowledge_leakage_detected=True)
    assert result.dataset_promotion_readiness_report.decision == PointInTimeUniverseDecision.BLOCKED


def test_mixed_or_unknown_universe_source_becomes_gap_or_research_only():
    result = _evaluate(universe_source="MIXED_OR_UNKNOWN")
    assert result.dataset_promotion_readiness_report.decision in {
        PointInTimeUniverseDecision.GAP,
        PointInTimeUniverseDecision.RESEARCH_ONLY,
    }
