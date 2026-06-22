import json

import pytest

from stock_risk_mcp.historical_paper_trading_fixture import load_historical_paper_trading_fixture
from stock_risk_mcp.historical_paper_trading_guard import validate_historical_paper_trading_metadata_safety
from stock_risk_mcp.historical_paper_trading_models import (
    HistoricalPaperDecision,
    HistoricalPaperFill,
    HistoricalPaperLedger,
    HistoricalPaperPerformanceReport,
    HistoricalPaperPolicy,
    HistoricalPaperPosition,
    HistoricalPaperRiskLimit,
    HistoricalPaperTrade,
    HistoricalPaperTradingAuditRecord,
    HistoricalPaperTradingConfig,
    HistoricalPaperTradingGapCategory,
    HistoricalPaperTradingGapReport,
    HistoricalPaperTradingInput,
    HistoricalPaperTradingSafetyReport,
    HistoricalPaperOrderIntent,
)


def historical_paper_trading_fixture_payload():
    return {
        "schema_version": "5.10-historical-paper-trading-input",
        "paper_trading_input_id": "historical-paper-trading-input-1",
        "paper_trading_config": {
            "config_id": "historical-paper-trading-config-1",
            "strategy_track": "DOMESTIC_KR",
            "initial_cash": 1000000.0,
            "slippage_bps": 5.0,
            "fee_bps": 2.0,
        },
        "paper_policy": {
            "policy_id": "historical-paper-policy-1",
            "max_positions": 5,
            "max_exposure": 500000.0,
            "max_per_symbol_exposure": 150000.0,
            "max_daily_loss": 50000.0,
            "max_drawdown": 100000.0,
            "default_holding_period_sessions": 5,
            "stop_simulation_rule": "FIXED_PCT",
            "take_profit_simulation_rule": "FIXED_PCT",
        },
        "paper_decision": {
            "decision_id": "historical-paper-decision-1",
            "signal_candidate_ref_id": "HISTORICAL-SIGNAL-CANDIDATE-1",
            "paper_side": "PAPER_BUY",
            "decision_timestamp": "2026-06-18T15:30:00+09:00",
            "decision_reason": "Paper-only deterministic decision.",
        },
        "paper_order_intent": {
            "paper_order_intent_id": "historical-paper-order-intent-1",
            "signal_candidate_ref_id": "HISTORICAL-SIGNAL-CANDIDATE-1",
            "decision_id": "HISTORICAL-PAPER-DECISION-1",
            "paper_side": "PAPER_BUY",
            "symbol": "005930",
            "quantity": 10,
            "decision_timestamp": "2026-06-18T15:30:00+09:00",
            "intended_entry_session": "2026-06-19",
        },
        "paper_fill": {
            "paper_fill_id": "historical-paper-fill-1",
            "paper_order_intent_id": "HISTORICAL-PAPER-ORDER-INTENT-1",
            "symbol": "005930",
            "paper_side": "PAPER_BUY",
            "fill_price": 70000.0,
            "fill_quantity": 10,
            "fill_timestamp": "2026-06-19T09:05:00+09:00",
            "slippage_cost": 350.0,
            "fee_cost": 140.0,
        },
        "paper_ledger": {
            "paper_ledger_id": "historical-paper-ledger-1",
            "starting_cash": 1000000.0,
            "cash_balance": 999510.0,
            "reserved_cash": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "fees_paid": 140.0,
            "slippage_paid": 350.0,
        },
        "paper_position": {
            "paper_position_id": "historical-paper-position-1",
            "symbol": "005930",
            "open_quantity": 10,
            "average_entry_price": 70000.0,
            "market_value": 700000.0,
            "unrealized_pnl": 0.0,
        },
        "paper_trade": {
            "paper_trade_id": "historical-paper-trade-1",
            "symbol": "005930",
            "entry_fill_id": "HISTORICAL-PAPER-FILL-1",
            "entry_side": "PAPER_BUY",
            "entry_price": 70000.0,
            "entry_quantity": 10,
            "status": "OPEN",
        },
        "paper_risk_limit": {
            "paper_risk_limit_id": "historical-paper-risk-limit-1",
            "max_positions": 5,
            "max_exposure": 500000.0,
            "max_per_symbol_exposure": 150000.0,
            "max_daily_loss": 50000.0,
            "max_drawdown": 100000.0,
        },
        "paper_performance_report": {
            "performance_report_id": "historical-paper-performance-report-1",
            "total_return": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "turnover": 0.0,
            "exposure_time": 0.0,
            "fees": 140.0,
            "slippage_cost": 350.0,
            "number_of_trades": 1,
        },
        "safety_report": {
            "safety_report_id": "historical-paper-trading-safety-report-1",
            "paper_trading_input_id": "historical-paper-trading-input-1",
        },
        "gap_report": {
            "gap_report_id": "historical-paper-trading-gap-report-1",
            "paper_trading_input_id": "historical-paper-trading-input-1",
            "gap_status": "NO_GAPS",
            "gap_categories": [],
            "blocking_gap_count": 0,
            "report_only_gap_count": 0,
            "gaps": [],
        },
        "audit_records": [
            {
                "audit_record_id": "historical-paper-trading-audit-record-1",
                "paper_trading_input_id": "historical-paper-trading-input-1",
                "created_at": "2026-06-18T18:30:00+09:00",
                "operator_context": "TEST",
                "source_path": "fixtures/historical/historical_paper_trading_fixture.json",
            }
        ],
    }


