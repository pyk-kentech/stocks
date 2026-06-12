from __future__ import annotations

from stock_risk_mcp.candidate_filters import evaluate_candidate
from stock_risk_mcp.candidate_universe import CandidateDecision, CandidateScanPolicy, CandidateScanResult
from stock_risk_mcp.indicators import analyze_price_bars
from stock_risk_mcp.models import SourceType
from stock_risk_mcp.setup import TradeSizingPolicy
from stock_risk_mcp.setup_grading import SetupGrader
from stock_risk_mcp.trade_plan import create_trade_plan


def scan_candidate(scan_run_id, ticker, as_of_date, price_provider, repository, scan_policy, strategy_policy=None, account_equity=10_000, cash_available=5_000):
    history = price_provider.get_history_until(ticker, as_of_date)
    if not history:
        return CandidateScanResult(
            scan_run_id=scan_run_id, ticker=ticker, as_of_date=as_of_date, decision=CandidateDecision.EXCLUDE,
            score=0, reasons=["Insufficient as-of price history; at least 120 bars required."],
            warnings=["Compliance status unknown"] if not repository.get_compliance_records(ticker) else [],
            metadata={"scoring_mode": "POLICY_WEIGHTED" if strategy_policy else "FIXED_RULES"},
        )
    indicator_set, _ = analyze_price_bars(ticker, history, "candidate_scanner", SourceType.SYSTEM)
    setup = SetupGrader().grade(indicator_set, strategy_policy)
    trade = create_trade_plan(setup, history, TradeSizingPolicy(account_equity=account_equity, cash_available=cash_available))
    values = {item.indicator_code: item.value for item in indicator_set.indicators}
    records = repository.get_compliance_records(ticker)
    result = evaluate_candidate(
        scan_run_id, ticker, as_of_date, scan_policy, setup.grade, setup.score, trade.decision, history[-1].close,
        values.get("RETURN_1D_PCT"), values.get("RETURN_5D_PCT"), values.get("RETURN_20D_PCT"),
        values.get("AVG_DOLLAR_VOLUME_20D"), values.get("VOLUME_SPIKE_RATIO"),
        values.get("DOLLAR_VOLUME_SPIKE_RATIO"), values.get("VOLATILITY_20D_PCT"),
        trade.risk_reward_ratio, True if records else None,
        {"trade_plan": trade.model_dump(mode="json"), "last_price_date": history[-1].date.isoformat(),
         "policy_id": trade.policy_id, "policy_version": trade.policy_version, "scoring_mode": trade.setup_scoring_mode},
    )
    return result.model_copy(update={"reasons": [*setup.reasons, *result.reasons], "warnings": [*setup.warnings, *result.warnings]})
