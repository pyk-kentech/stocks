from stock_risk_mcp.market_data_provider_registry_engine import build_market_data_provider_registry
from stock_risk_mcp.market_data_provider_registry_models import (
    MarketDataProviderRegistryInput,
    ProviderCandidateName,
    ProviderReadinessLevel,
)
from tests.test_market_data_provider_registry_models import market_data_provider_registry_payload


def _run(**overrides):
    payload = market_data_provider_registry_payload()
    payload.update(overrides)
    return build_market_data_provider_registry(MarketDataProviderRegistryInput.model_validate(payload))


def test_data_consuming_modules_expose_required_data_classes():
    result = _run()
    module_names = {item.module_name.value for item in result.module_data_requirement_report.requirements}
    assert "MARKET_REGIME_ENGINE" in module_names
    assert "EVENT_RISK_GATE" in module_names


def test_market_regime_requires_nq_es_vix_dxy_10y_usdkrw():
    result = _run()
    requirement = next(item for item in result.module_data_requirement_report.requirements if item.module_name.value == "MARKET_REGIME_ENGINE")
    required = {item.value for item in requirement.required_data_classes}
    assert {"FUTURES", "VOLATILITY_INDEX", "FX", "RATES_YIELDS"} <= required


def test_position_sizing_requires_price_atr_fx_cost_risk_evidence():
    result = _run()
    requirement = next(item for item in result.module_data_requirement_report.requirements if item.module_name.value == "POSITION_SIZING_ENGINE")
    required = {item.value for item in requirement.required_data_classes}
    assert "EQUITY_PRICE_OHLCV" in required
    assert "FX" in required
    assert "FEE_TAX_SLIPPAGE" in required
    assert "VOLUME_RELATIVE_VOLUME" in required


def test_event_risk_gate_requires_economic_and_earnings_calendar():
    result = _run()
    requirement = next(item for item in result.module_data_requirement_report.requirements if item.module_name.value == "EVENT_RISK_GATE")
    required = {item.value for item in requirement.required_data_classes}
    assert "ECONOMIC_CALENDAR" in required
    assert "EARNINGS_CALENDAR" in required


def test_breadth_engine_requires_market_internals():
    result = _run()
    requirement = next(item for item in result.module_data_requirement_report.requirements if item.module_name.value == "BREADTH_ENGINE")
    required = {item.value for item in requirement.required_data_classes}
    assert "BREADTH_MARKET_INTERNALS" in required


def test_local_fixture_provider_is_fixture_only():
    result = _run()
    provider = next(item for item in result.global_provider_registry_report.providers if item.provider_name == ProviderCandidateName.LOCAL_FIXTURE)
    assert provider.readiness_level == ProviderReadinessLevel.FIXTURE_ONLY


def test_manual_csv_is_backtest_ready_only_with_refs():
    result = _run()
    provider = next(item for item in result.global_provider_registry_report.providers if item.provider_name == ProviderCandidateName.MANUAL_CSV)
    assert provider.readiness_level == ProviderReadinessLevel.BACKTEST_READY


def test_yahoo_and_cme_delayed_are_sanity_check_only():
    result = _run()
    provider = next(item for item in result.global_provider_registry_report.providers if item.provider_name == ProviderCandidateName.YAHOO_DELAYED)
    assert provider.readiness_level == ProviderReadinessLevel.SANITY_CHECK_ONLY


def test_databento_is_preferred_futures_training_candidate_with_evidence_refs_only():
    result = _run()
    selection = result.provider_selection_report.preferred_provider_by_data_class
    assert selection["FUTURES"] == "DATABENTO"
    databento = next(item for item in result.global_provider_registry_report.providers if item.provider_name == ProviderCandidateName.DATABENTO)
    assert databento.api_key_evidence_ref is not None
    assert databento.subscription_evidence_ref is not None


def test_ibkr_is_live_read_only_candidate_without_connection():
    result = _run()
    ibkr = next(item for item in result.global_provider_registry_report.providers if item.provider_name == ProviderCandidateName.IBKR)
    assert ibkr.readiness_level == ProviderReadinessLevel.LIVE_READ_ONLY_READY


def test_missing_provider_for_critical_data_class_produces_gap():
    payload = market_data_provider_registry_payload()
    payload["provider_candidates"] = [item for item in payload["provider_candidates"] if item["provider_name"] != "DATABENTO"]
    result = build_market_data_provider_registry(MarketDataProviderRegistryInput.model_validate(payload))
    assert result.provider_selection_report.selection_decision.value == "GAP"


def test_normalized_data_contract_emits_provider_independent_fields():
    result = _run()
    contract = result.canonical_data_contract_report.contracts[0]
    assert contract.instrument_key
    assert contract.provider_symbol
    assert contract.source_provider.value
    assert contract.available_at is not None


def test_symbol_mapping_includes_core_keys_and_events():
    result = _run()
    keys = {item.canonical_key for item in result.symbol_mapping_report.mappings}
    assert {"NQ_FUTURES_MAIN", "ES_FUTURES_MAIN", "VIX_INDEX", "DXY_INDEX", "US10Y_YIELD", "USDKRW_SPOT", "FOMC_EVENT", "US_CPI_EVENT"} <= keys


def test_any_real_network_provider_attempt_is_blocked():
    payload = market_data_provider_registry_payload()
    payload["audit_records"][0]["operator_context"] = "network requests to ibkr"
    with __import__("pytest").raises(ValueError):
        build_market_data_provider_registry(MarketDataProviderRegistryInput.model_validate(payload))


def test_audit_report_is_redacted():
    result = _run()
    assert result.audit_records[0].redaction_applied is True
