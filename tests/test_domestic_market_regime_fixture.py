import pytest

from stock_risk_mcp.domestic_market_regime_fixture import load_domestic_market_regime_fixture
from stock_risk_mcp.domestic_market_regime_models import MarketRegimeLabel
from tests.test_domestic_realtime_fixture import write


def market_regime_config_payload(*, strategy_track: str = "DOMESTIC_KR"):
    return {
        "config_id": "domestic-market-regime-config-1",
        "strategy_track": strategy_track,
        "market_profile_id": "KRX",
        "explicit_regime_classification_opt_in": True,
        "stale_evidence_policy": "FAIL_CLOSED",
        "report_only_eligibility_mode": "AUXILIARY_METADATA_ONLY",
        "threshold_profile_id": "DOMESTIC_REGIME_THRESHOLDS_V1",
        "evidence_sufficiency_mode": "STRICT_OR_INSUFFICIENT",
        "wording_validation_mode": "FAIL_CLOSED",
        "non_executable_enforcement_mode": "FAIL_CLOSED",
        "non_executable": True,
        "signal_generation_allowed": False,
        "cloud_llm_called": False,
        "model_runtime_called": False,
        "prompt_pack_executed": False,
        "prompt_stub_executed": False,
        "ml_model_trained": False,
    }


def market_regime_fixture_payload(
    *,
    fixture_id: str = "domestic-market-regime-fixture-1",
    strategy_track: str = "DOMESTIC_KR",
    explicit_report_only: bool = False,
    data_quality_flags: list[str] | None = None,
):
    return {
        "schema_version": "4.11-domestic-market-regime-fixture",
        "fixture_id": fixture_id,
        "created_at": "2026-06-18T09:00:00+09:00",
        "market_regime_config": market_regime_config_payload(strategy_track=strategy_track),
        "market_regime_input_set": {
            "input_set_id": "domestic-market-regime-input-set-1",
            "strategy_track": strategy_track,
            "market_profile_summary": {"market_id": "KRX", "country": "KR", "base_currency": "KRW"},
            "observation_window_metadata": {
                "window_id": "OPENING_30M",
                "start_timestamp": "2026-06-18T09:00:00+09:00",
                "end_timestamp": "2026-06-18T09:30:00+09:00",
            },
            "index_evidence": {
                "index_id": "KOSPI",
                "short_return_pct": 1.4,
                "medium_return_pct": 2.2,
                "drawdown_proxy_pct": -0.8,
                "stale": False,
                "data_quality_flags": [],
            },
            "sector_evidence": {
                "sector_universe_id": "KRX_MAIN_SECTORS",
                "sector_return_distribution": {"SEMICONDUCTOR": 2.1, "AUTO": 1.6, "BIO": 0.5},
                "leadership_concentration_pct": 0.68,
                "rotation_proxy": 0.22,
                "stale": False,
                "data_quality_flags": [],
            },
            "breadth_evidence": {
                "breadth_proxy_pct": 0.64,
                "advancing_count_proxy": 410,
                "declining_count_proxy": 210,
                "stale": False,
                "data_quality_flags": [],
            },
            "liquidity_evidence": {
                "turnover_proxy_ratio": 1.18,
                "volume_expansion_proxy_ratio": 1.21,
                "stale": False,
                "data_quality_flags": [],
            },
            "volatility_evidence": {
                "volatility_proxy_pct": 1.2,
                "volatility_expansion_proxy_ratio": 0.92,
                "stale": False,
                "data_quality_flags": [],
            },
            "risk_evidence": {
                "risk_off_warning_score": 0.18,
                "stress_marker_count": 0,
                "defensive_condition_markers": [],
                "stale": False,
                "data_quality_flags": [],
            },
            "data_quality_flags": data_quality_flags or [],
            "explicit_report_only": explicit_report_only,
            "source_trace_references": ["fixture://domestic-market-regime-fixture-1"],
        },
    }


def test_domestic_market_regime_fixture_loads_valid_input(tmp_path):
    fixture = load_domestic_market_regime_fixture(
        write(tmp_path, "domestic_market_regime_fixture.json", market_regime_fixture_payload())
    )
    assert fixture.market_regime_config.strategy_track.value == "DOMESTIC_KR"
    assert fixture.market_regime_input_set.index_evidence.index_id == "KOSPI"


def test_domestic_market_regime_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_domestic_market_regime_fixture(
            write(tmp_path, "domestic_market_regime_fixture.txt", market_regime_fixture_payload())
        )


def test_domestic_market_regime_fixture_rejects_missing_strategy_track(tmp_path):
    payload = market_regime_fixture_payload()
    del payload["market_regime_config"]["strategy_track"]
    with pytest.raises(ValueError, match="strategy_track"):
        load_domestic_market_regime_fixture(
            write(tmp_path, "domestic_market_regime_fixture.json", payload)
        )


def test_domestic_market_regime_fixture_rejects_missing_market_profile(tmp_path):
    payload = market_regime_fixture_payload()
    del payload["market_regime_input_set"]["market_profile_summary"]
    with pytest.raises(ValueError, match="market_profile"):
        load_domestic_market_regime_fixture(
            write(tmp_path, "domestic_market_regime_fixture.json", payload)
        )


def test_domestic_market_regime_fixture_rejects_missing_index_evidence(tmp_path):
    payload = market_regime_fixture_payload()
    del payload["market_regime_input_set"]["index_evidence"]
    with pytest.raises(ValueError, match="index_evidence"):
        load_domestic_market_regime_fixture(
            write(tmp_path, "domestic_market_regime_fixture.json", payload)
        )


def test_domestic_market_regime_fixture_rejects_missing_sector_evidence(tmp_path):
    payload = market_regime_fixture_payload()
    del payload["market_regime_input_set"]["sector_evidence"]
    with pytest.raises(ValueError, match="sector_evidence"):
        load_domestic_market_regime_fixture(
            write(tmp_path, "domestic_market_regime_fixture.json", payload)
        )


def test_domestic_market_regime_fixture_rejects_overseas_track(tmp_path):
    with pytest.raises(ValueError, match="DOMESTIC_KR"):
        load_domestic_market_regime_fixture(
            write(
                tmp_path,
                "domestic_market_regime_fixture.json",
                market_regime_fixture_payload(strategy_track="OVERSEAS_US"),
            )
        )


def test_domestic_market_regime_fixture_rejects_unsafe_trigger_attempt(tmp_path):
    with pytest.raises(ValueError, match="unsafe trigger"):
        load_domestic_market_regime_fixture(
            write(
                tmp_path,
                "domestic_market_regime_fixture.json",
                market_regime_fixture_payload(data_quality_flags=["UNSAFE_TRIGGER_ATTEMPT"]),
            )
        )


def test_domestic_market_regime_fixture_exposes_safe_regime_label_enum():
    assert MarketRegimeLabel.REGIME_RISK_ON.value == "REGIME_RISK_ON"
