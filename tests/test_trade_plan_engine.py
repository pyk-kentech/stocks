from stock_risk_mcp.trade_plan_engine import build_trade_plan_report
from stock_risk_mcp.trade_plan_models import TradePlanFixture
from tests.test_trade_plan_fixture import candidate_payload


def candidate(ticker, **updates):
    value = dict(candidate_payload()["candidates"][0])
    value.update(ticker=ticker, **updates)
    return value


def fixture(candidates=None, **config_updates):
    value = candidate_payload(candidates)
    value["config"].update(**config_updates)
    return TradePlanFixture.model_validate(value)


def test_trade_plan_report_is_deterministic_and_advisory_only():
    report = build_trade_plan_report(fixture(), "fixture-checksum")
    plan = report.plans[0]
    assert build_trade_plan_report(fixture(), "fixture-checksum") == report
    assert plan.plan_status == "TRADE_PLAN_READY"
    assert plan.suggested_quantity == 250
    assert plan.max_loss_amount == 1000
    assert plan.risk_reward_ratio == 2
    assert report.metadata_json["advisory_only"] is True
    assert report.metadata_json["orders_created"] is False
    assert report.metadata_json["order_intents_created"] is False
    assert report.metadata_json["strategy_decisions_created"] is False
    assert report.metadata_json["gates_bypassed"] is False
    assert report.metadata_json["external_network_calls"] is False


def test_invalid_stop_and_unsupported_side_are_blocked():
    invalid_stop = build_trade_plan_report(fixture([
        candidate("AAA", stop_reference=100.0),
        candidate("BBB", side="SELL"),
    ]), "fixture-checksum")
    assert invalid_stop.plans[0].plan_status == "BLOCKED_INVALID_STOP"
    assert invalid_stop.plans[1].plan_status == "BLOCKED_UNSUPPORTED_SIDE"


def test_risk_reward_and_insufficient_evidence_block_plans():
    report = build_trade_plan_report(fixture([
        candidate("AAA", target_reference=104.0),
        candidate("BBB", target_reference=None),
    ]), "fixture-checksum")
    assert report.plans[0].plan_status == "BLOCKED_RISK_REWARD_TOO_LOW"
    assert report.plans[1].plan_status == "BLOCKED_INSUFFICIENT_EVIDENCE"


def test_quantity_floor_zero_returns_no_trade():
    report = build_trade_plan_report(fixture([
        candidate("AAA", entry_reference=100.0, stop_reference=50.0, target_reference=200.0),
    ], portfolio_equity=1000.0, risk_pct_per_trade=0.01), "fixture-checksum")
    assert report.plans[0].plan_status == "NO_TRADE"
    assert report.plans[0].suggested_quantity == 0


def test_basket_risk_cap_blocks_second_ready_plan():
    report = build_trade_plan_report(fixture([
        candidate("AAA"),
        candidate("BBB"),
    ], max_basket_risk_pct=0.015), "fixture-checksum")
    assert report.plans[0].plan_status == "TRADE_PLAN_READY"
    assert report.plans[1].plan_status == "BLOCKED_BASKET_RISK_CAP"
    assert report.summary_counts["ready_count"] == 1


def test_short_margin_and_leverage_are_not_supported():
    report = build_trade_plan_report(fixture([
        candidate("AAA", side="SHORT"),
    ]), "fixture-checksum")
    plan = report.plans[0]
    assert plan.plan_status == "BLOCKED_UNSUPPORTED_SIDE"
    assert "SHORT_SELLING_DISABLED" in plan.block_reasons
