import json

import pytest

from stock_risk_mcp.risk_adjusted_paper_eval_fixture import load_risk_adjusted_paper_eval_fixture
from stock_risk_mcp.risk_adjusted_paper_eval_guard import validate_risk_adjusted_paper_eval_metadata_safety
from stock_risk_mcp.risk_adjusted_paper_eval_models import (
    RiskAdjustedPaperEvalDecision,
    RiskAdjustedPaperEvalGapCategory,
    RiskAdjustedPaperEvalInput,
)


def risk_adjusted_paper_eval_payload(**overrides):
    payload = {
        "evaluation_id": "risk-adjusted-paper-eval-1",
        "allocation_policy_candidate_ref": "allocation-policy-1",
        "policy_promotion_decision": "TRAINED_OFFLINE",
        "point_in_time_dataset_ref": "pit-dataset-ref-1",
        "walk_forward_split_ref": "walk-forward-ref-1",
        "ensemble_candidate_ref": "ensemble-ref-1",
        "regime_feature_refs": ["REGIME-FEATURE-1", "REGIME-FEATURE-2"],
        "cnn_fear_greed_feature_ref": "cnn-fear-greed-ref-1",
        "market_data_fixture_ref": "market-data-fixture-ref-1",
        "fee_tax_slippage_assumptions_ref": "cost-ref-1",
        "initial_cash": 1000000.0,
        "evaluation_window_start": "2026-06-20T09:00:00+09:00",
        "evaluation_window_end": "2026-06-24T15:30:00+09:00",
        "benchmark_ref": "kospi-benchmark-ref-1",
        "symbol": "005930",
        "quantity": 10,
        "decision_timestamp": "2026-06-20T09:00:00+09:00",
        "simulated_fill_timestamp": "2026-06-20T09:05:00+09:00",
        "simulated_fill_price": 70000.0,
        "benchmark_return": 0.01,
        "end_price": 73500.0,
        "volatility": 0.08,
        "max_drawdown_limit": 0.15,
        "daily_loss_limit": 0.05,
        "max_gross_exposure": 1.0,
        "max_single_action_exposure": 0.8,
        "max_inverse_hedge_exposure": 0.2,
        "turnover_limit": 0.8,
        "inverse_hedge_exposure": 0.05,
        "turnover": 0.25,
        "fee_bps": 5.0,
        "tax_bps": 1.0,
        "slippage_bps": 4.0,
        "future_price_leakage_detected": False,
        "future_regime_fear_leakage_detected": False,
        "available_at_safe_market_data": True,
        "regime_bucket_name": "RISK_OFF",
        "fear_bucket_name": "FEAR",
        "policy_score": 0.71,
        "safety_report": {
            "safety_report_id": "risk-adjusted-paper-eval-safety-1",
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
                "audit_record_id": "risk-adjusted-paper-eval-audit-1",
                "created_at": "2026-06-24T16:00:00+09:00",
                "source_path": "fixtures/paper/risk_adjusted_paper_eval_fixture.json",
                "operator_context": "offline risk adjusted paper evaluation",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_default_paper_evaluation_layer_is_local_offline_report_only():
    loaded = RiskAdjustedPaperEvalInput.model_validate(risk_adjusted_paper_eval_payload())
    assert loaded.report_only is True
    assert loaded.offline_only is True
    assert loaded.no_broker_api is True


def test_guard_rejects_raw_secret_token_account_markers():
    with pytest.raises(ValueError):
        validate_risk_adjusted_paper_eval_metadata_safety({"authorization": "Bearer abc"}, context="paper eval")


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "risk_adjusted_paper_eval_fixture.json"
    fixture_path.write_text(json.dumps(risk_adjusted_paper_eval_payload()), encoding="utf-8")
    loaded = load_risk_adjusted_paper_eval_fixture(fixture_path)
    assert isinstance(loaded, RiskAdjustedPaperEvalInput)
    assert loaded.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_risk_adjusted_paper_eval_fixture("https://example.com/eval.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_risk_adjusted_paper_eval_fixture(tmp_path / "eval.parquet")


def test_decision_enum_surface():
    assert RiskAdjustedPaperEvalDecision.PAPER_PASS.value == "PAPER_PASS"
    assert RiskAdjustedPaperEvalDecision.GAP.value == "GAP"


def test_gap_category_surface():
    categories = {item.value for item in RiskAdjustedPaperEvalGapCategory}
    assert "MISSING_CNN_FEATURE" in categories
    assert "FUTURE_PRICE_LEAKAGE_DETECTED" in categories
