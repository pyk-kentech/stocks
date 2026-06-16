from __future__ import annotations

from stock_risk_mcp.walk_forward_policy_models import CandidatePolicyComparison, PolicyPromotionGates


def decide_promotion(comparison: CandidatePolicyComparison, gates: PolicyPromotionGates) -> CandidatePolicyComparison:
    reasons: list[str] = []
    candidate = comparison.aggregate_candidate_metrics
    if candidate.safety_violation:
        return comparison.model_copy(update={"promotion_decision": "REJECT_UNSAFE_POLICY", "gate_reasons": ["SAFETY_VIOLATION"]})
    if candidate.trade_count < gates.minimum_sample_count:
        return comparison.model_copy(update={"promotion_decision": "INSUFFICIENT_EVIDENCE", "gate_reasons": ["MINIMUM_SAMPLE_COUNT_NOT_MET"]})
    if candidate.max_drawdown_pct > gates.max_drawdown_pct_cap:
        return comparison.model_copy(update={"promotion_decision": "DEMOTE_CANDIDATE_POLICY", "gate_reasons": ["MAX_DRAWDOWN_CAP_EXCEEDED"]})
    if candidate.missing_data_rate > gates.max_missing_data_rate:
        return comparison.model_copy(update={"promotion_decision": "INSUFFICIENT_EVIDENCE", "gate_reasons": ["MISSING_DATA_RATE_TOO_HIGH"]})
    if candidate.blocked_rate > gates.max_blocked_rate:
        return comparison.model_copy(update={"promotion_decision": "DEMOTE_CANDIDATE_POLICY", "gate_reasons": ["BLOCKED_RATE_TOO_HIGH"]})
    if comparison.aggregate_return_delta_pct < 0:
        return comparison.model_copy(update={"promotion_decision": "DEMOTE_CANDIDATE_POLICY", "gate_reasons": ["UNDERPERFORMED_BASELINE"]})
    if comparison.aggregate_return_delta_pct < gates.minimum_return_improvement_pct:
        reasons.append("IMPROVEMENT_THRESHOLD_NOT_MET")
        return comparison.model_copy(update={"promotion_decision": "KEEP_BASELINE_POLICY", "gate_reasons": reasons})
    if comparison.stability_score < gates.minimum_stability_score:
        return comparison.model_copy(update={"promotion_decision": "INSUFFICIENT_EVIDENCE", "gate_reasons": ["STABILITY_THRESHOLD_NOT_MET"]})
    return comparison.model_copy(update={"promotion_decision": "PROMOTE_CANDIDATE_POLICY", "gate_reasons": []})
