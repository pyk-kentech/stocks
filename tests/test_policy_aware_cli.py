from __future__ import annotations

import csv
import json
from datetime import date, timedelta

from stock_risk_mcp.cli import main
from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.setup import SetupDirection, SetupGrade, TradeDecision, TradePlan
from stock_risk_mcp.strategy_policy import create_default_strategy_policy


def test_setup_and_trade_plan_cli_default_fixed_and_active_policy_modes(tmp_path, capsys) -> None:
    db_path = tmp_path / "risk.sqlite3"
    price_file = tmp_path / "prices.csv"
    _write_prices(price_file)
    repository = RiskRepository(db_path)
    repository.save_strategy_policy(create_default_strategy_policy())

    fixed = _run(capsys, ["analyze-setup", "--ticker", "SAFE", "--price-history-file", str(price_file)])
    active = _run(
        capsys,
        [
            "create-trade-plan-and-save",
            "--ticker",
            "SAFE",
            "--price-history-file",
            str(price_file),
            "--db",
            str(db_path),
            "--account-equity",
            "10000",
            "--cash-available",
            "5000",
            "--use-active-policy",
        ],
    )
    explicit = _run(
        capsys,
        [
            "analyze-setup",
            "--ticker",
            "SAFE",
            "--price-history-file",
            str(price_file),
            "--db",
            str(db_path),
            "--policy-id",
            "default",
            "--policy-version",
            "v1",
        ],
    )

    assert fixed["scoring_mode"] == "FIXED_RULES"
    assert active["setup_scoring_mode"] == "POLICY_WEIGHTED"
    assert active["policy_id"] == "default"
    assert explicit["scoring_mode"] == "POLICY_WEIGHTED"


def test_basket_and_paper_cli_use_active_policy(tmp_path, capsys) -> None:
    db_path = tmp_path / "risk.sqlite3"
    repository = RiskRepository(db_path)
    repository.save_strategy_policy(create_default_strategy_policy())
    repository.save_trade_plan(_trade_plan())

    basket = _run(
        capsys,
        [
            "build-basket-and-save",
            "--db",
            str(db_path),
            "--account-equity",
            "10000",
            "--cash-available",
            "5000",
            "--min-candidates",
            "1",
            "--use-active-policy",
        ],
    )
    repository.save_price_bars(
        [PriceBar(ticker="SAFE", date=date.today(), low=9.5, high=14.5, close=14)]
    )
    paper = _run(
        capsys,
        [
            "paper-trade-basket",
            "--db",
            str(db_path),
            "--basket-id",
            basket["basket_id"],
            "--horizon-days",
            "10",
        ],
    )

    assert basket["basket_scoring_mode"] == "POLICY_WEIGHTED"
    assert basket["policy_id"] == "default"
    assert paper["policy_id"] == "default"
    assert paper["trades"][0]["policy_version"] == "v1"


def _run(capsys, args: list[str]) -> dict:
    main(args)
    return json.loads(capsys.readouterr().out)


def _write_prices(path) -> None:
    start = date(2026, 1, 1)
    bars = [
        PriceBar(
            ticker="SAFE",
            date=start + timedelta(days=index),
            high=101 + index * 0.1,
            low=99 + index * 0.1,
            close=100 + index * 0.1,
            volume=1_000_000 if index < 120 else 3_000_000,
        )
        for index in range(121)
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["ticker", "date", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        for bar in bars:
            writer.writerow(bar.model_dump(mode="json"))


def _trade_plan() -> TradePlan:
    return TradePlan(
        ticker="SAFE",
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
        beginner_summary="fixture",
    )
