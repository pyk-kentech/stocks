from datetime import datetime

from stock_risk_mcp.order_intent import OrderSide, OrderType
from stock_risk_mcp.realtime_market_data import MarketRegion
from stock_risk_mcp.strategy_core import (
    DeterministicStrategyEngine,
    StrategyCandidate,
    StrategyConfig,
    StrategyDecisionStatus,
    StrategyFeatureSnapshot,
)


def snapshot(**features) -> StrategyFeatureSnapshot:
    return StrategyFeatureSnapshot(
        snapshot_id="snapshot-1", ticker="abc", region=MarketRegion.US,
        observed_at=datetime(2026, 6, 15), features=features,
    )


def candidate(side=OrderSide.BUY, order_type=OrderType.LIMIT, **metadata) -> StrategyCandidate:
    return StrategyCandidate(
        candidate_id="candidate-1", snapshot_id="snapshot-1", side=side,
        order_type=order_type, quantity=1, limit_price=10, rationale="fixture",
        metadata_json=metadata,
    )


def test_deterministic_engine_produces_candidate_watch_and_missing_data() -> None:
    engine = DeterministicStrategyEngine()
    config = StrategyConfig()
    buy = engine.decide(snapshot(signal_score=0.8, risk_score=0.2, hard_block=False), candidate(), config)
    repeat = engine.decide(snapshot(signal_score=0.8, risk_score=0.2, hard_block=False), candidate(), config)
    watch = engine.decide(snapshot(signal_score=0.2, risk_score=0.2, hard_block=False), candidate(), config)
    missing = engine.decide(snapshot(signal_score=0.8), candidate(), config)

    assert buy.status == repeat.status == StrategyDecisionStatus.CANDIDATE_BUY
    assert buy.reasons == repeat.reasons
    assert watch.status == StrategyDecisionStatus.WATCH
    assert missing.status == StrategyDecisionStatus.NEEDS_MORE_DATA


def test_deterministic_engine_blocks_high_risk_and_forbidden_candidates() -> None:
    engine = DeterministicStrategyEngine()
    features = snapshot(signal_score=-0.9, risk_score=0.2, hard_block=False)

    sell = engine.decide(features, candidate(OrderSide.SELL), StrategyConfig())
    high_risk = engine.decide(snapshot(signal_score=0.8, risk_score=0.9, hard_block=False), candidate(), StrategyConfig())
    market = engine.decide(features, candidate(order_type=OrderType.MARKET), StrategyConfig())
    leveraged = engine.decide(features, candidate(leverage=True), StrategyConfig())

    assert sell.status == StrategyDecisionStatus.CANDIDATE_SELL
    assert sell.requires_sell_safety
    assert high_risk.status == StrategyDecisionStatus.AVOID
    assert market.status == StrategyDecisionStatus.BLOCKED
    assert leveraged.status == StrategyDecisionStatus.BLOCKED
