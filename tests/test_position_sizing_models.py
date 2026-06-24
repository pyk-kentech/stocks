import json

import pytest

from stock_risk_mcp.position_sizing_fixture import load_position_sizing_fixture
from stock_risk_mcp.position_sizing_guard import validate_position_sizing_metadata_safety
from stock_risk_mcp.position_sizing_models import (
    PositionSizingDecision,
    PositionSizingInput,
    StopDistanceMode,
)


def position_sizing_payload(**overrides):
    payload = {
        "sizing_review_id": "position-sizing-1",
        "candidate_symbol": "QQQ",
        "market": "NASDAQ",
        "currency": "USD",
        "side": "LONG",
        "candidate_action_type": "ALLOCATE",
        "entry_price": 500.0,
        "current_price": 500.0,
        "atr_value": 10.0,
        "atr_period": 14,
        "atr_multiplier": 2.0,
        "fixed_stop_percent": 0.05,
        "explicit_stop_price": 475.0,
        "account_equity": 100000.0,
        "available_cash": 100000.0,
        "risk_per_trade_percent": 0.01,
        "max_risk_cash_per_trade": 1000.0,
        "daily_risk_budget": 2500.0,
        "remaining_daily_risk_budget": 2500.0,
        "current_gross_exposure": 0.10,
        "current_net_exposure": 0.10,
        "current_open_risk_percent": 0.005,
        "max_portfolio_exposure": 1.0,
        "max_gross_exposure": 1.0,
        "max_net_exposure": 1.0,
        "max_single_position_exposure": 0.25,
        "max_sector_exposure": 0.35,
        "max_inverse_hedge_exposure": 0.15,
        "sector_name": "TECH",
        "sector_exposure_after_trade_estimate": 0.20,
        "is_inverse_or_hedge": False,
        "instrument_eligibility_ref": "docs/eligibility/qqq.md",
        "liquidity_evidence_ref": "docs/liquidity/qqq.md",
        "leverage_flag": False,
        "daily_reset_warning": False,
        "short_holding_period_warning": False,
        "basis_risk_note": "LOW",
        "fee_bps": 5.0,
        "tax_bps": 0.0,
        "slippage_bps": 3.0,
        "fee_tax_slippage_assumption_ref": "docs/costs/us_equity_costs.md",
        "fx_conversion_rate": 1.0,
        "fx_conversion_ref": "docs/fx/usdusd.md",
        "market_regime_constraint_ref": "fixtures/regime/market_regime_report.json",
        "market_regime_label": "RISK_ON",
        "market_volatility_state": "NORMAL_VOL",
        "market_stress_state": "NORMAL",
        "market_regime_size_multiplier": 1.0,
        "provider_readiness_ref": "fixtures/provider/provider_selection_report.json",
        "provider_readiness_level": "PAPER_READY",
        "provider_policy_allows_research_only": False,
        "price_contract_ref": "fixtures/provider/qqq_price_contract.json",
        "atr_contract_ref": "fixtures/provider/qqq_atr_contract.json",
        "fx_contract_ref": "fixtures/provider/usd_contract.json",
        "cost_contract_ref": "fixtures/provider/us_costs_contract.json",
        "paper_evaluation_ref": "fixtures/paper/risk_adjusted_eval.json",
        "available_at": "2026-06-24T09:05:00+09:00",
        "observed_at": "2026-06-24T09:00:00+09:00",
        "decision_anchor_at": "2026-06-24T09:05:00+09:00",
        "source_refs": [
            "fixtures/provider/qqq_price_contract.json",
            "fixtures/provider/provider_selection_report.json",
        ],
        "stop_mode": "FIXED_PERCENT",
        "requested_allocation_percent": 0.20,
        "requested_quantity": 100,
        "round_lot_size": 1,
        "confidence_multiplier": 1.0,
        "volatility_size_multiplier": 1.0,
        "learned_size_multiplier": 1.0,
        "max_daily_loss_cap": 0.03,
        "max_open_risk_cap": 0.05,
        "max_order_count_per_day": 5,
        "cool_down_policy": "NONE",
        "fail_closed": True,
        "report_only_preview_allowed": True,
        "safety_report": {
            "safety_report_id": "position-sizing-safety-1",
            "blocked_capabilities": [
                "LIVE_TRADING_BLOCKED",
                "REAL_ORDER_BLOCKED",
                "ACCOUNT_MUTATION_BLOCKED",
                "BROKER_API_BLOCKED",
                "KIWOOM_API_BLOCKED",
                "WEBSOCKET_BLOCKED",
                "NETWORK_BLOCKED",
                "AUTONOMOUS_TRADING_BLOCKED",
            ],
            "findings": [],
        },
        "audit_records": [
            {
                "audit_record_id": "position-sizing-audit-1",
                "created_at": "2026-06-24T18:00:00+09:00",
                "source_path": "fixtures/position_sizing/position_sizing_fixture.json",
                "operator_context": "offline position sizing review",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_default_position_sizing_is_local_offline_report_only():
    loaded = PositionSizingInput.model_validate(position_sizing_payload())
    assert loaded.report_only is True
    assert loaded.offline_only is True
    assert loaded.no_broker_api is True
    assert loaded.no_order is True


def test_guard_rejects_secret_token_account_and_broker_markers():
    with pytest.raises(ValueError):
        validate_position_sizing_metadata_safety({"authorization": "Bearer abc"}, context="position sizing")
    with pytest.raises(ValueError):
        validate_position_sizing_metadata_safety({"account_id": "123-45"}, context="position sizing")


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "position_sizing_fixture.json"
    fixture_path.write_text(json.dumps(position_sizing_payload()), encoding="utf-8")
    loaded = load_position_sizing_fixture(fixture_path)
    assert isinstance(loaded, PositionSizingInput)
    assert loaded.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_position_sizing_fixture("https://example.com/position_sizing.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_position_sizing_fixture(tmp_path / "position_sizing.parquet")


def test_decision_enum_surface():
    assert PositionSizingDecision.SIZE_READY.value == "SIZE_READY"
    assert PositionSizingDecision.RISK_BUDGET_LIMITED.value == "RISK_BUDGET_LIMITED"
    assert PositionSizingDecision.DATA_GAP.value == "DATA_GAP"


def test_stop_mode_surface():
    assert StopDistanceMode.FIXED_PERCENT.value == "FIXED_PERCENT"
    assert StopDistanceMode.ATR_MULTIPLE.value == "ATR_MULTIPLE"
