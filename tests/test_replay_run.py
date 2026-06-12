import json
from datetime import date, datetime, timedelta

from stock_risk_mcp.basket import BasketMode, BasketPlan, BasketPolicy, BasketRiskSummary
from stock_risk_mcp.cli import main
from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.replay_dataset import load_replay_dataset
from stock_risk_mcp.replay_run import ReplayRunService
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.setup import SetupDirection, SetupGrade, TradeDecision, TradePlan


def test_existing_basket_replay_snapshot_preserves_source_and_loads_dataset(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    plan = _empty_plan("official-basket")
    repository.save_basket_plan(plan)

    result = ReplayRunService(repository).snapshot_from_basket(plan.basket_id, as_of_date=date(2026, 6, 13))
    dataset = load_replay_dataset(repository, result.run.run_id)

    assert result.saved_to_basket_plans is True
    assert dataset.run.source_basket_id == "official-basket"
    assert dataset.basket is not None
    assert dataset.outcome is None
    assert any("metadata" in note for note in dataset.run.notes)


def test_recent_trade_plan_replay_is_snapshot_only_by_default(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    for ticker in ("AAA", "BBB", "CCC"):
        repository.save_trade_plan(_trade_plan(ticker))

    result = ReplayRunService(repository).snapshot_from_recent_trade_plans(
        account_equity=10_000,
        cash_available=5_000,
        max_candidates=3,
        as_of_date=date(2026, 6, 13),
    )

    assert result.saved_to_basket_plans is False
    assert repository.count_rows("basket_plans") == 0
    assert repository.get_replay_basket_snapshot(result.run.run_id).basket_id == result.basket.basket_id
    assert "Basket was stored only as replay snapshot." in result.run.notes
    assert "saved_to_basket_plans: false" in result.run.notes


def test_recent_trade_plan_replay_saves_official_basket_only_when_requested(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    for ticker in ("AAA", "BBB", "CCC"):
        repository.save_trade_plan(_trade_plan(ticker))

    result = ReplayRunService(repository).snapshot_from_recent_trade_plans(
        account_equity=10_000,
        cash_available=5_000,
        max_candidates=3,
        save_basket=True,
    )

    assert result.saved_to_basket_plans is True
    assert repository.count_rows("basket_plans") == 1
    assert repository.get_basket_plan(result.basket.basket_id).basket_id == result.basket.basket_id
    assert "Basket was also saved to basket_plans." in result.run.notes
    assert "saved_to_basket_plans: true" in result.run.notes


def test_as_of_date_is_metadata_only_for_recent_snapshot_outcome(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    for ticker in ("AAA", "BBB", "CCC"):
        repository.save_trade_plan(_trade_plan(ticker))
        repository.save_price_bars(
            [PriceBar(ticker=ticker, date=date.today() + timedelta(days=1), high=15, low=10, close=14)]
        )

    result = ReplayRunService(repository).snapshot_from_recent_trade_plans(
        account_equity=10_000,
        cash_available=5_000,
        max_candidates=3,
        as_of_date=date(2000, 1, 1),
    )

    assert result.run.as_of_date == date(2000, 1, 1)
    assert result.outcome is not None
    assert result.outcome.entry_date != result.run.as_of_date


def test_replay_cli_reports_snapshot_only_and_save_basket_modes(tmp_path, capsys) -> None:
    db_path = tmp_path / "risk.sqlite3"
    repository = RiskRepository(db_path)
    for ticker in ("AAA", "BBB", "CCC"):
        repository.save_trade_plan(_trade_plan(ticker))
    common = [
        "--db", str(db_path), "--account-equity", "10000", "--cash-available", "5000", "--max-candidates", "3"
    ]

    main(["replay-snapshot-from-recent-trade-plans", *common])
    snapshot_only = json.loads(capsys.readouterr().out)
    main(["replay-snapshot-from-recent-trade-plans", *common, "--save-basket"])
    saved = json.loads(capsys.readouterr().out)
    main(["replay-runs", "--db", str(db_path)])
    runs = json.loads(capsys.readouterr().out)
    main(["replay-show", "--db", str(db_path), "--run-id", snapshot_only["run"]["run_id"]])
    shown = json.loads(capsys.readouterr().out)

    assert snapshot_only["saved_to_basket_plans"] is False
    assert saved["saved_to_basket_plans"] is True
    assert len(runs["runs"]) == 2
    assert shown["basket"]["basket_id"] == snapshot_only["basket"]["basket_id"]


def _trade_plan(ticker: str) -> TradePlan:
    return TradePlan(
        ticker=ticker,
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


def _empty_plan(basket_id: str) -> BasketPlan:
    return BasketPlan(
        basket_id=basket_id,
        basket_name="fixture",
        mode=BasketMode.PAPER_TRADING,
        policy=BasketPolicy(account_equity=10_000, cash_available=5_000),
        candidates=[],
        allocations=[],
        blocked=[],
        risk_summary=BasketRiskSummary(
            total_allocated_loss=0,
            max_allowed_loss=100,
            total_notional_value=0,
            max_allowed_notional=2500,
            candidate_count=0,
            sector_counts={},
            theme_counts={},
            blocked_reasons=[],
            warnings=[],
            risk_ok=True,
        ),
        decision=TradeDecision.NO_TRADE,
        beginner_summary="fixture",
        created_at=datetime(2026, 6, 13),
    )
