from __future__ import annotations

import csv
import json
from datetime import date, timedelta

import pytest

from stock_risk_mcp.cli import main
from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.setup import SetupDirection, SetupGrade, SetupSignal, TradeDecision, TradeSizingPolicy
from stock_risk_mcp.trade_plan import create_trade_plan
from stock_risk_mcp.repository import RiskRepository


@pytest.mark.parametrize(
    ("grade", "expected_rr", "expected_decision"),
    [
        (SetupGrade.A, 4.0, TradeDecision.PROPOSE),
        (SetupGrade.B, 3.0, TradeDecision.REVIEW),
    ],
)
def test_trade_plan_uses_grade_target_rr(grade, expected_rr, expected_decision) -> None:
    plan = create_trade_plan(_setup(grade), _bars(), TradeSizingPolicy(account_equity=10_000, cash_available=5_000))

    assert plan.direction == SetupDirection.LONG
    assert plan.risk_reward_ratio == pytest.approx(expected_rr)
    assert plan.decision == expected_decision
    assert plan.position_size is not None and plan.position_size > 0


def test_c_setup_does_not_trade() -> None:
    plan = create_trade_plan(
        _setup(SetupGrade.C),
        _bars(),
        TradeSizingPolicy(account_equity=10_000, cash_available=5_000),
    )

    assert plan.decision == TradeDecision.NO_TRADE
    assert plan.entry_price is None
    assert plan.position_size is None


def test_repository_saves_gets_and_lists_trade_plans(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    plan = create_trade_plan(_setup(SetupGrade.A), _bars(), TradeSizingPolicy(account_equity=10_000, cash_available=5_000))

    plan_id = repository.save_trade_plan(plan)

    assert repository.count_rows("trade_plans") == 1
    assert repository.get_trade_plan(plan_id) == plan
    assert repository.list_trade_plans("safe") == [plan]


def test_setup_and_trade_plan_cli_commands(tmp_path, capsys) -> None:
    price_file = tmp_path / "prices.csv"
    db_path = tmp_path / "risk.sqlite3"
    _write_price_csv(price_file, _strong_setup_bars())

    main(["analyze-setup", "--ticker", "SAFE", "--price-history-file", str(price_file)])
    setup_output = json.loads(capsys.readouterr().out)

    common = [
        "--ticker",
        "SAFE",
        "--price-history-file",
        str(price_file),
        "--account-equity",
        "10000",
        "--cash-available",
        "5000",
    ]
    main(["create-trade-plan", *common])
    plan_output = json.loads(capsys.readouterr().out)
    main(["create-trade-plan-and-save", *common, "--db", str(db_path)])
    saved_output = json.loads(capsys.readouterr().out)

    assert setup_output["grade"] in {"A", "B", "C", "NO_TRADE"}
    assert plan_output["decision"] in {"PROPOSE", "REVIEW", "NO_TRADE", "BLOCK"}
    assert saved_output["saved"]["trade_plan_id"] == 1
    assert RiskRepository(db_path).count_rows("trade_plans") == 1


def _setup(grade: SetupGrade) -> SetupSignal:
    return SetupSignal(
        ticker="SAFE",
        direction=SetupDirection.LONG,
        grade=grade,
        score={SetupGrade.A: 85, SetupGrade.B: 65, SetupGrade.C: 45}[grade],
        reasons=["fixture"],
        warnings=[],
        indicator_codes_used=["ATR_14_PCT"],
        beginner_summary="fixture",
    )


def _bars() -> list[PriceBar]:
    start = date(2026, 1, 1)
    return [
        PriceBar(ticker="SAFE", date=start + timedelta(days=index), high=101, low=99, close=100, volume=1000)
        for index in range(21)
    ]


def _strong_setup_bars() -> list[PriceBar]:
    start = date(2026, 1, 1)
    bars: list[PriceBar] = []
    for index in range(121):
        close = 100 + index * 0.1
        volume = 1_000_000 if index < 120 else 3_000_000
        bars.append(
            PriceBar(
                ticker="SAFE",
                date=start + timedelta(days=index),
                high=close + 1,
                low=close - 1,
                close=close,
                volume=volume,
            )
        )
    return bars


def _write_price_csv(path, bars: list[PriceBar]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["ticker", "date", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        for bar in bars:
            writer.writerow(bar.model_dump(mode="json"))
