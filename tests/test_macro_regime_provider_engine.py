import pytest

from stock_risk_mcp.macro_regime_provider_client import (
    build_fred_request_preview,
    execute_fred_observations_request,
    parse_mocked_provider_payload,
)
from stock_risk_mcp.macro_regime_provider_models import (
    FredSeriesRequest,
    MacroRegimePipelineInput,
    MacroRegimeRuntimeContext,
    MockedProviderPayload,
)
from stock_risk_mcp.macro_regime_snapshot_engine import build_macro_regime_snapshot
from tests.test_macro_regime_provider_models import macro_regime_payload


def test_fred_request_preview_redacts_key_and_stays_preview_only():
    request = FredSeriesRequest(
        request_id="fred-vix",
        series_id="VIX",
        fred_series_code="VIXCLS",
        observation_start="2026-06-20",
        observation_end="2026-06-25",
        api_key_ref="FRED_KEY_REF",
    )
    preview = build_fred_request_preview(request)
    assert preview.provider.value == "FRED"
    assert preview.query_params["api_key"] == "FRED_KEY_REF"
    assert "API_KEY" in preview.redacted_fields
    assert preview.status.value == "MOCKED_ONLY"


def test_real_fred_execute_is_blocked_in_pytest_even_with_opt_in():
    request = FredSeriesRequest(
        request_id="fred-vix",
        series_id="VIX",
        fred_series_code="VIXCLS",
        api_key_ref="FRED_KEY_REF",
        allow_real_http=True,
        explicit_opt_in=True,
    )
    with pytest.raises(ValueError, match="must never run in pytest"):
        execute_fred_observations_request(
            request,
            api_key="not-used",
            runtime_context=MacroRegimeRuntimeContext.PYTEST,
        )


def test_mocked_provider_parsers_support_fred_and_manual_futures():
    fred_payload = MockedProviderPayload.model_validate(
        {
            "payload_id": "fred-vix",
            "provider": "FRED",
            "series_id": "VIX",
            "source_ref": "fixtures/macro/fred_vix.json",
            "payload": {"observations": [{"date": "2026-06-25", "value": "16.20"}]},
        }
    )
    fred_points, fred_events = parse_mocked_provider_payload(fred_payload)
    assert len(fred_points) == 1
    assert fred_points[0].series_id.value == "VIX"
    assert fred_events == []

    futures_payload = MockedProviderPayload.model_validate(
        {
            "payload_id": "manual-futures",
            "provider": "LOCAL_FIXTURE",
            "source_ref": "fixtures/macro/futures.json",
            "payload": {
                "records": [
                    {
                        "series_id": "NQ_CONTINUOUS",
                        "provider_symbol": "NQM2026",
                        "observed_at": "2026-06-26T09:00:00+09:00",
                        "available_at": "2026-06-26T09:02:00+09:00",
                        "value": 20150.0,
                        "pct_change_1d": 0.7,
                        "unit": "INDEX",
                    }
                ]
            },
        }
    )
    futures_points, futures_events = parse_mocked_provider_payload(futures_payload)
    assert len(futures_points) == 1
    assert futures_points[0].series_id.value == "NQ_CONTINUOUS"
    assert futures_events == []


def test_snapshot_engine_marks_nq_es_provider_gap_when_fixtures_missing():
    payload = macro_regime_payload(
        max_data_age_minutes=3000,
        manual_series_points=[],
        mocked_provider_payloads=[
            {
                "payload_id": "fred-vix",
                "provider": "FRED",
                "series_id": "VIX",
                "source_ref": "fixtures/macro/fred_vix.json",
                "payload": {"observations": [{"date": "2026-06-25", "value": "16.20"}]},
            },
            {
                "payload_id": "fred-us10y",
                "provider": "FRED",
                "series_id": "US10Y",
                "source_ref": "fixtures/macro/fred_us10y.json",
                "payload": {"observations": [{"date": "2026-06-25", "value": "4.10"}]},
            },
            {
                "payload_id": "fred-usdkrw",
                "provider": "FRED",
                "series_id": "USDKRW",
                "source_ref": "fixtures/macro/fred_usdkrw.json",
                "payload": {"observations": [{"date": "2026-06-25", "value": "1372.00"}]},
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
    assert snapshot.readiness.value == "DATA_GAP"
    assert any(entry.gap_category == "MISSING_NQ_CONTINUOUS" for entry in gap_report.gap_entries)
    assert any(entry.gap_category == "MISSING_ES_CONTINUOUS" for entry in gap_report.gap_entries)
    assert freshness_report.stale_series_count == 0
    assert capability_report.report_only is True
    assert conflict_report.report_only is True
    assert safety_report.no_order is True
