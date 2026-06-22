import copy

from stock_risk_mcp.historical_paper_trading_engine import run_historical_paper_trading
from stock_risk_mcp.historical_paper_trading_models import HistoricalPaperTradingInput
from tests.test_historical_paper_trading_models import historical_paper_trading_fixture_payload


def _engine_payload():
    payload = historical_paper_trading_fixture_payload()
    payload["paper_trading_config"]["initial_cash"] = 1000000.0
    payload["paper_trading_config"]["slippage_bps"] = 5.0
    payload["paper_trading_config"]["fee_bps"] = 2.0
    payload["paper_decision"]["signal_candidate_ref_id"] = "HISTORICAL-SIGNAL-CANDIDATE-1"
    payload["paper_order_intent"]["signal_candidate_ref_id"] = "HISTORICAL-SIGNAL-CANDIDATE-1"
    payload["paper_order_intent"]["quantity"] = 2
    payload["paper_fill"]["fill_price"] = 100.0
    payload["paper_fill"]["fill_quantity"] = 2
    payload["paper_ledger"]["starting_cash"] = 1000000.0
    payload["paper_ledger"]["cash_balance"] = 1000000.0
    payload["paper_ledger"]["fees_paid"] = 0.0
    payload["paper_ledger"]["slippage_paid"] = 0.0
    payload["paper_position"]["open_quantity"] = 0
    payload["paper_position"]["average_entry_price"] = 0.0
    payload["paper_position"]["market_value"] = 0.0
    payload["paper_trade"]["entry_price"] = 0.0
    payload["paper_trade"]["entry_quantity"] = 1
    payload["paper_performance_report"]["number_of_trades"] = 0
    payload["paper_runtime_context"] = {
        "signal_candidate": {
            "candidate_id": "HISTORICAL-SIGNAL-CANDIDATE-1",
            "symbol": "005930",
            "score": 0.80,
            "confidence_bucket": "HIGH",
            "predicted_outcome_label": "OUTCOME_FAVORABLE",
            "risk_review_blocked": False,
            "promotion_blocked": True,
        },
        "price_bars": [
            {
                "session": "2026-06-19",
                "open": 100.0,
                "high": 110.0,
                "low": 98.0,
                "close": 108.0,
                "volume": 100000,
            }
        ],
        "current_mark_price": 108.0,
        "existing_position_count": 0,
        "existing_symbol_exposure": 0.0,
        "existing_total_exposure": 0.0,
        "daily_loss": 0.0,
        "drawdown": 0.0,
    }
    return payload


def build_input(payload=None):
    return HistoricalPaperTradingInput.model_validate(payload or _engine_payload())


def test_historical_paper_policy_evaluation_success_path():
    result = run_historical_paper_trading(build_input())

    assert result.paper_decision.paper_side.value == "PAPER_BUY"


def test_historical_paper_decision_generation_success_path():
    result = run_historical_paper_trading(build_input())

    assert result.paper_decision.decision_id == "HISTORICAL-PAPER-DECISION-1"


def test_historical_paper_order_intent_generation_success_path():
    result = run_historical_paper_trading(build_input())

    assert result.paper_order_intent.paper_side.value == "PAPER_BUY"
    assert result.paper_order_intent.quantity == 2


def test_historical_paper_order_intent_remains_paper_only_and_simulated_only():
    result = run_historical_paper_trading(build_input())

    assert result.paper_order_intent.paper_only is True
    assert result.paper_order_intent.simulated_only is True


def test_historical_paper_fill_next_bar_open_success_path():
    result = run_historical_paper_trading(build_input())

    assert result.paper_fill.fill_price == 100.0


def test_historical_paper_slippage_applied():
    result = run_historical_paper_trading(build_input())

    assert result.paper_fill.slippage_cost == 1.0


def test_historical_paper_fee_applied():
    result = run_historical_paper_trading(build_input())

    assert result.paper_fill.fee_cost == 0.4


def test_historical_paper_missing_price_bar_produces_gap():
    payload = _engine_payload()
    payload["paper_runtime_context"]["price_bars"] = []

    result = run_historical_paper_trading(build_input(payload))

    assert any(item["gap_category"] == "PAPER_TRADING_MISSING_PRICE_BAR" for item in result.gap_report.gaps)


def test_historical_paper_missing_fill_price_produces_gap():
    payload = _engine_payload()
    payload["paper_runtime_context"]["price_bars"][0]["open"] = None

    result = run_historical_paper_trading(build_input(payload))

    assert any(item["gap_category"] == "PAPER_TRADING_MISSING_FILL_PRICE" for item in result.gap_report.gaps)


