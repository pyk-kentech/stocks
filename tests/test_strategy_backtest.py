from stock_risk_mcp.strategy_backtest import (
    StrategyBacktestReason,
    StrategyBacktestTradeStatus,
    run_strategy_backtest,
)
from stock_risk_mcp.strategy_backtest_fixture import StrategyBacktestFixture
from tests.test_strategy_backtest_fixture import payload


def fixture(value=None):
    return StrategyBacktestFixture.model_validate(value or payload())


def test_strict_after_fill_and_forced_exit_are_deterministic() -> None:
    first = run_strategy_backtest(fixture())
    second = run_strategy_backtest(fixture())
    trade = first.trades[0]

    assert trade.entry_price == 100
    assert trade.exit_price == 110
    assert trade.exit_reason == StrategyBacktestReason.FORCED_END_OF_FIXTURE
    assert first.metric.total_return_pct == second.metric.total_return_pct == 1.0
    assert first.metric.trade_count == 1
    assert first.metric.stop_loss_hit_count == 0


def test_sell_closes_full_position_and_sell_without_position_is_blocked() -> None:
    value = payload()
    value["snapshots"].append({
        "snapshot": {
            "snapshot_id": "s2", "ticker": "ABC", "region": "US",
            "observed_at": "2026-01-01T09:07:00+00:00",
            "features": {"signal_score": -0.8, "risk_score": 0.2, "hard_block": False},
        },
        "features_available_at": "2026-01-01T09:07:00+00:00",
    })
    value["candidate_events"].append({
        "candidate": {"candidate_id": "c2", "snapshot_id": "s2", "side": "SELL", "order_type": "LIMIT", "rationale": "exit"},
        "decision_timestamp": "2026-01-01T09:07:00+00:00",
    })
    value["price_paths"][0]["points"].append({"timestamp": "2026-01-01T09:08:00+00:00", "price": 120})
    result = run_strategy_backtest(fixture(value))
    assert result.trades[0].exit_price == 120
    assert result.trades[0].quantity == 1

    value["candidate_events"] = [value["candidate_events"][1]]
    no_position = run_strategy_backtest(fixture(value))
    assert no_position.trades[0].status == StrategyBacktestTradeStatus.BLOCKED
    assert no_position.trades[0].reason == StrategyBacktestReason.BLOCKED_NO_POSITION


def test_repeated_buy_insufficient_cash_missing_price_and_market_are_audited() -> None:
    repeated = payload()
    repeated["snapshots"].append({
        "snapshot": {
            "snapshot_id": "s2", "ticker": "ABC", "region": "US",
            "observed_at": "2026-01-01T09:06:30+00:00",
            "features": {"signal_score": 0.9, "risk_score": 0.2, "hard_block": False},
        }, "features_available_at": "2026-01-01T09:06:30+00:00",
    })
    repeated["candidate_events"].append({
        "candidate": {"candidate_id": "c2", "snapshot_id": "s2", "side": "BUY", "order_type": "LIMIT", "rationale": "again"},
        "decision_timestamp": "2026-01-01T09:06:30+00:00",
    })
    repeated["price_paths"][0]["points"] = repeated["price_paths"][0]["points"][:2]
    assert run_strategy_backtest(fixture(repeated)).trades[1].reason == StrategyBacktestReason.BLOCKED_ALREADY_POSITIONED

    insufficient = payload()
    insufficient["backtest_config"]["initial_cash"] = 50
    assert run_strategy_backtest(fixture(insufficient)).trades[0].reason == StrategyBacktestReason.BLOCKED_INSUFFICIENT_CASH

    missing = payload()
    missing["price_paths"] = []
    assert run_strategy_backtest(fixture(missing)).trades[0].status == StrategyBacktestTradeStatus.NEEDS_MORE_DATA

    market = payload()
    market["candidate_events"][0]["candidate"]["order_type"] = "MARKET"
    assert run_strategy_backtest(fixture(market)).metric.blocked_decision_count == 1

    no_position_no_future = payload()
    no_position_no_future["snapshots"][0]["snapshot"]["features"]["signal_score"] = -0.8
    no_position_no_future["candidate_events"][0]["candidate"]["side"] = "SELL"
    no_position_no_future["price_paths"] = []
    result = run_strategy_backtest(fixture(no_position_no_future))
    assert result.trades[0].reason == StrategyBacktestReason.BLOCKED_NO_POSITION


def test_portfolio_equity_curve_calculates_drawdown_and_exposure() -> None:
    value = payload()
    value["price_paths"][0]["points"] = [
        {"timestamp": "2026-01-01T09:06:00+00:00", "price": 100},
        {"timestamp": "2026-01-01T09:07:00+00:00", "price": 80},
        {"timestamp": "2026-01-01T09:08:00+00:00", "price": 110},
    ]
    result = run_strategy_backtest(fixture(value))
    assert result.metric.max_drawdown_pct == -2.0
    assert result.metric.exposure_time_pct == 100.0


def test_watch_is_audited_without_counting_as_blocked_and_candidate_quantity_is_ignored() -> None:
    watch = payload()
    watch["snapshots"][0]["snapshot"]["features"]["signal_score"] = 0.1
    watch_result = run_strategy_backtest(fixture(watch))
    assert watch_result.metric.blocked_decision_count == 0
    assert watch_result.trades[0].status == StrategyBacktestTradeStatus.SKIPPED

    quantity = payload()
    quantity["candidate_events"][0]["candidate"]["quantity"] = 99
    quantity_result = run_strategy_backtest(fixture(quantity))
    assert quantity_result.trades[0].quantity == 1


def test_equity_curve_preserves_simulator_order_for_same_fill_timestamp() -> None:
    value = payload()
    value["candidate_events"][0]["decision_timestamp"] = "2026-01-01T09:01:00+00:00"
    value["snapshots"].extend([
        {
            "snapshot": {
                "snapshot_id": "s2", "ticker": "ABC", "region": "US",
                "observed_at": "2026-01-01T09:04:00+00:00",
                "features": {"signal_score": -0.8, "risk_score": 0.2, "hard_block": False},
            }, "features_available_at": "2026-01-01T09:04:00+00:00",
        },
        {
            "snapshot": {
                "snapshot_id": "s3", "ticker": "ABC", "region": "US",
                "observed_at": "2026-01-01T09:06:00+00:00",
                "features": {"signal_score": 0.8, "risk_score": 0.2, "hard_block": False},
            }, "features_available_at": "2026-01-01T09:06:00+00:00",
        },
    ])
    value["candidate_events"].extend([
        {
            "candidate": {"candidate_id": "c2", "snapshot_id": "s2", "side": "SELL", "order_type": "LIMIT", "rationale": "close"},
            "decision_timestamp": "2026-01-01T09:04:00+00:00",
        },
        {
            "candidate": {"candidate_id": "c3", "snapshot_id": "s3", "side": "BUY", "order_type": "LIMIT", "rationale": "reopen"},
            "decision_timestamp": "2026-01-01T09:06:00+00:00",
        },
    ])
    value["price_paths"][0]["points"] = [
        {"timestamp": "2026-01-01T09:02:00+00:00", "price": 100},
        {"timestamp": "2026-01-01T09:07:00+00:00", "price": 105},
        {"timestamp": "2026-01-01T09:08:00+00:00", "price": 110},
    ]
    result = run_strategy_backtest(fixture(value))
    assert result.metric.exposure_time_pct == 100
