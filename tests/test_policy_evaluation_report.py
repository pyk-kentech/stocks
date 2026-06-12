from stock_risk_mcp.policy_evaluation_report import policy_evaluation_report
from stock_risk_mcp.policy_evaluation_suite import evaluate_policy_suite
from tests.test_policy_evaluation_suite import _replay


def test_report_contains_pair_counts_and_deltas() -> None:
    suite = evaluate_policy_suite([(_replay("r1", "base"), _replay("r1", "candidate"))], 1, 1)
    report = policy_evaluation_report(suite)

    assert report["completed_pair_count"] == 1
    assert "incomplete_pair_count" in report
    assert "objective_delta" in report
