from __future__ import annotations

import sqlite3
from datetime import date

from stock_risk_mcp.basket import BasketCandidate, BasketPolicy
from stock_risk_mcp.basket_backtest import run_basket_backtest
from stock_risk_mcp.basket_builder import build_basket
from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.setup import SetupGrade, TradeDecision
from stock_risk_mcp.strategy_memory import create_memories_from_paper_trades, create_memory_from_basket_result
from stock_risk_mcp.strategy_policy import apply_strategy_policy_to_basket_policy, create_default_strategy_policy


def test_policy_aware_basket_filters_block_before_scoring_and_propagates_metadata() -> None:
    strategy = create_default_strategy_policy()
    basket_policy = apply_strategy_policy_to_basket_policy(
        BasketPolicy(account_equity=10_000, cash_available=5_000, min_candidates=1),
        strategy,
    )
    blocked = _candidate("BLOCK", TradeDecision.BLOCK, score=7)

    plan = build_basket([_candidate("SAFE", TradeDecision.PROPOSE), blocked], basket_policy, strategy)

    assert plan.policy_id == "default"
    assert plan.policy_version == "v1"
    assert plan.basket_scoring_mode == "POLICY_WEIGHTED"
    assert next(item for item in plan.candidates if item.ticker == "BLOCK").score == 7


def test_policy_metadata_reaches_paper_results_memory_and_repository(tmp_path) -> None:
    strategy = create_default_strategy_policy()
    basket_policy = apply_strategy_policy_to_basket_policy(
        BasketPolicy(account_equity=10_000, cash_available=5_000, min_candidates=1),
        strategy,
    )
    plan = build_basket([_candidate("SAFE", TradeDecision.PROPOSE)], basket_policy, strategy)
    result, trades = run_basket_backtest(
        plan,
        {"SAFE": [PriceBar(ticker="SAFE", date=date.today(), low=9.5, high=14.5, close=14)]},
        date.today(),
        10,
    )
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    plan_row = repository.save_basket_plan(plan)
    trade_row = repository.save_paper_trade(trades[0])
    result_row = repository.save_basket_backtest_result(result)

    assert plan_row == trade_row == result_row == 1
    assert trades[0].policy_id == result.policy_id == "default"
    assert repository.get_basket_plan(plan.basket_id).policy_version == "v1"
    assert repository.list_paper_trades(plan.basket_id)[0].policy_id == "default"
    assert repository.get_basket_backtest_result(plan.basket_id).policy_id == "default"
    assert create_memory_from_basket_result(result).features_json["basket_scoring_mode"] == "POLICY_WEIGHTED"
    trade_memory = create_memories_from_paper_trades(trades)[0]
    assert trade_memory.features_json["policy_id"] == "default"
    assert trade_memory.features_json["basket_scoring_mode"] == "POLICY_WEIGHTED"


def test_existing_basket_and_paper_tables_get_nullable_policy_columns(tmp_path) -> None:
    path = tmp_path / "old.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE basket_plans (id INTEGER PRIMARY KEY)")
        connection.execute("CREATE TABLE paper_trades (id INTEGER PRIMARY KEY)")
        connection.execute("CREATE TABLE basket_backtest_results (id INTEGER PRIMARY KEY)")

    RiskRepository(path)

    with sqlite3.connect(path) as connection:
        basket_columns = {row[1] for row in connection.execute("PRAGMA table_info(basket_plans)")}
        trade_columns = {row[1] for row in connection.execute("PRAGMA table_info(paper_trades)")}
        result_columns = {row[1] for row in connection.execute("PRAGMA table_info(basket_backtest_results)")}
    assert {"policy_id", "policy_version", "basket_scoring_mode"} <= basket_columns
    assert {"policy_id", "policy_version"} <= trade_columns
    assert {"policy_id", "policy_version"} <= result_columns


def _candidate(ticker: str, decision: TradeDecision, score: int = 0) -> BasketCandidate:
    return BasketCandidate(
        ticker=ticker,
        setup_grade=SetupGrade.A,
        setup_score=85,
        decision=decision,
        entry_price=10,
        stop_price=9,
        target_price=14,
        risk_reward_ratio=4,
        max_loss_amount=25,
        position_size=25,
        notional_value=250,
        score=score,
        reasons=[],
        warnings=[],
    )
