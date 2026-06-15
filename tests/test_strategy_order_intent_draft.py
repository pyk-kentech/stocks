from stock_risk_mcp.order_intent import OrderIntentStatus
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.strategy_core import (
    StrategyCandidate, StrategyCandidateOrderType, StrategyCandidateSide,
    StrategyDecision, StrategyDecisionReason, StrategyDecisionStatus, StrategyFeatureSnapshot,
)
from stock_risk_mcp.strategy_order_intent_draft import create_order_intent_draft
from stock_risk_mcp.realtime_market_data import MarketRegion


def seed(repository, side=StrategyCandidateSide.BUY, order_type=StrategyCandidateOrderType.LIMIT, metadata=None):
    snapshot = StrategyFeatureSnapshot(snapshot_id="s1", ticker="ABC", region=MarketRegion.US, features={})
    candidate = StrategyCandidate(
        candidate_id="c1", snapshot_id="s1", side=side, order_type=order_type,
        quantity=1, limit_price=10, rationale="fixture", metadata_json=metadata or {},
    )
    status = StrategyDecisionStatus.CANDIDATE_BUY if side == StrategyCandidateSide.BUY else StrategyDecisionStatus.CANDIDATE_SELL
    decision = StrategyDecision(
        decision_id="d1", run_id="r1", candidate_id="c1", snapshot_id="s1", status=status,
        reasons=[StrategyDecisionReason.BUY_SIGNAL if side == StrategyCandidateSide.BUY else StrategyDecisionReason.SELL_SIGNAL],
        confidence_score=0.8, draft_order_intent_allowed=True,
        requires_sell_safety=side == StrategyCandidateSide.SELL,
    )
    repository.save_strategy_feature_snapshot(snapshot, "r1")
    repository.save_strategy_candidate(candidate, "r1")
    repository.save_strategy_decision(decision)
    return decision


def test_candidate_buy_and_sell_create_created_draft_only(tmp_path) -> None:
    buy_repo = RiskRepository(tmp_path / "buy.sqlite3")
    buy = create_order_intent_draft(buy_repo, seed(buy_repo))
    assert buy.status == OrderIntentStatus.CREATED
    assert buy.metadata_json["requires_risk_gate"] is True
    assert buy.metadata_json["requires_execution_gate"] is True

    sell_repo = RiskRepository(tmp_path / "sell.sqlite3")
    sell = create_order_intent_draft(sell_repo, seed(sell_repo, StrategyCandidateSide.SELL))
    assert sell.status == OrderIntentStatus.CREATED
    assert sell.metadata_json["requires_sell_safety"] is True


def test_market_and_forbidden_exposure_create_no_draft(tmp_path) -> None:
    for order_type, metadata in (
        (StrategyCandidateOrderType.MARKET, {}),
        (StrategyCandidateOrderType.LIMIT, {"leverage": True}),
    ):
        repository = RiskRepository(tmp_path / f"{order_type.value}-{len(metadata)}.sqlite3")
        decision = seed(repository, order_type=order_type, metadata=metadata)
        try:
            create_order_intent_draft(repository, decision)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe draft must be blocked")
        assert repository.list_order_intents() == []
