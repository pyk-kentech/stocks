from stock_risk_mcp.paper_eval_engine import build_paper_eval_report
from stock_risk_mcp.paper_eval_models import PaperEvalFixture
from tests.test_paper_eval_fixture import fixture_payload


def payload(**updates):
    value = fixture_payload()
    for key, item in updates.items():
        value[key] = item
    return value


def first_input(**updates):
    value = dict(fixture_payload()["inputs"][0])
    value.update(**updates)
    return value


def first_bar(**updates):
    value = dict(fixture_payload()["price_paths"][0]["bars"][0])
    value.update(**updates)
    return value


def second_bar(**updates):
    value = dict(fixture_payload()["price_paths"][0]["bars"][1])
    value.update(**updates)
    return value


def fixture(value=None):
    return PaperEvalFixture.model_validate(value or fixture_payload())


def test_report_is_deterministic_and_target_exit_updates_metrics():
    report = build_paper_eval_report(fixture(), "fixture-checksum")
    trade = report.paper_trades[0]
    assert build_paper_eval_report(fixture(), "fixture-checksum") == report
    assert trade.exit_reason == "TARGET_HIT"
    assert trade.net_pnl == 80.0
    assert report.metrics.trade_count == 1
    assert report.metrics.target_hit_count == 1
    assert report.metadata_json["paper_only"] is True
    assert report.metadata_json["orders_submitted"] is False


def test_stop_hit_and_same_bar_stop_first_are_conservative():
    stop_report = build_paper_eval_report(
        fixture(payload(price_paths=[{
            "ticker": "ABC",
            "bars": [first_bar(), second_bar(low=95.0, high=101.0, close=96.0)],
        }])),
        "fixture-checksum",
    )
    same_bar_report = build_paper_eval_report(
        fixture(payload(price_paths=[{
            "ticker": "ABC",
            "bars": [first_bar(), second_bar(low=95.0, high=109.0, close=100.0)],
        }])),
        "fixture-checksum",
    )
    assert stop_report.paper_trades[0].exit_reason == "STOP_HIT"
    assert same_bar_report.paper_trades[0].exit_reason == "STOP_HIT"


def test_forced_end_of_fixture_close_and_missing_data_are_reported():
    forced_report = build_paper_eval_report(
        fixture(payload(price_paths=[{
            "ticker": "ABC",
            "bars": [first_bar(), second_bar(high=107.0, low=100.0, close=107.0)],
        }])),
        "fixture-checksum",
    )
    missing_report = build_paper_eval_report(
        fixture(payload(price_paths=[{
            "ticker": "ZZZ",
            "bars": [first_bar()],
        }])),
        "fixture-checksum",
    )
    assert forced_report.paper_trades[0].exit_reason == "FORCED_END_OF_FIXTURE"
    assert missing_report.metrics.missing_data_count == 1


def test_cash_checks_and_invalid_plan_inputs_block_candidates():
    blocked_cash = build_paper_eval_report(
        fixture(payload(config={
            "initial_cash": 100.0,
            "allow_limit_entry_only": True,
            "fee_per_trade": 0.0,
            "slippage_per_share": 0.0,
            "same_bar_exit_policy": "STOP_FIRST",
            "max_open_positions": 10,
        })),
        "fixture-checksum",
    )
    blocked_stop = build_paper_eval_report(
        fixture(payload(inputs=[first_input(stop_reference=100.0)])),
        "fixture-checksum",
    )
    assert blocked_cash.metrics.blocked_plan_count == 1
    assert blocked_stop.metrics.blocked_plan_count == 1


def test_fee_slippage_equity_curve_and_expectancy_are_computed():
    report = build_paper_eval_report(
        fixture(payload(config={
            "initial_cash": 100000.0,
            "allow_limit_entry_only": True,
            "fee_per_trade": 1.0,
            "slippage_per_share": 0.5,
            "same_bar_exit_policy": "STOP_FIRST",
            "max_open_positions": 10,
        })),
        "fixture-checksum",
    )
    trade = report.paper_trades[0]
    assert trade.gross_pnl == 80.0
    assert trade.net_pnl == 68.0
    assert len(report.equity_curve) >= 2
    assert report.metrics.expectancy_amount == 68.0
