from __future__ import annotations

import sqlite3

from stock_risk_mcp.indicators import IndicatorSet, IndicatorSignal, IndicatorValue
from stock_risk_mcp.models import Severity
from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.setup import SetupGrade, TradeSizingPolicy
from stock_risk_mcp.setup_grading import SetupGrader, grade_setup
from stock_risk_mcp.strategy_policy import create_default_strategy_policy, normalize_weights
from stock_risk_mcp.trade_plan import create_trade_plan
from datetime import date, timedelta


def test_policy_none_preserves_fixed_setup_grading() -> None:
    indicators = _indicator_set(RETURN_5D_PCT=10, AVG_DOLLAR_VOLUME_20D=60_000_000)

    original = SetupGrader().grade(indicators)
    explicit = grade_setup(indicators, None)

    assert explicit == original
    assert explicit.scoring_mode == "FIXED_RULES"
    assert explicit.policy_id is None


def test_strategy_policy_uses_weighted_scoring_and_policy_thresholds() -> None:
    policy = create_default_strategy_policy().model_copy(
        update={"setup_thresholds": {"A": 95, "B": 70, "C": 20, "NO_TRADE": 0}}
    )

    setup = grade_setup(_strong_indicator_set(), policy)

    assert setup.scoring_mode == "POLICY_WEIGHTED"
    assert setup.policy_id == "default"
    assert setup.policy_version == "v1"
    assert setup.grade == SetupGrade.B


def test_changing_policy_weights_changes_setup_score() -> None:
    indicators = _indicator_set(RETURN_5D_PCT=10, AVG_DOLLAR_VOLUME_20D=1_000_000)
    baseline = create_default_strategy_policy()
    return_heavy = baseline.model_copy(
        update={
            "weights": normalize_weights(
                {key: (0.8 if key == "return_5d_score" else 0.01) for key in baseline.weights}
            )
        }
    )
    liquidity_heavy = baseline.model_copy(
        update={
            "weights": normalize_weights(
                {key: (0.8 if key == "dollar_volume_score" else 0.01) for key in baseline.weights}
            )
        }
    )

    assert grade_setup(indicators, return_heavy).score > grade_setup(indicators, liquidity_heavy).score


def test_trade_plan_propagates_and_persists_setup_policy_metadata(tmp_path) -> None:
    setup = grade_setup(_strong_indicator_set(), create_default_strategy_policy())
    plan = create_trade_plan(setup, _bars(), TradeSizingPolicy(account_equity=10_000, cash_available=5_000))
    repository = RiskRepository(tmp_path / "risk.sqlite3")

    plan_id = repository.save_trade_plan(plan)

    assert plan.policy_id == "default"
    assert plan.policy_version == "v1"
    assert plan.setup_scoring_mode == "POLICY_WEIGHTED"
    assert repository.get_trade_plan(plan_id) == plan


def test_existing_trade_plans_table_gets_nullable_policy_columns(tmp_path) -> None:
    path = tmp_path / "old.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE trade_plans (id INTEGER PRIMARY KEY)")

    RiskRepository(path)

    with sqlite3.connect(path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(trade_plans)")}
    assert {"policy_id", "policy_version", "setup_scoring_mode"} <= columns


def _strong_indicator_set() -> IndicatorSet:
    return _indicator_set(
        RETURN_5D_PCT=10,
        RETURN_20D_PCT=20,
        DISTANCE_FROM_SMA_20_PCT=5,
        DISTANCE_FROM_SMA_60_PCT=10,
        RSI_14=55,
        VOLUME_SPIKE_RATIO=3,
        AVG_DOLLAR_VOLUME_20D=60_000_000,
        VOLATILITY_20D_PCT=3,
        MAX_DRAWDOWN_60D_PCT=-10,
        BOLLINGER_POSITION=0.5,
    )


def _indicator_set(**values: float) -> IndicatorSet:
    return IndicatorSet(
        ticker="SAFE",
        indicators=[
            IndicatorValue(
                ticker="SAFE",
                indicator_code=code,
                category="TEST",
                value=value,
                signal=IndicatorSignal.NEUTRAL,
                severity=Severity.LOW,
                interpretation=code,
                beginner_explanation=code,
            )
            for code, value in values.items()
        ],
    )


def _bars() -> list[PriceBar]:
    start = date(2026, 1, 1)
    return [
        PriceBar(ticker="SAFE", date=start + timedelta(days=index), high=101, low=99, close=100, volume=1000)
        for index in range(21)
    ]