def test_historical_paper_invalid_slippage_rejected():
    payload = _engine_payload()
    payload["paper_trading_config"]["slippage_bps"] = -1.0

    result = run_historical_paper_trading(build_input(payload))

    assert any(item["gap_category"] == "PAPER_TRADING_INVALID_SLIPPAGE" for item in result.gap_report.gaps)


def test_historical_paper_invalid_fee_rejected():
    payload = _engine_payload()
    payload["paper_trading_config"]["fee_bps"] = -1.0

    result = run_historical_paper_trading(build_input(payload))

    assert any(item["gap_category"] == "PAPER_TRADING_INVALID_FEE" for item in result.gap_report.gaps)


def test_historical_paper_insufficient_simulated_cash_blocks_fill():
    payload = _engine_payload()
    payload["paper_ledger"]["cash_balance"] = 100.0

    result = run_historical_paper_trading(build_input(payload))

    assert any(item["gap_category"] == "PAPER_TRADING_INVALID_POSITION_SIZE" for item in result.gap_report.gaps)


def test_historical_paper_max_positions_blocks_decision():
    payload = _engine_payload()
    payload["paper_policy"]["max_positions"] = 1
    payload["paper_runtime_context"]["existing_position_count"] = 1

    result = run_historical_paper_trading(build_input(payload))

    assert result.paper_decision.paper_side.value == "PAPER_SKIP"


def test_historical_paper_max_per_symbol_exposure_blocks_decision():
    payload = _engine_payload()
    payload["paper_runtime_context"]["existing_symbol_exposure"] = 200000.0

    result = run_historical_paper_trading(build_input(payload))

    assert any(item["gap_category"] == "PAPER_TRADING_INVALID_EXPOSURE_LIMIT" for item in result.gap_report.gaps)


def test_historical_paper_max_total_exposure_blocks_decision():
    payload = _engine_payload()
    payload["paper_runtime_context"]["existing_total_exposure"] = 600000.0

    result = run_historical_paper_trading(build_input(payload))

    assert any(item["gap_category"] == "PAPER_TRADING_INVALID_EXPOSURE_LIMIT" for item in result.gap_report.gaps)


def test_historical_paper_ledger_update_after_fill():
    result = run_historical_paper_trading(build_input())

    assert result.paper_ledger.cash_balance == 999798.6


def test_historical_paper_position_update_after_fill():
    result = run_historical_paper_trading(build_input())

    assert result.paper_position.open_quantity == 2
    assert result.paper_position.market_value == 216.0


def test_historical_paper_trade_record_generation():
    result = run_historical_paper_trading(build_input())

    assert result.paper_trade.entry_quantity == 2
    assert result.paper_trade.status == "OPEN"


def test_historical_paper_realized_pnl_calculation():
    payload = _engine_payload()
    payload["paper_decision"]["paper_side"] = "PAPER_CLOSE"
    payload["paper_order_intent"]["paper_side"] = "PAPER_CLOSE"
    payload["paper_fill"]["paper_side"] = "PAPER_CLOSE"
    payload["paper_trade"]["entry_price"] = 90.0
    payload["paper_trade"]["entry_quantity"] = 2
    payload["paper_position"]["open_quantity"] = 2
    payload["paper_position"]["average_entry_price"] = 90.0
    payload["paper_position"]["market_value"] = 180.0

    result = run_historical_paper_trading(build_input(payload))

    assert result.paper_ledger.realized_pnl > 0


def test_historical_paper_unrealized_pnl_calculation():
    result = run_historical_paper_trading(build_input())

    assert result.paper_ledger.unrealized_pnl == 16.0


def test_historical_paper_performance_report_generation():
    result = run_historical_paper_trading(build_input())

    assert result.paper_performance_report.number_of_trades == 1


def test_historical_paper_win_rate_calculation():
    payload = _engine_payload()
    payload["paper_decision"]["paper_side"] = "PAPER_CLOSE"
    payload["paper_order_intent"]["paper_side"] = "PAPER_CLOSE"
    payload["paper_fill"]["paper_side"] = "PAPER_CLOSE"
    payload["paper_trade"]["entry_price"] = 90.0
    payload["paper_trade"]["entry_quantity"] = 2
    payload["paper_position"]["open_quantity"] = 2
    payload["paper_position"]["average_entry_price"] = 90.0
    payload["paper_position"]["market_value"] = 180.0

    result = run_historical_paper_trading(build_input(payload))

    assert result.paper_performance_report.win_rate == 1.0


