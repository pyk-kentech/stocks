from __future__ import annotations

from stock_risk_mcp.setup import SetupDirection, SetupGrade, SetupSignal, TradeDecision, TradePlan, TradeSizingPolicy


def test_setup_and_trade_plan_models_normalize_ticker() -> None:
    signal = SetupSignal(
        ticker=" safe ",
        direction=SetupDirection.LONG,
        grade=SetupGrade.A,
        score=85,
        reasons=["strong"],
        warnings=[],
        indicator_codes_used=["RETURN_5D_PCT"],
        beginner_summary="A setup",
    )
    plan = TradePlan(
        ticker=" safe ",
        direction=SetupDirection.LONG,
        setup_grade=SetupGrade.A,
        setup_score=85,
        entry_price=10,
        stop_price=9,
        target_price=14,
        risk_reward_ratio=4,
        max_loss_amount=25,
        position_size=25,
        notional_value=250,
        decision=TradeDecision.PROPOSE,
        reasons=[],
        warnings=[],
        beginner_summary="proposal",
    )
    policy = TradeSizingPolicy(account_equity=10_000, cash_available=5_000)

    assert signal.ticker == "SAFE"
    assert plan.ticker == "SAFE"
    assert policy.setup_risk_multipliers[SetupGrade.A] == 1.0
    assert policy.setup_risk_multipliers[SetupGrade.C] == 0.0
