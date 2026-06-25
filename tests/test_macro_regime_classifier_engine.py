from stock_risk_mcp.macro_regime_classifier_engine import build_macro_regime_classification
from stock_risk_mcp.macro_regime_integration_engine import build_macro_regime_pipeline_result
from stock_risk_mcp.macro_regime_provider_models import MacroRegimePipelineInput
from stock_risk_mcp.macro_regime_snapshot_engine import build_macro_regime_snapshot
from tests.test_macro_regime_provider_models import macro_regime_payload


def test_classifier_builds_risk_on_when_cross_asset_inputs_are_constructive():
    payload = macro_regime_payload(
        manual_series_points=[
            {
                "series_id": "NQ_CONTINUOUS",
                "asset_class": "FUTURES",
                "provider": "LOCAL_FIXTURE",
                "provider_symbol": "NQM2026",
                "observed_at": "2026-06-26T09:00:00+09:00",
                "available_at": "2026-06-26T09:02:00+09:00",
                "value": 20150.0,
                "pct_change_1d": 0.7,
                "unit": "INDEX",
                "source_ref": "fixtures/macro/nq.json",
            },
            {
                "series_id": "ES_CONTINUOUS",
                "asset_class": "FUTURES",
                "provider": "LOCAL_FIXTURE",
                "provider_symbol": "ESM2026",
                "observed_at": "2026-06-26T09:00:00+09:00",
                "available_at": "2026-06-26T09:02:00+09:00",
                "value": 5525.0,
                "pct_change_1d": 0.5,
                "unit": "INDEX",
                "source_ref": "fixtures/macro/es.json",
            },
        ],
        mocked_provider_payloads=[
            {
                "payload_id": "fred-vix",
                "provider": "FRED",
                "series_id": "VIX",
                "source_ref": "fixtures/macro/fred_vix.json",
                "payload": {"observations": [{"date": "2026-06-25", "value": "15.20"}]},
            },
            {
                "payload_id": "fred-us10y",
                "provider": "FRED",
                "series_id": "US10Y",
                "source_ref": "fixtures/macro/fred_us10y.json",
                "payload": {"observations": [{"date": "2026-06-25", "value": "3.90"}]},
            },
            {
                "payload_id": "fred-usdkrw",
                "provider": "FRED",
                "series_id": "USDKRW",
                "source_ref": "fixtures/macro/fred_usdkrw.json",
                "payload": {"observations": [{"date": "2026-06-25", "value": "1360.00"}]},
            },
            {
                "payload_id": "fred-dollar",
                "provider": "FRED",
                "series_id": "DOLLAR_STRENGTH",
                "source_ref": "fixtures/macro/fred_dollar.json",
                "payload": {"observations": [{"date": "2026-06-25", "value": "121.50"}]},
            },
        ],
    )
    snapshot, capability_report, freshness_report, conflict_report, gap_report, safety_report, event_window_report = build_macro_regime_snapshot(
        MacroRegimePipelineInput.model_validate(payload)
    )
    classification = build_macro_regime_classification(snapshot, event_window_report)
    result = build_macro_regime_pipeline_result(
        snapshot,
        classification,
        capability_report,
        freshness_report,
        conflict_report,
        event_window_report,
        gap_report,
        safety_report,
    )
    assert result.classification.label.value == "MACRO_RISK_ON"
    assert result.v7_integration_report.market_regime_context == "RISK_ON_COMPATIBLE"
    assert result.v8_integration_report.macro_bias == "CONSTRUCTIVE_MACRO_OVERLAY"


def test_classifier_degrades_to_data_gap_when_critical_inputs_missing():
    snapshot, capability_report, freshness_report, conflict_report, gap_report, safety_report, event_window_report = build_macro_regime_snapshot(
        MacroRegimePipelineInput.model_validate(macro_regime_payload(manual_series_points=[], mocked_provider_payloads=[]))
    )
    classification = build_macro_regime_classification(snapshot, event_window_report)
    assert classification.label.value == "MACRO_DATA_GAP"
    assert "MISSING_NQ_CONTINUOUS" in classification.blocking_gap_categories
