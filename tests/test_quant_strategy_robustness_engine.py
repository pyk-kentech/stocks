from stock_risk_mcp.quant_strategy_robustness_engine import build_quant_strategy_robustness
from stock_risk_mcp.quant_strategy_robustness_models import QuantStrategyRobustnessDecision
from tests.test_quant_strategy_robustness_models import quant_strategy_robustness_payload


def _evaluate(**overrides):
    payload = quant_strategy_robustness_payload()
    payload.update(overrides)
    from stock_risk_mcp.quant_strategy_robustness_models import QuantStrategyRobustnessInput

    return build_quant_strategy_robustness(QuantStrategyRobustnessInput.model_validate(payload))


def test_point_in_time_universe_dataset_can_become_training_ready():
    result = _evaluate()
    assert result.robustness_readiness_report.decision == QuantStrategyRobustnessDecision.TRAINING_READY


def test_current_survivors_only_dataset_is_downgraded():
    result = _evaluate(
        universe_policy={
            **quant_strategy_robustness_payload()["universe_policy"],
            "universe_mode": "CURRENT_SURVIVORS_ONLY",
            "historical_universe_snapshots_available": False,
            "delisted_handled": False,
        }
    )
    assert result.robustness_readiness_report.decision in {
        QuantStrategyRobustnessDecision.RESEARCH_READY,
        QuantStrategyRobustnessDecision.GAP,
    }


def test_missing_available_at_causes_gap():
    result = _evaluate(
        point_in_time_policy={
            **quant_strategy_robustness_payload()["point_in_time_policy"],
            "event_features_have_available_at": False,
        }
    )
    assert result.robustness_readiness_report.decision == QuantStrategyRobustnessDecision.GAP


def test_future_leakage_is_blocked():
    result = _evaluate(
        point_in_time_policy={
            **quant_strategy_robustness_payload()["point_in_time_policy"],
            "future_data_leakage_blocked": False,
        }
    )
    assert result.robustness_readiness_report.decision == QuantStrategyRobustnessDecision.BLOCKED


def test_missing_delisting_or_corporate_action_policy_causes_gap():
    result = _evaluate(
        point_in_time_policy={
            **quant_strategy_robustness_payload()["point_in_time_policy"],
            "corporate_action_policy_present": False,
            "delisting_policy_present": False,
        }
    )
    assert result.robustness_readiness_report.decision == QuantStrategyRobustnessDecision.GAP


def test_walk_forward_split_is_accepted():
    result = _evaluate()
    assert result.walk_forward_policy_report.walk_forward_ready is True


def test_repeated_final_test_tuning_is_rejected():
    result = _evaluate(
        walk_forward_policy={
            **quant_strategy_robustness_payload()["walk_forward_policy"],
            "repeated_final_test_tuning_count": 2,
            "final_test_period_reused_for_tuning": True,
        }
    )
    assert result.robustness_readiness_report.decision == QuantStrategyRobustnessDecision.BLOCKED


def test_excessive_parameter_search_is_flagged():
    result = _evaluate(
        walk_forward_policy={
            **quant_strategy_robustness_payload()["walk_forward_policy"],
            "parameter_search_count": 99,
            "max_parameter_search_count": 20,
        }
    )
    assert result.data_snooping_report.excessive_parameter_search_flagged is True


def test_strategy_diversification_families_are_represented():
    result = _evaluate()
    assert result.strategy_diversification_report.family_count >= 3


def test_high_strategy_correlation_and_drawdown_comovement_are_flagged():
    result = _evaluate(
        diversification_policy={
            **quant_strategy_robustness_payload()["diversification_policy"],
            "max_pairwise_strategy_correlation": 0.95,
            "max_drawdown_comovement": 0.85,
        }
    )
    assert result.strategy_diversification_report.strategy_correlation_flagged is True
    assert result.strategy_diversification_report.drawdown_comovement_flagged is True


def test_regime_bucket_gaps_are_reported():
    result = _evaluate(
        regime_policy={
            **quant_strategy_robustness_payload()["regime_policy"],
            "evaluated_bucket_count": 2,
        }
    )
    assert result.regime_readiness_report.missing_bucket_count == 4