def test_historical_paper_trading_models_accept_local_fixture_only_inputs(tmp_path):
    fixture_file = tmp_path / "historical_paper_trading_fixture.json"
    fixture_file.write_text(json.dumps(historical_paper_trading_fixture_payload()), encoding="utf-8")

    result = load_historical_paper_trading_fixture(fixture_file)

    assert isinstance(result, HistoricalPaperTradingInput)
    assert isinstance(result.paper_trading_config, HistoricalPaperTradingConfig)
    assert result.paper_trading_config.no_external_execution is True


def test_historical_paper_trading_models_require_safety_flags():
    payload = historical_paper_trading_fixture_payload()
    payload["paper_trading_config"]["no_broker_api"] = False

    with pytest.raises(ValueError, match="no_broker_api"):
        HistoricalPaperTradingInput.model_validate(payload)


def test_historical_paper_policy_construction():
    result = HistoricalPaperTradingInput.model_validate(historical_paper_trading_fixture_payload())
    assert isinstance(result.paper_policy, HistoricalPaperPolicy)


def test_historical_paper_decision_construction():
    result = HistoricalPaperTradingInput.model_validate(historical_paper_trading_fixture_payload())
    assert isinstance(result.paper_decision, HistoricalPaperDecision)


def test_historical_paper_order_intent_construction():
    result = HistoricalPaperTradingInput.model_validate(historical_paper_trading_fixture_payload())
    assert isinstance(result.paper_order_intent, HistoricalPaperOrderIntent)


def test_historical_paper_order_intent_is_paper_only_and_simulated_only():
    result = HistoricalPaperTradingInput.model_validate(historical_paper_trading_fixture_payload())
    assert result.paper_order_intent.paper_only is True
    assert result.paper_order_intent.simulated_only is True


def test_historical_paper_order_intent_does_not_expose_real_order_intent():
    result = HistoricalPaperTradingInput.model_validate(historical_paper_trading_fixture_payload())
    dumped = result.paper_order_intent.model_dump(mode="json")
    assert "order_intent_id" not in dumped
    assert "broker_order_intent_id" not in dumped


def test_historical_paper_fill_construction():
    result = HistoricalPaperTradingInput.model_validate(historical_paper_trading_fixture_payload())
    assert isinstance(result.paper_fill, HistoricalPaperFill)


def test_historical_paper_ledger_construction():
    result = HistoricalPaperTradingInput.model_validate(historical_paper_trading_fixture_payload())
    assert isinstance(result.paper_ledger, HistoricalPaperLedger)


def test_historical_paper_position_construction():
    result = HistoricalPaperTradingInput.model_validate(historical_paper_trading_fixture_payload())
    assert isinstance(result.paper_position, HistoricalPaperPosition)


def test_historical_paper_trade_construction():
    result = HistoricalPaperTradingInput.model_validate(historical_paper_trading_fixture_payload())
    assert isinstance(result.paper_trade, HistoricalPaperTrade)


def test_historical_paper_risk_limit_construction():
    result = HistoricalPaperTradingInput.model_validate(historical_paper_trading_fixture_payload())
    assert isinstance(result.paper_risk_limit, HistoricalPaperRiskLimit)


def test_historical_paper_performance_report_construction():
    result = HistoricalPaperTradingInput.model_validate(historical_paper_trading_fixture_payload())
    assert isinstance(result.paper_performance_report, HistoricalPaperPerformanceReport)


def test_historical_paper_safety_report_construction():
    result = HistoricalPaperTradingInput.model_validate(historical_paper_trading_fixture_payload())
    assert isinstance(result.safety_report, HistoricalPaperTradingSafetyReport)


def test_historical_paper_gap_report_construction():
    result = HistoricalPaperTradingInput.model_validate(historical_paper_trading_fixture_payload())
    assert isinstance(result.gap_report, HistoricalPaperTradingGapReport)


def test_historical_paper_audit_record_construction():
    result = HistoricalPaperTradingInput.model_validate(historical_paper_trading_fixture_payload())
    assert isinstance(result.audit_records[0], HistoricalPaperTradingAuditRecord)


def test_historical_paper_trading_fixture_loader_wraps_source_path_in_error(tmp_path):
    fixture_file = tmp_path / "historical_paper_trading_fixture.txt"
    fixture_file.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match=str(fixture_file)):
        load_historical_paper_trading_fixture(fixture_file)