def test_historical_paper_profit_factor_calculation():
    payload = _engine_payload()
    payload["paper_decision"]["paper_side"] = "PAPER_CLOSE"
    payload["paper_order_intent"]["paper_side"] = "PAPER_CLOSE"
    payload["paper_fill"]["paper_side"] = "PAPER_CLOSE"
    payload["paper_trade"]["entry_price"] = 90.0
    payload["paper_trade"]["entry_quantity"] = 2
    payload["paper_position"]["open_quantity"] = 2
    payload["paper_position"]["average_entry_price"] = 90.0
    payload["paper_position"]["market_value"] = 180.0

    result = run_historical_paper_trading(build_input(payload))

    assert result.paper_performance_report.profit_factor >= 0.0


def test_historical_paper_turnover_calculation():
    result = run_historical_paper_trading(build_input())

    assert result.paper_performance_report.turnover > 0.0


def test_historical_paper_drawdown_calculation():
    payload = _engine_payload()
    payload["paper_runtime_context"]["drawdown"] = 1234.0

    result = run_historical_paper_trading(build_input(payload))

    assert result.paper_performance_report.max_drawdown == 1234.0


def test_historical_paper_safety_report_generation():
    result = run_historical_paper_trading(build_input())

    assert result.safety_report.no_broker_api is True


def test_historical_paper_gap_report_generation():
    result = run_historical_paper_trading(build_input())

    assert "PAPER_TRADING_PLAN_GENERATED" in result.gap_report.gap_categories


def test_historical_paper_audit_record_generation():
    result = run_historical_paper_trading(build_input())

    assert result.audit_records


def test_historical_paper_rejects_real_order_intent_marker():
    payload = _engine_payload()
    payload["paper_runtime_context"]["metadata"] = {"real_order_intent": "unsafe"}

    result = run_historical_paper_trading(build_input(payload))

    assert any(item["gap_category"] == "PAPER_TRADING_REAL_ORDER_INTENT_NOT_ALLOWED" for item in result.gap_report.gaps)


def test_historical_paper_rejects_broker_account_order_metadata():
    payload = _engine_payload()
    payload["paper_runtime_context"]["metadata"] = {"broker_account": "unsafe"}

    result = run_historical_paper_trading(build_input(payload))

    assert any(item["gap_category"] == "PAPER_TRADING_BROKER_PATH_NOT_ALLOWED" for item in result.gap_report.gaps)


def test_historical_paper_rejects_kiwoom_ls_metadata():
    payload = _engine_payload()
    payload["paper_runtime_context"]["metadata"] = {"kiwoom_order": "unsafe"}

    result = run_historical_paper_trading(build_input(payload))

    assert any(item["gap_category"] == "PAPER_TRADING_KIWOOM_API_NOT_ALLOWED" for item in result.gap_report.gaps)


def test_historical_paper_rejects_live_trading_marker():
    payload = _engine_payload()
    payload["paper_runtime_context"]["metadata"] = {"live_trading": "unsafe"}

    result = run_historical_paper_trading(build_input(payload))

    assert any(item["gap_category"] == "PAPER_TRADING_LIVE_TRADING_NOT_ALLOWED" for item in result.gap_report.gaps)


def test_historical_paper_rejects_network_provider_marker():
    payload = _engine_payload()
    payload["paper_runtime_context"]["metadata"] = {"network_provider": "tcp://local"}

    result = run_historical_paper_trading(build_input(payload))

    assert any(item["gap_category"] == "PAPER_TRADING_PROVIDER_API_NOT_ALLOWED" for item in result.gap_report.gaps)


def test_historical_paper_rejects_cloud_llm_local_llm_runtime_marker():
    payload = _engine_payload()
    payload["paper_runtime_context"]["metadata"] = {"cloud_llm": "gemini"}

    result = run_historical_paper_trading(build_input(payload))

    assert any(item["gap_category"] == "PAPER_TRADING_CLOUD_LLM_NOT_ALLOWED" for item in result.gap_report.gaps)


def test_historical_paper_rejects_credentials_marker():
    payload = _engine_payload()
    payload["paper_runtime_context"]["metadata"] = {"api_token": "secret"}

    result = run_historical_paper_trading(build_input(payload))

    assert any(item["gap_category"] == "PAPER_TRADING_CREDENTIALS_NOT_ALLOWED" for item in result.gap_report.gaps)


def test_historical_paper_rejects_parquet_marker():
    payload = _engine_payload()
    payload["paper_runtime_context"]["metadata"] = {"artifact_path": "paper.parquet"}

    result = run_historical_paper_trading(build_input(payload))

    assert any(item["gap_category"] == "PAPER_TRADING_PARQUET_NOT_ALLOWED" for item in result.gap_report.gaps)
