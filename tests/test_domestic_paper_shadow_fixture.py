import pytest

from stock_risk_mcp.domestic_calibration_engine import build_promotion_gate_report
from stock_risk_mcp.domestic_calibration_fixture import load_domestic_calibration_fixture
from stock_risk_mcp.domestic_candidate_evaluation_engine import build_candidate_evaluation_report
from stock_risk_mcp.domestic_candidate_evaluation_fixture import load_domestic_candidate_evaluation_fixture
from stock_risk_mcp.domestic_paper_shadow_fixture import load_domestic_paper_shadow_fixture
from stock_risk_mcp.domestic_paper_shadow_models import PaperShadowDecisionType
from tests.test_domestic_calibration_fixture import calibration_fixture_payload
from tests.test_domestic_candidate_evaluation_fixture import (
    domestic_candidate_evaluation_fixture_payload,
)
from tests.test_domestic_realtime_fixture import write


def _promotion_gate_payload(tmp_path, calibration_payload: dict | None = None):
    fixture = load_domestic_calibration_fixture(
        write(tmp_path, "domestic_calibration_fixture.json", calibration_payload or calibration_fixture_payload(tmp_path))
    )
    return build_promotion_gate_report(fixture).model_dump(mode="json")


def _candidate_evaluation_report_payload(tmp_path, evaluation_payload: dict | None = None):
    fixture = load_domestic_candidate_evaluation_fixture(
        write(
            tmp_path,
            "domestic_candidate_evaluation_fixture.json",
            evaluation_payload or domestic_candidate_evaluation_fixture_payload(),
        )
    )
    return build_candidate_evaluation_report(fixture).model_dump(mode="json")


def paper_shadow_config_payload(
    *,
    strategy_track: str = "DOMESTIC_KR",
    explicit_opt_in: bool = True,
):
    return {
        "config_id": "domestic-paper-shadow-config-1",
        "strategy_track": strategy_track,
        "explicit_paper_shadow_opt_in": explicit_opt_in,
        "allowed_promotion_gate_statuses": ["PROMOTION_READY_FOR_PAPER_SHADOW"],
        "blocked_promotion_gate_statuses": [
            "PROMOTION_REJECTED",
            "PROMOTION_REPORT_ONLY",
            "PROMOTION_BLOCKED_SAFETY",
            "PROMOTION_BLOCKED_COVERAGE",
            "PROMOTION_BLOCKED_REGRESSION",
        ],
        "journal_generation_mode": "CANDIDATE_LEVEL_ONLY",
        "review_aggregation_mode": "DERIVED_SUMMARY_ONLY",
        "report_only_preservation_mode": "PRESERVE",
        "non_actionable_preservation_mode": "PRESERVE",
    }


def paper_shadow_fixture_payload(
    tmp_path,
    *,
    config: dict | None = None,
    promotion_gate_report: dict | None = None,
    candidate_evaluation_reports: list[dict] | None = None,
):
    gate = promotion_gate_report or _promotion_gate_payload(tmp_path)
    reports = candidate_evaluation_reports or [_candidate_evaluation_report_payload(tmp_path)]
    return {
        "schema_version": "4.7-domestic-paper-shadow-fixture",
        "run_id": "domestic-paper-shadow-run-1",
        "created_at": "2026-06-17T11:00:00+09:00",
        "paper_shadow_config": config or paper_shadow_config_payload(),
        "paper_shadow_input_set": {
            "input_set_id": "paper-shadow-input-set-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_summary": {"market_id": "KRX", "country": "KR", "base_currency": "KRW"},
            "promotion_gate_report": gate,
            "promotion_gate_criteria_reference": "domestic-calibration-criteria-1",
            "calibration_pack_reference": gate["calibration_pack_id"],
            "coverage_report_reference": "coverage-report-1",
            "regression_report_reference": "regression-report-1",
            "candidate_evaluation_reports": reports,
            "replay_provenance_markers": ["V4.5_REPLAY_FIXTURE"],
            "scenario_family_markers": ["BASELINE", "STALE_REPORT_ONLY"],
            "advisory_context_markers": ["NON_EXECUTABLE_CONTEXT_ONLY"],
        },
    }


def test_domestic_paper_shadow_fixture_loads_valid_input(tmp_path):
    fixture = load_domestic_paper_shadow_fixture(
        write(tmp_path, "domestic_paper_shadow_fixture.json", paper_shadow_fixture_payload(tmp_path))
    )
    assert fixture.paper_shadow_config.strategy_track.value == "DOMESTIC_KR"
    assert fixture.paper_shadow_input_set.promotion_gate_report.gate_status.value


def test_domestic_paper_shadow_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_domestic_paper_shadow_fixture(
            write(tmp_path, "domestic_paper_shadow_fixture.txt", paper_shadow_fixture_payload(tmp_path))
        )


def test_domestic_paper_shadow_fixture_requires_explicit_opt_in(tmp_path):
    payload = paper_shadow_fixture_payload(
        tmp_path,
        config=paper_shadow_config_payload(explicit_opt_in=False),
    )
    with pytest.raises(ValueError, match="opt-in"):
        load_domestic_paper_shadow_fixture(
            write(tmp_path, "domestic_paper_shadow_fixture.json", payload)
        )


def test_domestic_paper_shadow_fixture_rejects_missing_strategy_track(tmp_path):
    payload = paper_shadow_fixture_payload(tmp_path)
    del payload["paper_shadow_config"]["strategy_track"]
    with pytest.raises(ValueError, match="strategy_track"):
        load_domestic_paper_shadow_fixture(
            write(tmp_path, "domestic_paper_shadow_fixture.json", payload)
        )


def test_domestic_paper_shadow_fixture_rejects_missing_market_profile(tmp_path):
    payload = paper_shadow_fixture_payload(tmp_path)
    del payload["paper_shadow_input_set"]["market_profile_summary"]
    with pytest.raises(ValueError, match="market_profile"):
        load_domestic_paper_shadow_fixture(
            write(tmp_path, "domestic_paper_shadow_fixture.json", payload)
        )


def test_domestic_paper_shadow_fixture_rejects_missing_promotion_gate(tmp_path):
    payload = paper_shadow_fixture_payload(tmp_path)
    del payload["paper_shadow_input_set"]["promotion_gate_report"]
    with pytest.raises(ValueError, match="promotion_gate"):
        load_domestic_paper_shadow_fixture(
            write(tmp_path, "domestic_paper_shadow_fixture.json", payload)
        )


def test_domestic_paper_shadow_fixture_rejects_missing_candidate_evaluation(tmp_path):
    payload = paper_shadow_fixture_payload(tmp_path)
    payload["paper_shadow_input_set"]["candidate_evaluation_reports"] = []
    with pytest.raises(ValueError, match="candidate evaluation"):
        load_domestic_paper_shadow_fixture(
            write(tmp_path, "domestic_paper_shadow_fixture.json", payload)
        )


def test_domestic_paper_shadow_fixture_rejects_overseas_track(tmp_path):
    payload = paper_shadow_fixture_payload(
        tmp_path,
        config=paper_shadow_config_payload(strategy_track="OVERSEAS_US"),
    )
    with pytest.raises(ValueError, match="DOMESTIC_KR"):
        load_domestic_paper_shadow_fixture(
            write(tmp_path, "domestic_paper_shadow_fixture.json", payload)
        )


def test_domestic_paper_shadow_fixture_exposes_decision_type_enum():
    assert PaperShadowDecisionType.SHADOW_WATCH.value == "SHADOW_WATCH"
