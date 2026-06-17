import pytest

from stock_risk_mcp.domestic_shadow_advisory_context_fixture import load_domestic_shadow_advisory_context_fixture
from stock_risk_mcp.domestic_shadow_advisory_context_models import AdvisoryContextEvidenceItemType
from stock_risk_mcp.domestic_shadow_outcome_engine import build_paper_shadow_outcome_review_report
from stock_risk_mcp.domestic_shadow_outcome_fixture import load_domestic_shadow_outcome_fixture
from tests.test_domestic_realtime_fixture import write
from tests.test_domestic_shadow_outcome_fixture import shadow_outcome_fixture_payload


def _outcome_review_report_payload(tmp_path, outcome_payload: dict | None = None):
    fixture = load_domestic_shadow_outcome_fixture(
        write(
            tmp_path,
            "domestic_shadow_outcome_fixture.json",
            outcome_payload or shadow_outcome_fixture_payload(tmp_path),
        )
    )
    return build_paper_shadow_outcome_review_report(fixture).model_dump(mode="json")


def _paper_shadow_journal_payload(tmp_path, outcome_payload: dict | None = None):
    fixture = load_domestic_shadow_outcome_fixture(
        write(
            tmp_path,
            "domestic_shadow_outcome_fixture.json",
            outcome_payload or shadow_outcome_fixture_payload(tmp_path),
        )
    )
    return fixture.shadow_outcome_input_set.paper_shadow_journal.model_dump(mode="json")


def advisory_context_config_payload(
    *,
    strategy_track: str = "DOMESTIC_KR",
    training_only_context: bool = True,
    llm_runtime_allowed: bool = False,
):
    return {
        "config_id": "domestic-shadow-advisory-context-config-1",
        "strategy_track": strategy_track,
        "market_profile_id": "KRX",
        "explicit_advisory_context_opt_in": True,
        "supported_advisory_task_names": [
            "IDENTIFY_MISSING_DATA",
            "CHALLENGE_ASSUMPTIONS",
            "ADVISORY_BOUNDARY_REFUSAL",
        ],
        "supported_tracks": ["DOMESTIC_KR"],
        "report_level_bundle_mode": "REVIEW_REPORT_LEVEL_PRIMARY",
        "sub_summary_inclusion_mode": "MANDATORY",
        "wording_validation_mode": "FAIL_CLOSED",
        "coverage_sufficiency_mode": "VALIDATE_AND_REPORT",
        "distillation_eligible": True,
        "training_only_context": training_only_context,
        "llm_training_context_allowed": True,
        "llm_runtime_allowed": llm_runtime_allowed,
        "cloud_llm_called": False,
        "local_model_runtime_called": False,
        "non_executable": True,
        "no_trade_instruction": True,
    }


def advisory_context_policy_payload(*, allowed_evidence_item_types: list[str] | None = None):
    return {
        "policy_id": "domestic-shadow-advisory-context-policy-1",
        "allowed_evidence_item_types": allowed_evidence_item_types or [
            "SHADOW_DECISION_SUMMARY",
            "OUTCOME_LABEL_SUMMARY",
            "BLOCKED_REASON_SUMMARY",
            "REPORT_ONLY_REASON_SUMMARY",
            "NON_ACTIONABLE_SUMMARY",
            "SCENARIO_COVERAGE_SUMMARY",
            "SYMBOL_COVERAGE_SUMMARY",
            "RISK_OBSERVATION_SUMMARY",
            "DATA_QUALITY_SUMMARY",
            "GAP_SUMMARY",
            "TRAINING_CONTEXT_SUMMARY",
        ],
        "forbidden_wording_patterns": ["BUY", "SELL", "ENTRY", "EXIT", "ORDER", "EXECUTE"],
        "deterministic_summary_length_cap": 160,
        "minimum_scenario_coverage_count": 1,
        "minimum_symbol_coverage_count": 1,
        "minimum_observation_window_coverage_count": 1,
        "supported_advisory_task_compatibility_mode": "STRICT",
        "non_executable_enforcement_mode": "FAIL_CLOSED",
        "gap_preservation_mode": "PRESERVE",
    }


def shadow_advisory_context_fixture_payload(
    tmp_path,
    *,
    config: dict | None = None,
    policy: dict | None = None,
    supported_advisory_task_names: list[str] | None = None,
    advisory_context_markers: list[str] | None = None,
    data_quality_flags: list[str] | None = None,
    outcome_payload: dict | None = None,
):
    journal = _paper_shadow_journal_payload(tmp_path, outcome_payload)
    outcome_review_report = _outcome_review_report_payload(tmp_path, outcome_payload)
    scenario_coverage = list(outcome_review_report["scenario_family_counts"].keys())
    symbol_coverage = list(outcome_review_report["symbol_counts"].keys())
    observation_window_coverage = list(outcome_review_report["observation_horizon_counts"].keys())
    source_promotion_gate_id = journal["entries"][0]["source_promotion_gate_id"]
    return {
        "schema_version": "4.9-domestic-shadow-advisory-context-fixture",
        "run_id": "domestic-shadow-advisory-context-run-1",
        "created_at": "2026-06-17T12:00:00+09:00",
        "shadow_review_advisory_context_config": config or advisory_context_config_payload(),
        "shadow_review_advisory_input_set": {
            "input_set_id": "domestic-shadow-advisory-context-input-set-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_summary": {"market_id": "KRX", "country": "KR", "base_currency": "KRW"},
            "paper_shadow_journal": journal,
            "source_paper_shadow_review_report_id": "paper-shadow-review-1",
            "outcome_review_report": outcome_review_report,
            "source_promotion_gate_id": source_promotion_gate_id,
            "calibration_pack_reference": "calibration-pack-1",
            "scenario_family_coverage": scenario_coverage,
            "symbol_coverage": symbol_coverage,
            "observation_window_coverage": observation_window_coverage,
            "supported_advisory_task_names": supported_advisory_task_names or [
                "IDENTIFY_MISSING_DATA",
                "CHALLENGE_ASSUMPTIONS",
            ],
            "accepts_shadow_review_context": True,
            "non_actionable_marker": True,
            "training_only_context": True,
            "advisory_context_markers": advisory_context_markers or ["NON_EXECUTABLE_CONTEXT_ONLY"],
            "data_quality_flags": data_quality_flags or [],
        },
        "advisory_context_policy": policy or advisory_context_policy_payload(),
    }


