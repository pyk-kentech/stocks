from stock_risk_mcp.strategy_ensemble_alpha_engine import build_strategy_ensemble_alpha_gate
from stock_risk_mcp.strategy_ensemble_alpha_models import (
    EnsemblePromotionDecision,
    StrategyEnsembleAlphaInput,
)
from tests.test_strategy_ensemble_alpha_models import strategy_ensemble_alpha_payload


def _evaluate(**overrides):
    payload = strategy_ensemble_alpha_payload()
    payload.update(overrides)
    return build_strategy_ensemble_alpha_gate(StrategyEnsembleAlphaInput.model_validate(payload))


def test_single_alpha_portfolio_is_blocked_or_research_only():
    result = _evaluate(
        portfolio={
            **strategy_ensemble_alpha_payload()["portfolio"],
            "allocations": [{"alpha_id": "alpha-1", "proposed_weight": 1.0}],
        },
        alpha_candidates=[strategy_ensemble_alpha_payload()["alpha_candidates"][0]],
    )
    assert result.ensemble_promotion_readiness_report.decision in {
        EnsemblePromotionDecision.BLOCKED,
        EnsemblePromotionDecision.RESEARCH_ONLY,
    }


def test_diversified_alpha_families_can_become_ensemble_ready():
    result = _evaluate(
        alpha_candidates=[
            {
                **candidate,
                "training_promotion_decision": "TRAINING_READY",
            }
            for candidate in strategy_ensemble_alpha_payload()["alpha_candidates"]
        ],
        portfolio={
            **strategy_ensemble_alpha_payload()["portfolio"],
            "allocations": [
                {"alpha_id": "alpha-1", "proposed_weight": 0.34},
                {"alpha_id": "alpha-2", "proposed_weight": 0.33},
                {"alpha_id": "alpha-3", "proposed_weight": 0.33},
            ],
        },
    )
    assert result.ensemble_promotion_readiness_report.decision in {
        EnsemblePromotionDecision.ENSEMBLE_READY,
        EnsemblePromotionDecision.PAPER_CANDIDATE,
    }


def test_sufficiently_diversified_portfolio_with_valid_refs_can_become_paper_candidate():
    result = _evaluate()
    assert result.ensemble_promotion_readiness_report.decision == EnsemblePromotionDecision.PAPER_CANDIDATE


def test_missing_v73_promotion_ref_causes_gap():
    alpha = {
        **strategy_ensemble_alpha_payload()["alpha_candidates"][0],
        "training_promotion_ref": None,
    }
    result = _evaluate(alpha_candidates=[alpha, *strategy_ensemble_alpha_payload()["alpha_candidates"][1:]])
    assert result.ensemble_promotion_readiness_report.decision == EnsemblePromotionDecision.GAP


def test_blocked_alpha_dependency_blocks_portfolio_promotion():
    alpha = {
        **strategy_ensemble_alpha_payload()["alpha_candidates"][0],
        "training_promotion_decision": "BLOCKED",
    }
    result = _evaluate(alpha_candidates=[alpha, *strategy_ensemble_alpha_payload()["alpha_candidates"][1:]])
    assert result.ensemble_promotion_readiness_report.decision == EnsemblePromotionDecision.BLOCKED


def test_high_alpha_correlation_is_flagged():
    result = _evaluate(
        correlation_matrix_summary={
            "max_pair_correlation": 0.92,
            "high_correlation_pairs": [["alpha-1", "alpha-2"]],
        }
    )
    assert result.alpha_correlation_risk_report.high_alpha_correlation_flagged is True


def test_high_drawdown_co_movement_is_flagged():
    result = _evaluate(
        drawdown_summary={
            "max_drawdown_co_movement": 0.88,
            "high_drawdown_pairs": [["alpha-1", "alpha-2"]],
        }
    )
    assert result.drawdown_co_movement_report.high_drawdown_co_movement_flagged is True


def test_excessive_family_concentration_is_blocked():
    result = _evaluate(
        alpha_candidates=[
            {
                **candidate,
                "strategy_family": "MOMENTUM",
            }
            for candidate in strategy_ensemble_alpha_payload()["alpha_candidates"]
        ]
    )
    assert result.ensemble_promotion_readiness_report.decision == EnsemblePromotionDecision.BLOCKED


def test_excessive_single_alpha_weight_is_blocked():
    result = _evaluate(
        portfolio={
            **strategy_ensemble_alpha_payload()["portfolio"],
            "allocations": [
                {"alpha_id": "alpha-1", "proposed_weight": 0.70},
                {"alpha_id": "alpha-2", "proposed_weight": 0.15},
                {"alpha_id": "alpha-3", "proposed_weight": 0.15},
            ],
        }
    )
    assert result.ensemble_promotion_readiness_report.decision == EnsemblePromotionDecision.BLOCKED


def test_missing_regime_coverage_causes_gap():
    result = _evaluate(
        regime_overlap_summary={
            "regime_coverage_complete": False,
            "overlap_ratio": 0.35,
            "covered_regimes": ["RISK_ON"],
        }
    )
    assert result.ensemble_promotion_readiness_report.decision == EnsemblePromotionDecision.GAP


def test_duplicate_signal_detection_works():
    result = _evaluate(duplicate_signal_detected=True)
    assert result.strategy_family_diversification_report.duplicate_signal_detected is True
