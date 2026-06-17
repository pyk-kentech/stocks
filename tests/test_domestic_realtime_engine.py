from stock_risk_mcp.domestic_realtime_engine import (
    build_domestic_realtime_plan_report,
    build_domestic_realtime_quality_report,
    normalize_domestic_realtime_events,
)
from stock_risk_mcp.domestic_realtime_models import RealtimeQualityStatus
from stock_risk_mcp.domestic_realtime_fixture import load_domestic_realtime_fixture
from tests.test_domestic_realtime_fixture import (
    domestic_realtime_fixture_payload,
    event_payload,
    subscription_limit_payload,
    subscription_plan_payload,
    write,
)


def test_domestic_realtime_engine_reports_subscription_limit_exceeded(tmp_path):
    payload = domestic_realtime_fixture_payload(
        subscription_limit=subscription_limit_payload(max_symbols=1),
        subscription_plan=subscription_plan_payload(symbols=["005930", "000660"]),
    )
    fixture = load_domestic_realtime_fixture(write(tmp_path, "domestic_realtime_fixture.json", payload))
    report = build_domestic_realtime_plan_report(fixture)
    assert report.limit_exceeded is True
    assert report.fallback_applied == "REPORT_ONLY_IF_OVER_CAPACITY"


def test_domestic_realtime_engine_normalizes_trade_event(tmp_path):
    fixture = load_domestic_realtime_fixture(write(tmp_path, "domestic_realtime_fixture.json", domestic_realtime_fixture_payload(events=[event_payload(event_type="TRADE")])))
    normalized = normalize_domestic_realtime_events(fixture)
    assert normalized[0]["event_type"] == "TRADE"
    assert normalized[0]["symbol"] == "005930"


def test_domestic_realtime_engine_normalizes_quote_and_orderbook_events(tmp_path):
    fixture = load_domestic_realtime_fixture(
        write(
            tmp_path,
            "domestic_realtime_fixture.json",
            domestic_realtime_fixture_payload(
                events=[
                    event_payload(event_type="QUOTE"),
                    event_payload(event_type="ORDERBOOK"),
                ]
            ),
        )
    )
    normalized = normalize_domestic_realtime_events(fixture)
    assert {item["event_type"] for item in normalized} == {"QUOTE", "ORDERBOOK"}


def test_domestic_realtime_engine_builds_volume_spike_event(tmp_path):
    fixture = load_domestic_realtime_fixture(
        write(
            tmp_path,
            "domestic_realtime_fixture.json",
            domestic_realtime_fixture_payload(
                events=[event_payload(event_type="TRADE", extra={"volume": 1000.0, "baseline_volume": 100.0})]
            ),
        )
    )
    normalized = normalize_domestic_realtime_events(fixture)
    assert normalized[0]["volume_spike_ratio"] == 10.0


def test_domestic_realtime_engine_fails_closed_on_stale_data_by_default(tmp_path):
    fixture = load_domestic_realtime_fixture(
        write(
            tmp_path,
            "domestic_realtime_fixture.json",
            domestic_realtime_fixture_payload(
                events=[
                    event_payload(
                        provider_timestamp="2026-06-17T08:58:00+09:00",
                        received_timestamp="2026-06-17T09:00:10+09:00",
                    )
                ],
            ),
        )
    )
    report = build_domestic_realtime_quality_report(fixture)
    assert report.quality_status == RealtimeQualityStatus.FAILED_STALE


def test_domestic_realtime_engine_allows_report_only_downgrade_when_explicit(tmp_path):
    fixture = load_domestic_realtime_fixture(
        write(
            tmp_path,
            "domestic_realtime_fixture.json",
            domestic_realtime_fixture_payload(
                report_only_mode=True,
                staleness_policy={
                    "default_policy": "FAIL_CLOSED",
                    "provider_timestamp_required": True,
                    "received_timestamp_required": True,
                    "maximum_provider_to_received_lag_seconds": 5,
                    "maximum_event_age_seconds": 60,
                    "impossible_timestamp_rejection": True,
                    "timestamp_mismatch_treatment": "STALE_OR_INVALID",
                    "allow_report_only_downgrade": True,
                },
                events=[
                    event_payload(
                        provider_timestamp="2026-06-17T08:58:00+09:00",
                        received_timestamp="2026-06-17T09:00:10+09:00",
                    )
                ],
            ),
        )
    )
    report = build_domestic_realtime_quality_report(fixture)
    assert report.quality_status == RealtimeQualityStatus.REPORT_ONLY_STALE


def test_domestic_realtime_engine_rejects_unsafe_order_trigger_attempt(tmp_path):
    payload = domestic_realtime_fixture_payload(
        events=[event_payload(extra={"data_quality_flags": ["ORDER_TRIGGER_ATTEMPT"]})]
    )
    fixture = load_domestic_realtime_fixture(write(tmp_path, "domestic_realtime_fixture.json", payload))
    report = build_domestic_realtime_quality_report(fixture)
    assert "ORDER_TRIGGER_ATTEMPT" in report.block_reasons
