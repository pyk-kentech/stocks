import json

import pytest

from stock_risk_mcp.domestic_scanner_fixture import load_domestic_scanner_fixture
from stock_risk_mcp.domestic_scanner_models import ScannerCandidateState

from tests.test_domestic_realtime_fixture import (
    domestic_realtime_fixture_payload,
    event_payload,
    market_profile_payload,
    provider_profile_payload,
    write,
)


def scanner_config_payload(
    *,
    strategy_track: str = "DOMESTIC_KR",
    report_only_mode: bool = False,
):
    return {
        "config_id": "domestic-scanner-config-1",
        "strategy_track": strategy_track,
        "report_only_mode": report_only_mode,
        "volume_spike_ratio_threshold": 2.0,
        "price_momentum_pct_threshold": 1.0,
        "max_spread_pct": 0.02,
        "min_bid_ask_size": 100.0,
        "watchlist_add_score_threshold": 70,
        "watchlist_remove_score_threshold": 25,
        "candidate_mapping_policy": "HYBRID_V43_V33",
        "compatibility_mapping_policy": "DISCOVER_WATCH_EXCLUDE",
    }


def technical_context_payload():
    return {
        "technical_setup_summary": "MACD turn with RSI support",
        "indicator_markers": ["MACD", "RSI", "MA", "ATR", "VOLUME"],
        "setup_grade": "B",
        "evidence_freshness": "CURRENT_FIXTURE",
    }


def profitability_context_payload(
    *,
    status: str = "NON_ACTIONABLE",
):
    return {
        "profitability_context_status": status,
        "track_aware_profitability_check": "placeholder-report",
        "expected_net_profit_pct": 0.03,
        "break_even_move_pct": 0.01,
        "cost_aware_minimum_target_move_pct": 0.015,
    }


def advisory_context_payload():
    return {
        "supported_tracks": ["DOMESTIC_KR"],
        "prompt_pack_context_marker": "DOMESTIC_SCANNER_REPORT",
        "supports_report_only_mode": True,
    }


def domestic_scanner_fixture_payload(
    *,
    scanner_config: dict | None = None,
    domestic_realtime_fixture: dict | None = None,
    strategy_request: dict | None = None,
    report_only_mode: bool = False,
):
    realtime_fixture = domestic_realtime_fixture or domestic_realtime_fixture_payload(
        strategy_request=strategy_request or market_profile_payload(),
        report_only_mode=report_only_mode,
    )
    return {
        "schema_version": "4.3-domestic-scanner-fixture",
        "run_id": "domestic-scanner-run-1",
        "created_at": "2026-06-17T09:02:00+09:00",
        "scanner_config": scanner_config or scanner_config_payload(report_only_mode=report_only_mode),
        "domestic_realtime_fixture": realtime_fixture,
        "technical_context": technical_context_payload(),
        "profitability_context": profitability_context_payload(),
        "advisory_context": advisory_context_payload(),
    }


def test_domestic_scanner_fixture_loads_valid_domestic_config(tmp_path):
    fixture = load_domestic_scanner_fixture(
        write(tmp_path, "domestic_scanner_fixture.json", domestic_scanner_fixture_payload())
    )
    assert fixture.scanner_config.strategy_track.value == "DOMESTIC_KR"
    assert fixture.domestic_realtime_fixture.strategy_request.strategy_track.value == "DOMESTIC_KR"


def test_domestic_scanner_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_domestic_scanner_fixture(
            write(tmp_path, "domestic_scanner_fixture.txt", domestic_scanner_fixture_payload())
        )


def test_domestic_scanner_fixture_rejects_missing_strategy_track(tmp_path):
    payload = domestic_scanner_fixture_payload()
    del payload["scanner_config"]["strategy_track"]
    with pytest.raises(ValueError, match="strategy_track"):
        load_domestic_scanner_fixture(write(tmp_path, "domestic_scanner_fixture.json", payload))


def test_domestic_scanner_fixture_rejects_missing_market_profile(tmp_path):
    payload = domestic_scanner_fixture_payload()
    del payload["domestic_realtime_fixture"]["strategy_request"]["market_profile"]
    with pytest.raises(ValueError, match="market_profile"):
        load_domestic_scanner_fixture(write(tmp_path, "domestic_scanner_fixture.json", payload))


def test_domestic_scanner_fixture_rejects_overseas_track(tmp_path):
    payload = domestic_scanner_fixture_payload(
        scanner_config=scanner_config_payload(strategy_track="OVERSEAS_US"),
        domestic_realtime_fixture=domestic_realtime_fixture_payload(
            strategy_request=market_profile_payload(
                strategy_track="OVERSEAS_US",
                market_id="US_EQUITY",
                country="US",
                base_currency="USD",
            ),
            provider_profile=provider_profile_payload(
                strategy_track="OVERSEAS_US",
                market_id="US_EQUITY",
            ),
            events=[
                event_payload(
                    extra={"strategy_track": "OVERSEAS_US", "market_id": "US_EQUITY"}
                )
            ],
        ),
    )
    with pytest.raises(ValueError, match="DOMESTIC_KR"):
        load_domestic_scanner_fixture(write(tmp_path, "domestic_scanner_fixture.json", payload))


def test_domestic_scanner_fixture_exposes_internal_state_enum():
    assert ScannerCandidateState.SCANNER_READY.value == "SCANNER_READY"