def test_domestic_shadow_advisory_context_fixture_loads_valid_input(tmp_path):
    fixture = load_domestic_shadow_advisory_context_fixture(
        write(tmp_path, "domestic_shadow_advisory_context_fixture.json", shadow_advisory_context_fixture_payload(tmp_path))
    )
    assert fixture.shadow_review_advisory_context_config.strategy_track.value == "DOMESTIC_KR"
    assert fixture.shadow_review_advisory_input_set.outcome_review_report.review_report_id


def test_domestic_shadow_advisory_context_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_domestic_shadow_advisory_context_fixture(
            write(tmp_path, "domestic_shadow_advisory_context_fixture.txt", shadow_advisory_context_fixture_payload(tmp_path))
        )


def test_domestic_shadow_advisory_context_fixture_rejects_missing_strategy_track(tmp_path):
    payload = shadow_advisory_context_fixture_payload(tmp_path)
    del payload["shadow_review_advisory_context_config"]["strategy_track"]
    with pytest.raises(ValueError, match="strategy_track"):
        load_domestic_shadow_advisory_context_fixture(
            write(tmp_path, "domestic_shadow_advisory_context_fixture.json", payload)
        )


def test_domestic_shadow_advisory_context_fixture_rejects_missing_market_profile(tmp_path):
    payload = shadow_advisory_context_fixture_payload(tmp_path)
    del payload["shadow_review_advisory_input_set"]["market_profile_summary"]
    with pytest.raises(ValueError, match="market_profile"):
        load_domestic_shadow_advisory_context_fixture(
            write(tmp_path, "domestic_shadow_advisory_context_fixture.json", payload)
        )


def test_domestic_shadow_advisory_context_fixture_rejects_missing_paper_shadow_journal(tmp_path):
    payload = shadow_advisory_context_fixture_payload(tmp_path)
    del payload["shadow_review_advisory_input_set"]["paper_shadow_journal"]
    with pytest.raises(ValueError, match="paper_shadow_journal"):
        load_domestic_shadow_advisory_context_fixture(
            write(tmp_path, "domestic_shadow_advisory_context_fixture.json", payload)
        )


def test_domestic_shadow_advisory_context_fixture_rejects_missing_outcome_review(tmp_path):
    payload = shadow_advisory_context_fixture_payload(tmp_path)
    del payload["shadow_review_advisory_input_set"]["outcome_review_report"]
    with pytest.raises(ValueError, match="outcome_review_report"):
        load_domestic_shadow_advisory_context_fixture(
            write(tmp_path, "domestic_shadow_advisory_context_fixture.json", payload)
        )


def test_domestic_shadow_advisory_context_fixture_rejects_missing_promotion_gate(tmp_path):
    payload = shadow_advisory_context_fixture_payload(tmp_path)
    del payload["shadow_review_advisory_input_set"]["source_promotion_gate_id"]
    with pytest.raises(ValueError, match="source_promotion_gate_id"):
        load_domestic_shadow_advisory_context_fixture(
            write(tmp_path, "domestic_shadow_advisory_context_fixture.json", payload)
        )


def test_domestic_shadow_advisory_context_fixture_rejects_missing_training_only_marker(tmp_path):
    payload = shadow_advisory_context_fixture_payload(tmp_path)
    del payload["shadow_review_advisory_context_config"]["training_only_context"]
    with pytest.raises(ValueError, match="training_only_context"):
        load_domestic_shadow_advisory_context_fixture(
            write(tmp_path, "domestic_shadow_advisory_context_fixture.json", payload)
        )


def test_domestic_shadow_advisory_context_fixture_rejects_overseas_track(tmp_path):
    payload = shadow_advisory_context_fixture_payload(
        tmp_path,
        config=advisory_context_config_payload(strategy_track="OVERSEAS_US"),
    )
    with pytest.raises(ValueError, match="DOMESTIC_KR"):
        load_domestic_shadow_advisory_context_fixture(
            write(tmp_path, "domestic_shadow_advisory_context_fixture.json", payload)
        )


def test_domestic_shadow_advisory_context_fixture_rejects_unsafe_trigger_attempt(tmp_path):
    payload = shadow_advisory_context_fixture_payload(tmp_path, data_quality_flags=["UNSAFE_TRIGGER_ATTEMPT"])
    with pytest.raises(ValueError, match="unsafe trigger"):
        load_domestic_shadow_advisory_context_fixture(
            write(tmp_path, "domestic_shadow_advisory_context_fixture.json", payload)
        )


def test_domestic_shadow_advisory_context_fixture_exposes_evidence_item_enum():
    assert AdvisoryContextEvidenceItemType.OUTCOME_LABEL_SUMMARY.value == "OUTCOME_LABEL_SUMMARY"
