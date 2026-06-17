from stock_risk_mcp.domestic_scanner_engine import (
    build_domestic_scanner_candidates,
    build_domestic_scanner_quality_report,
    build_domestic_scanner_watchlist_plan,
)
from stock_risk_mcp.domestic_scanner_fixture import load_domestic_scanner_fixture
from stock_risk_mcp.domestic_scanner_models import (
    ScannerCandidateState,
    ScannerDiscoveryCompatibility,
)
from tests.test_domestic_scanner_fixture import domestic_scanner_fixture_payload
from tests.test_domestic_realtime_fixture import event_payload, write


def _load(tmp_path, payload):
    return load_domestic_scanner_fixture(write(tmp_path, "domestic_scanner_fixture.json", payload))


def test_domestic_scanner_generates_volume_spike_candidate(tmp_path):
    fixture = _load(
        tmp_path,
        domestic_scanner_fixture_payload(
            domestic_realtime_fixture=domestic_scanner_fixture_payload()["domestic_realtime_fixture"] | {
                "events": [event_payload(extra={"volume": 1000.0, "baseline_volume": 100.0})]
            }
        ),
    )
    result = build_domestic_scanner_candidates(fixture)
    assert result.candidates[0].volume_spike_signal.signal_pass is True
    assert result.candidates[0].internal_state == ScannerCandidateState.WATCHLIST_ADD


def test_domestic_scanner_generates_price_momentum_candidate(tmp_path):
    fixture = _load(
        tmp_path,
        domestic_scanner_fixture_payload(
            domestic_realtime_fixture=domestic_scanner_fixture_payload()["domestic_realtime_fixture"] | {
                "events": [
                    event_payload(extra={"price": 71000.0, "best_bid": 70900.0, "best_ask": 71020.0})
                ]
            }
        ),
    )
    result = build_domestic_scanner_candidates(fixture)
    assert result.candidates[0].price_momentum_signal.signal_pass is True
    assert result.candidates[0].compatibility_discovery_status in {
        ScannerDiscoveryCompatibility.DISCOVER,
        ScannerDiscoveryCompatibility.WATCH,
    }


def test_domestic_scanner_generates_liquidity_candidate(tmp_path):
    fixture = _load(tmp_path, domestic_scanner_fixture_payload())
    result = build_domestic_scanner_candidates(fixture)
    assert result.candidates[0].liquidity_signal.signal_pass is True


def test_domestic_scanner_builds_watchlist_add_plan(tmp_path):
    fixture = _load(tmp_path, domestic_scanner_fixture_payload())
    report = build_domestic_scanner_candidates(fixture)
    plan = build_domestic_scanner_watchlist_plan(report)
    assert plan.additions


def test_domestic_scanner_builds_watchlist_remove_plan(tmp_path):
    fixture = _load(
        tmp_path,
        domestic_scanner_fixture_payload(
            domestic_realtime_fixture=domestic_scanner_fixture_payload()["domestic_realtime_fixture"] | {
                "events": [
                    event_payload(
                        extra={
                            "best_bid": 69990.0,
                            "best_ask": 72000.0,
                            "bid_size": 10.0,
                            "ask_size": 10.0,
                            "volume": 10.0,
                            "baseline_volume": 1000.0,
                        }
                    )
                ]
            }
        ),
    )
    report = build_domestic_scanner_candidates(fixture)
    plan = build_domestic_scanner_watchlist_plan(report)
    assert plan.removals


def test_domestic_scanner_fails_closed_on_stale_event_by_default(tmp_path):
    fixture = _load(
        tmp_path,
        domestic_scanner_fixture_payload(
            domestic_realtime_fixture=domestic_scanner_fixture_payload()["domestic_realtime_fixture"] | {
                "events": [
                    event_payload(
                        provider_timestamp="2026-06-17T08:58:00+09:00",
                        received_timestamp="2026-06-17T09:00:10+09:00",
                    )
                ]
            }
        ),
    )
    report = build_domestic_scanner_candidates(fixture)
    assert report.candidates[0].internal_state == ScannerCandidateState.BLOCKED_QUALITY


def test_domestic_scanner_allows_explicit_report_only_stale_candidate(tmp_path):
    base = domestic_scanner_fixture_payload(report_only_mode=True)
    base["domestic_realtime_fixture"]["report_only_mode"] = True
    base["domestic_realtime_fixture"]["staleness_policy"]["allow_report_only_downgrade"] = True
    base["domestic_realtime_fixture"]["events"] = [
        event_payload(
            provider_timestamp="2026-06-17T08:58:00+09:00",
            received_timestamp="2026-06-17T09:00:10+09:00",
        )
    ]
    fixture = _load(tmp_path, base)
    report = build_domestic_scanner_candidates(fixture)
    assert report.candidates[0].internal_state == ScannerCandidateState.REPORT_ONLY_STALE


def test_domestic_scanner_rejects_unsafe_order_trigger_attempt(tmp_path):
    base = domestic_scanner_fixture_payload()
    base["domestic_realtime_fixture"]["events"] = [
        event_payload(extra={"data_quality_flags": ["ORDER_TRIGGER_ATTEMPT"]})
    ]
    fixture = _load(tmp_path, base)
    report = build_domestic_scanner_candidates(fixture)
    assert report.candidates[0].internal_state == ScannerCandidateState.REJECTED_UNSAFE_TRIGGER


def test_domestic_scanner_maps_v33_compatibility_status(tmp_path):
    fixture = _load(tmp_path, domestic_scanner_fixture_payload())
    report = build_domestic_scanner_candidates(fixture)
    assert report.candidates[0].compatibility_discovery_status in {
        ScannerDiscoveryCompatibility.DISCOVER,
        ScannerDiscoveryCompatibility.WATCH,
        ScannerDiscoveryCompatibility.EXCLUDE,
    }


def test_domestic_scanner_quality_report_preserves_realtime_flags(tmp_path):
    base = domestic_scanner_fixture_payload()
    base["domestic_realtime_fixture"]["events"] = [
        event_payload(extra={"data_quality_flags": ["CUSTOM_FLAG"]})
    ]
    fixture = _load(tmp_path, base)
    report = build_domestic_scanner_quality_report(fixture)
    assert "CUSTOM_FLAG" in report.candidates[0].preserved_quality_flags
