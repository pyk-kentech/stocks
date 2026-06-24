from stock_risk_mcp.market_regime_engine import build_market_regime
from stock_risk_mcp.market_regime_models import (
    MarketDirection,
    MarketRegimeDecision,
    MarketRiskAppetite,
    MarketStressState,
    MarketVolatilityState,
    MarketRegimeInput,
)
from tests.test_market_regime_models import market_regime_payload


def _run(**overrides):
    payload = market_regime_payload()
    payload.update(overrides)
    return build_market_regime(MarketRegimeInput.model_validate(payload))


def test_risk_on_fixture_classifies_bull_and_low_or_normal_vol():
    result = _run()
    assert result.summary_report.risk_appetite == MarketRiskAppetite.RISK_ON
    assert result.summary_report.market_direction == MarketDirection.BULL
    assert result.summary_report.volatility_state in {MarketVolatilityState.LOW_VOL, MarketVolatilityState.NORMAL_VOL}


def test_risk_off_fixture_classifies_bear_and_high_or_expanding_vol():
    snapshot = market_regime_payload()["snapshot"]
    snapshot["nq"]["pct_change_1d"] = -1.4
    snapshot["es"]["pct_change_1d"] = -1.2
    snapshot["vix"]["last_value"] = 31.0
    snapshot["vix"]["pct_change_1d"] = 14.0
    snapshot["dxy"]["pct_change_1d"] = 0.9
    snapshot["usdkrw"]["pct_change_1d"] = 1.5
    result = _run(snapshot=snapshot)
    assert result.summary_report.risk_appetite == MarketRiskAppetite.RISK_OFF
    assert result.summary_report.market_direction == MarketDirection.BEAR
    assert result.summary_report.volatility_state in {MarketVolatilityState.HIGH_VOL, MarketVolatilityState.VOL_EXPANSION}


def test_sideways_fixture_classifies_sideways():
    snapshot = market_regime_payload()["snapshot"]
    snapshot["nq"]["pct_change_1d"] = 0.03
    snapshot["es"]["pct_change_1d"] = -0.02
    snapshot["vix"]["last_value"] = 17.0
    snapshot["vix"]["pct_change_1d"] = 1.0
    result = _run(snapshot=snapshot)
    assert result.summary_report.market_direction == MarketDirection.SIDEWAYS


def test_high_vix_fixture_classifies_high_or_expanding_vol():
    snapshot = market_regime_payload()["snapshot"]
    snapshot["vix"]["last_value"] = 29.5
    snapshot["vix"]["pct_change_1d"] = 18.0
    result = _run(snapshot=snapshot)
    assert result.summary_report.volatility_state in {MarketVolatilityState.HIGH_VOL, MarketVolatilityState.VOL_EXPANSION}


def test_dxy_and_usdkrw_stress_are_represented():
    snapshot = market_regime_payload()["snapshot"]
    snapshot["dxy"]["pct_change_1d"] = 1.1
    snapshot["usdkrw"]["pct_change_1d"] = 1.7
    result = _run(snapshot=snapshot)
    assert result.summary_report.stress_state in {MarketStressState.DOLLAR_STRESS, MarketStressState.FX_STRESS, MarketStressState.CROSS_ASSET_STRESS}


def test_us10y_stress_is_represented():
    snapshot = market_regime_payload()["snapshot"]
    snapshot["us10y"]["pct_change_1d"] = 1.4
    result = _run(snapshot=snapshot)
    assert result.summary_report.stress_state in {MarketStressState.RATE_STRESS, MarketStressState.CROSS_ASSET_STRESS}


def test_nq_es_divergence_lowers_confidence_or_creates_conflict():
    snapshot = market_regime_payload()["snapshot"]
    snapshot["nq"]["pct_change_1d"] = 1.2
    snapshot["es"]["pct_change_1d"] = -1.1
    result = _run(snapshot=snapshot)
    assert result.cross_asset_conflict_report.conflict_count >= 1
    assert result.summary_report.confidence_bucket in {"LOW", "MEDIUM"}


def test_missing_available_at_causes_gap_or_blocked():
    snapshot = market_regime_payload()["snapshot"]
    snapshot["available_at"] = None
    result = _run(snapshot=snapshot)
    assert result.summary_report.decision in {MarketRegimeDecision.GAP, MarketRegimeDecision.BLOCKED}


def test_future_feature_leakage_blocks():
    snapshot = market_regime_payload()["snapshot"]
    snapshot["available_at"] = "2026-06-24T09:15:00+09:00"
    result = _run(snapshot=snapshot)
    assert result.summary_report.decision == MarketRegimeDecision.BLOCKED


def test_stale_critical_data_causes_gap():
    snapshot = market_regime_payload()["snapshot"]
    snapshot["available_at"] = "2026-06-24T06:00:00+09:00"
    result = _run(snapshot=snapshot)
    assert result.summary_report.decision == MarketRegimeDecision.GAP


def test_missing_optional_cnn_does_not_automatically_block():
    snapshot = market_regime_payload()["snapshot"]
    snapshot["cnn_fear_greed_feature_ref"] = None
    result = _run(snapshot=snapshot)
    assert result.summary_report.decision != MarketRegimeDecision.BLOCKED
    assert result.training_feature_integration_report.cnn_fear_greed_feature_present is False


def test_training_feature_report_emits_v75_v76_compatible_fields():
    result = _run()
    report = result.training_feature_integration_report
    assert report.regime_feature_snapshot_id
    assert report.risk_state
    assert report.available_at_present is True
    assert report.training_feature_ready is True


def test_downstream_constraints_remain_report_only():
    result = _run()
    assert result.downstream_constraint_report.report_only is True
    assert all("BUY" not in item for item in result.downstream_constraint_report.constraints)


def test_audit_report_is_redacted():
    result = _run()
    assert result.audit_records[0].redaction_applied is True
