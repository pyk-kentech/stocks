from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.candidate_scanner import scan_candidate
from stock_risk_mcp.candidate_universe import (
    CandidateDecision,
    CandidateScanPolicy,
    CandidateScanResult,
    CandidateSource,
    ScanRun,
    ScanRunStatus,
)
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_policy import StrategyPolicy


class ScanPipelineResult(StrictModel):
    run: ScanRun
    results: list[CandidateScanResult] = Field(default_factory=list)
    saved: bool = False


def run_candidate_scan(
    repository,
    price_provider,
    tickers: list[str],
    as_of_date: date,
    source: CandidateSource,
    policy: CandidateScanPolicy,
    strategy_policy: StrategyPolicy | None = None,
    save: bool = False,
    account_equity: float = 10_000,
    cash_available: float = 5_000,
) -> ScanPipelineResult:
    scan_run_id = uuid4().hex
    results = [
        _scan_one(
            repository,
            price_provider,
            scan_run_id,
            ticker,
            as_of_date,
            policy,
            strategy_policy,
            account_equity,
            cash_available,
        )
        for ticker in tickers
    ]
    results = _apply_candidate_limit(results, policy.max_candidates)
    run = ScanRun(
        scan_run_id=scan_run_id,
        as_of_date=as_of_date,
        source=source,
        policy_id=strategy_policy.policy_id if strategy_policy else None,
        policy_version=strategy_policy.version if strategy_policy else None,
        universe_size=len(tickers),
        included_count=sum(item.decision == CandidateDecision.INCLUDE for item in results),
        watch_count=sum(item.decision == CandidateDecision.WATCH for item in results),
        excluded_count=sum(item.decision == CandidateDecision.EXCLUDE for item in results),
        status=ScanRunStatus.COMPLETED if results else ScanRunStatus.NO_DATA,
        notes=[
            "Candidate scan used only price history on or before as_of_date.",
            "Scan results are research records, not investment recommendations.",
        ],
        created_at=datetime.now(),
    )
    if save:
        repository.save_scan_run(run)
        repository.save_candidate_scan_results(results)
    return ScanPipelineResult(run=run, results=results, saved=save)


def _scan_one(
    repository,
    price_provider,
    scan_run_id: str,
    ticker: str,
    as_of_date: date,
    policy: CandidateScanPolicy,
    strategy_policy: StrategyPolicy | None,
    account_equity: float,
    cash_available: float,
) -> CandidateScanResult:
    try:
        return scan_candidate(
            scan_run_id,
            ticker,
            as_of_date,
            price_provider,
            repository,
            policy,
            strategy_policy,
            account_equity,
            cash_available,
        )
    except Exception as exc:
        return CandidateScanResult(
            scan_run_id=scan_run_id,
            ticker=ticker,
            as_of_date=as_of_date,
            decision=CandidateDecision.EXCLUDE,
            score=0,
            reasons=[f"Candidate scan failed: {exc}"],
            metadata={"scoring_mode": "POLICY_WEIGHTED" if strategy_policy else "FIXED_RULES"},
        )


def _apply_candidate_limit(results: list[CandidateScanResult], max_candidates: int) -> list[CandidateScanResult]:
    ranked = sorted(results, key=lambda item: item.score, reverse=True)
    selected_count = 0
    limited: list[CandidateScanResult] = []
    for result in ranked:
        if result.decision == CandidateDecision.EXCLUDE:
            limited.append(result)
            continue
        selected_count += 1
        if selected_count <= max_candidates:
            limited.append(result)
            continue
        limited.append(
            result.model_copy(
                update={
                    "decision": CandidateDecision.EXCLUDE,
                    "reasons": [*result.reasons, "Excluded by scan policy max_candidates limit."],
                }
            )
        )
    return limited
