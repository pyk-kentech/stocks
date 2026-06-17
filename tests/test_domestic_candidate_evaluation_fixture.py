import pytest

from stock_risk_mcp.domestic_candidate_evaluation_fixture import load_domestic_candidate_evaluation_fixture
from stock_risk_mcp.domestic_candidate_evaluation_models import CandidateEvaluationState

from tests.test_domestic_realtime_fixture import (
    domestic_realtime_fixture_payload,
    event_payload,
    market_profile_payload,
    provider_profile_payload,
    write,
)
from tests.test_domestic_scanner_fixture import domestic_scanner_fixture_payload


def technical_evidence_payload(
    *,
    setup_grade: str = "A",
    evidence_freshness: str = "CURRENT_FIXTURE",
    missing_flags: list[str] | None = None,
):
    return {
        "evidence_id": "tech-evidence-1",
        "ticker": "005930",
        "macd_evidence_summary": "MACD positive crossover",
        "rsi_evidence_summary": "RSI above 55",
        "moving_average_evidence_summary": "Price above MA20 and MA60",
        "hma_evidence_summary": "HMA rising",
        "atr_risk_evidence_summary": "ATR stable",
        "volume_evidence_summary": "Volume expansion confirmed",
        "divergence_evidence_summary": "No bearish divergence",
        "setup_grade": setup_grade,
        "evidence_freshness": evidence_freshness,
        "missing_evidence_flags": missing_flags or [],
    }


def profitability_context_payload(
    *,
    status: str = "ACTIONABLE",
    expected_net_profit: float = 25000.0,
    expected_net_return_pct: float = 0.03,
    break_even_move_pct: float = 0.01,
    cost_aware_minimum_target_move_pct: float = 0.015,
):
    return {
        "profitability_context_status": status,
        "track_aware_profitability_check": "fixture-profitability-check",
        "expected_net_profit": expected_net_profit,
        "expected_net_return_percentage": expected_net_return_pct,
        "break_even_move": break_even_move_pct,
        "cost_aware_minimum_target_move": cost_aware_minimum_target_move_pct,
    }


def evaluation_config_payload(
    *,
    strategy_track: str = "DOMESTIC_KR",
    report_only_mode: bool = False,
):
    return {
        "config_id": "domestic-candidate-evaluation-config-1",
        "strategy_track": strategy_track,
        "report_only_mode": report_only_mode,
        "minimum_technical_score_threshold": 60,
        "minimum_profitability_score_threshold": 60,
        "minimum_risk_acceptance_threshold": 50,
        "stale_evaluation_policy": "FAIL_CLOSED",
        "missing_evidence_policy": "BLOCK_OR_WATCH",
        "scanner_compatibility_carry_forward_policy": "PRESERVE",
        "evaluation_compatibility_mapping_policy": "DUAL_COMPATIBILITY",
    }


def advisory_context_payload():
    return {
        "supported_tracks": ["DOMESTIC_KR"],
        "prompt_pack_context_marker": "DOMESTIC_CANDIDATE_EVALUATION",
        "supports_report_only_mode": True,
    }


def domestic_candidate_evaluation_fixture_payload(
    *,
    evaluation_config: dict | None = None,
    scanner_fixture: dict | None = None,
    technical_evidence: dict | None = None,
    profitability_context: dict | None = None,
    advisory_context: dict | None = None,
):
    return {
        "schema_version": "4.4-domestic-candidate-evaluation-fixture",
        "run_id": "domestic-candidate-evaluation-run-1",
        "created_at": "2026-06-17T09:03:00+09:00",
        "evaluation_config": evaluation_config or evaluation_config_payload(),
        "domestic_scanner_fixture": scanner_fixture or domestic_scanner_fixture_payload(),
        "technical_evidence_context": technical_evidence or technical_evidence_payload(),
        "profitability_context": profitability_context or profitability_context_payload(),
        "advisory_context": advisory_context or advisory_context_payload(),
    }


def test_domestic_candidate_evaluation_fixture_loads_valid_domestic_input(tmp_path):
    fixture = load_domestic_candidate_evaluation_fixture(
        write(tmp_path, "domestic_candidate_evaluation_fixture.json", domestic_candidate_evaluation_fixture_payload())
    )
    assert fixture.evaluation_config.strategy_track.value == "DOMESTIC_KR"
    assert fixture.domestic_scanner_fixture.scanner_config.strategy_track.value == "DOMESTIC_KR"


def test_domestic_candidate_evaluation_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_domestic_candidate_evaluation_fixture(
            write(tmp_path, "domestic_candidate_evaluation_fixture.txt", domestic_candidate_evaluation_fixture_payload())
        )


def test_domestic_candidate_evaluation_fixture_rejects_missing_strategy_track(tmp_path):
    payload = domestic_candidate_evaluation_fixture_payload()
    del payload["evaluation_config"]["strategy_track"]
    with pytest.raises(ValueError, match="strategy_track"):
        load_domestic_candidate_evaluation_fixture(
            write(tmp_path, "domestic_candidate_evaluation_fixture.json", payload)
        )


def test_domestic_candidate_evaluation_fixture_rejects_missing_market_profile(tmp_path):
    payload = domestic_candidate_evaluation_fixture_payload()
    del payload["domestic_scanner_fixture"]["domestic_realtime_fixture"]["strategy_request"]["market_profile"]
    with pytest.raises(ValueError, match="market_profile"):
        load_domestic_candidate_evaluation_fixture(
            write(tmp_path, "domestic_candidate_evaluation_fixture.json", payload)
        )


def test_domestic_candidate_evaluation_fixture_rejects_overseas_track(tmp_path):
    payload = domestic_candidate_evaluation_fixture_payload(
        evaluation_config=evaluation_config_payload(strategy_track="OVERSEAS_US"),
        scanner_fixture=domestic_scanner_fixture_payload(
            scanner_config={
                **domestic_scanner_fixture_payload()["scanner_config"],
                "strategy_track": "OVERSEAS_US",
            },
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
        ),
    )
    with pytest.raises(ValueError, match="DOMESTIC_KR"):
        load_domestic_candidate_evaluation_fixture(
            write(tmp_path, "domestic_candidate_evaluation_fixture.json", payload)
        )


def test_domestic_candidate_evaluation_fixture_exposes_state_enum():
    assert CandidateEvaluationState.EVALUATION_READY.value == "EVALUATION_READY"
