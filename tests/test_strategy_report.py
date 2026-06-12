from __future__ import annotations

from stock_risk_mcp.strategy_report import build_strategy_report


def test_strategy_report_explains_common_outcome_limitations() -> None:
    report = build_strategy_report([], [])

    assert report["evaluation_mode"] == "COMMON_OUTCOME_EVALUATION"
    assert "not compare actual candidate policy performance" in report["warning"]
    assert "FULL_POLICY_REPLAY" in report["future_work"]
    assert "sample_count" in report["promotion_rule"]
