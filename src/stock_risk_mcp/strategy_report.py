from __future__ import annotations

from stock_risk_mcp.strategy_experiments import StrategyExperiment
from stock_risk_mcp.strategy_policy import StrategyPolicy


def build_strategy_report(
    policies: list[StrategyPolicy],
    experiments: list[StrategyExperiment],
) -> dict[str, object]:
    return {
        "evaluation_mode": "COMMON_OUTCOME_EVALUATION",
        "warning": (
            "COMMON_OUTCOME_EVALUATION does not compare actual candidate policy performance; "
            "all policies use the same stored basket outcomes."
        ),
        "promotion_rule": "Policies with sample_count below 30 must not be promoted.",
        "future_work": (
            "FULL_POLICY_REPLAY is available as a separate as-of-date policy comparison workflow. "
            "FEATURE_RESCORING remains unimplemented."
        ),
        "policies": [policy.model_dump(mode="json") for policy in policies],
        "experiments": [experiment.model_dump(mode="json") for experiment in experiments],
    }
