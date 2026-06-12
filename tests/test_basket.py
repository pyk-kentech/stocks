from __future__ import annotations

import json

from stock_risk_mcp.basket import BasketCandidate, BasketMode, BasketPolicy
from stock_risk_mcp.basket_builder import build_basket
from stock_risk_mcp.cli import main
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.setup import SetupGrade, TradeDecision
from tests.test_basket_builder import candidate


def test_basket_models_normalize_ticker_and_have_policy_defaults() -> None:
    candidate = BasketCandidate(
        ticker=" safe ",
        setup_grade=SetupGrade.A,
        setup_score=85,
        decision=TradeDecision.PROPOSE,
        entry_price=10,
        stop_price=9,
        target_price=14,
        risk_reward_ratio=4,
        max_loss_amount=25,
        position_size=25,
        notional_value=250,
        score=0,
        reasons=[],
        warnings=[],
    )
    policy = BasketPolicy(account_equity=10_000, cash_available=5_000)

    assert candidate.ticker == "SAFE"
    assert policy.basket_name == "momentum_event_basket"
    assert policy.setup_risk_units[SetupGrade.A] == 1.0
    assert policy.setup_risk_units[SetupGrade.B] == 0.5
    assert BasketMode.PAPER_TRADING.value == "PAPER_TRADING"


def test_repository_saves_gets_and_lists_basket_plan(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    plan = build_basket(
        [
            candidate("AAA", SetupGrade.A, TradeDecision.PROPOSE, sector="BIO", theme="AI"),
            candidate("BBB", SetupGrade.A, TradeDecision.PROPOSE, sector="TECH", theme="CLOUD"),
            candidate("CCC", SetupGrade.B, TradeDecision.REVIEW, sector="ENERGY", theme="SOLAR"),
        ],
        BasketPolicy(account_equity=10_000, cash_available=5_000),
    )

    plan_id = repository.save_basket_plan(plan)
    loaded = repository.get_basket_plan(plan.basket_id)

    assert plan_id == 1
    assert loaded.basket_id == plan.basket_id
    assert loaded.decision == plan.decision
    assert repository.get_basket_allocations(plan.basket_id) == plan.allocations
    assert repository.list_basket_plans()[0].basket_id == plan.basket_id


def test_basket_cli_build_save_and_show(tmp_path, capsys) -> None:
    db_path = tmp_path / "risk.sqlite3"
    repository = RiskRepository(db_path)
    for ticker, grade, decision in [
        ("AAA", SetupGrade.A, TradeDecision.PROPOSE),
        ("BBB", SetupGrade.A, TradeDecision.PROPOSE),
        ("CCC", SetupGrade.B, TradeDecision.REVIEW),
    ]:
        repository.save_trade_plan(_trade_plan(ticker, grade, decision))

    common = [
        "--db",
        str(db_path),
        "--account-equity",
        "10000",
        "--cash-available",
        "5000",
        "--max-candidates",
        "10",
    ]
    main(["build-basket-from-trade-plans", *common])
    built = json.loads(capsys.readouterr().out)
    main(["build-basket-and-save", *common])
    saved = json.loads(capsys.readouterr().out)
    main(["show-basket", "--db", str(db_path), "--basket-id", saved["basket_id"]])
    shown = json.loads(capsys.readouterr().out)

    assert built["decision"] in {"PROPOSE", "REVIEW", "NO_TRADE", "BLOCK"}
    assert saved["saved"]["basket_plan_id"] == 1
    assert shown["basket_id"] == saved["basket_id"]
    assert repository.count_rows("basket_plans") == 1
    assert repository.count_rows("basket_allocations") == len(saved["allocations"])


def _trade_plan(ticker, grade, decision):
    from stock_risk_mcp.setup import SetupDirection, TradePlan

    return TradePlan(
        ticker=ticker,
        direction=SetupDirection.LONG,
        setup_grade=grade,
        setup_score=85 if grade == SetupGrade.A else 65,
        entry_price=10,
        stop_price=9,
        target_price=14 if grade == SetupGrade.A else 13,
        risk_reward_ratio=4 if grade == SetupGrade.A else 3,
        max_loss_amount=25,
        position_size=25,
        notional_value=250,
        decision=decision,
        reasons=[],
        warnings=[],
        beginner_summary="fixture",
    )
