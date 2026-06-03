from __future__ import annotations

from dataclasses import dataclass

from stock_risk_mcp.models import CompanyRisk, MarketSnapshot, NewsEvent, RiskPolicy, RiskResult, TossSignal, TradeProposal
from stock_risk_mcp.provenance import MOCK_DATA_SOURCES
from stock_risk_mcp.repository import RiskRepository


@dataclass(frozen=True)
class SavedEvaluation:
    evaluation_id: int
    market_snapshot_id: int
    company_risk_id: int
    toss_investor_snapshot_id: int
    news_event_ids: list[int]


def save_evaluation_inputs_and_result(
    repository: RiskRepository,
    proposal: TradeProposal,
    policy: RiskPolicy,
    market: MarketSnapshot,
    company: CompanyRisk,
    toss_signal: TossSignal,
    result: RiskResult,
    news_events: list[NewsEvent] | None = None,
    source: str = "adapter",
) -> SavedEvaluation:
    market_id = repository.save_market_snapshot(market, source=source)
    company_id = repository.save_company_risk(company, source=source)
    toss_id = repository.save_toss_signal(proposal.ticker, toss_signal, source=source)
    news_ids = [repository.save_news_event(event) for event in news_events or []]
    evaluation_id = repository.save_risk_evaluation(
        proposal=proposal,
        policy=policy,
        result=result,
        market_snapshot_id=market_id,
        company_risk_id=company_id,
        toss_investor_snapshot_id=toss_id,
    )
    for data_source in MOCK_DATA_SOURCES:
        repository.upsert_data_source(data_source)
    repository.save_evaluation_reasons(evaluation_id, result.reason_details)
    return SavedEvaluation(
        evaluation_id=evaluation_id,
        market_snapshot_id=market_id,
        company_risk_id=company_id,
        toss_investor_snapshot_id=toss_id,
        news_event_ids=news_ids,
    )