@pytest.mark.parametrize(
    "paper_side",
    ["PAPER_BUY", "PAPER_SELL", "PAPER_HOLD", "PAPER_SKIP", "PAPER_CLOSE"],
)
def test_historical_paper_trading_accepts_paper_only_side_values(paper_side):
    payload = historical_paper_trading_fixture_payload()
    payload["paper_decision"]["paper_side"] = paper_side
    payload["paper_order_intent"]["paper_side"] = paper_side
    payload["paper_fill"]["paper_side"] = paper_side
    payload["paper_trade"]["entry_side"] = paper_side

    result = HistoricalPaperTradingInput.model_validate(payload)

    assert result.paper_decision.paper_side.value == paper_side


@pytest.mark.parametrize("side", ["BUY", "SELL", "HOLD", "ENTRY", "EXIT", "LONG", "SHORT", "ORDER"])
def test_historical_paper_trading_rejects_real_action_values(side):
    payload = historical_paper_trading_fixture_payload()
    payload["paper_decision"]["paper_side"] = side

    with pytest.raises(ValueError, match="paper side"):
        HistoricalPaperTradingInput.model_validate(payload)


@pytest.mark.parametrize(
    ("metadata", "match"),
    [
        ({"real_order_intent": "yes"}, "order"),
        ({"broker_account": "yes"}, "broker"),
        ({"kiwoom_order": "yes"}, "kiwoom"),
        ({"ls_order": "yes"}, "ls"),
        ({"network_provider": "tcp://local"}, "provider"),
        ({"live_trading": "yes"}, "live_trading"),
        ({"live_prod": "prod"}, "live_prod"),
        ({"cloud_llm": "gemini"}, "cloud_llm"),
        ({"local_llm_runtime": "ollama"}, "local_llm"),
        ({"api_token": "secret"}, "credential"),
        ({"artifact_path": "paper.parquet"}, "parquet"),
    ],
)
def test_historical_paper_trading_guard_rejects_unsafe_markers(metadata, match):
    with pytest.raises(ValueError, match=match):
        validate_historical_paper_trading_metadata_safety(metadata, context="historical paper trading")


def test_historical_paper_trading_gap_categories_exist():
    expected = {
        "PAPER_TRADING_PLAN_GENERATED",
        "PAPER_TRADING_LOCAL_ONLY",
        "PAPER_TRADING_OFFLINE_ONLY",
        "PAPER_TRADING_PAPER_ONLY",
        "PAPER_TRADING_SIMULATED_ONLY",
        "PAPER_TRADING_NON_EXECUTABLE",
        "PAPER_TRADING_MISSING_INPUT",
        "PAPER_TRADING_MISSING_SIGNAL_CANDIDATE_REF",
        "PAPER_TRADING_MISSING_PRICE_BAR",
        "PAPER_TRADING_MISSING_FILL_PRICE",
        "PAPER_TRADING_MISSING_LEDGER_STATE",
        "PAPER_TRADING_MISSING_RISK_LIMIT",
        "PAPER_TRADING_INVALID_INITIAL_CASH",
        "PAPER_TRADING_INVALID_POSITION_SIZE",
        "PAPER_TRADING_INVALID_EXPOSURE_LIMIT",
        "PAPER_TRADING_INVALID_SLIPPAGE",
        "PAPER_TRADING_INVALID_FEE",
        "PAPER_TRADING_UNSUPPORTED_PAPER_SIDE",
        "PAPER_TRADING_REAL_ACTION_NOT_ALLOWED",
        "PAPER_TRADING_REAL_ORDER_INTENT_NOT_ALLOWED",
        "PAPER_TRADING_BROKER_PATH_NOT_ALLOWED",
        "PAPER_TRADING_KIWOOM_API_NOT_ALLOWED",
        "PAPER_TRADING_LS_API_NOT_ALLOWED",
        "PAPER_TRADING_ACCOUNT_API_NOT_ALLOWED",
        "PAPER_TRADING_ORDER_API_NOT_ALLOWED",
        "PAPER_TRADING_NETWORK_NOT_ALLOWED",
        "PAPER_TRADING_PROVIDER_API_NOT_ALLOWED",
        "PAPER_TRADING_LIVE_TRADING_NOT_ALLOWED",
        "PAPER_TRADING_LIVE_PROD_NOT_ALLOWED",
        "PAPER_TRADING_CLOUD_LLM_NOT_ALLOWED",
        "PAPER_TRADING_LOCAL_LLM_RUNTIME_NOT_ALLOWED",
        "PAPER_TRADING_CREDENTIALS_NOT_ALLOWED",
        "PAPER_TRADING_PARQUET_NOT_ALLOWED",
    }

    assert expected.issubset({item.value for item in HistoricalPaperTradingGapCategory})
