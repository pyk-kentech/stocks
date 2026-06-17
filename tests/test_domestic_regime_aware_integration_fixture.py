import pytest

from stock_risk_mcp.domestic_market_regime_engine import (
    build_market_regime_classification,
    build_market_regime_report,
)
from stock_risk_mcp.domestic_market_regime_fixture import load_domestic_market_regime_fixture
from stock_risk_mcp.domestic_regime_aware_integration_fixture import (
    load_domestic_regime_aware_integration_fixture,
)
from tests.test_domestic_market_regime_fixture import market_regime_fixture_payload
from tests.test_domestic_realtime_fixture import write


def _market_regime_report_payload(tmp_path, regime_payload: dict | None = None):
    fixture = load_domestic_market_regime_fixture(
        write(
            tmp_path,
            "domestic_market_regime_fixture.json",
            regime_payload or market_regime_fixture_payload(),
        )
    )
    return build_market_regime_report(fixture).model_dump(mode="json")


def _market_regime_classification_payload(tmp_path, regime_payload: dict | None = None):
    fixture = load_domestic_market_regime_fixture(
        write(
            tmp_path,
            "domestic_market_regime_fixture.json",
            regime_payload or market_regime_fixture_payload(),
        )
    )
    return build_market_regime_classification(fixture).model_dump(mode="json")


def regime_aware_integration_config_payload(
    *,
    strategy_track: str = "DOMESTIC_KR",
    report_only_integration_mode: bool = False,
):
    return {
        "config_id": "domestic-regime-aware-integration-config-1",
        "strategy_track": strategy_track,
        "market_profile_id": "KRX",
        "explicit_regime_aware_integration_opt_in": True,
        "report_only_integration_mode": report_only_integration_mode,
        "stale_regime_context_policy": "FAIL_CLOSED",
        "missing_regime_report_policy": "FAIL_CLOSED",
        "coverage_sufficiency_mode": "STRICT_SECTION_COVERAGE",
        "wording_validation_mode": "FAIL_CLOSED",
        "non_executable_enforcement_mode": "FAIL_CLOSED",
        "non_executable": True,
        "orders_created": False,
        "order_intent_created": False,
        "order_drafts_created": False,
        "execution_approval_enabled": False,
        "cloud_llm_called": False,
        "model_runtime_called": False,
        "ml_training_run": False,
        "real_market_data_fetched": False,
        "prompt_pack_executed": False,
        "prompt_stub_executed": False,
    }


def _candidate_evaluation_context():
    return {
        "section_id": "candidate-evaluation-context-1",
        "source_artifact_ids": ["candidate-evaluation-report-1"],
        "has_regime_attachment": True,
        "watch_only_reason_count": 1,
        "blocked_reason_count": 0,
        "report_only_reason_count": 0,
        "non_actionable": True,
    }


def _replay_context():
    return {
        "section_id": "replay-context-1",
        "source_artifact_ids": ["replay-window-1"],
        "has_regime_attachment": True,
        "replay_window_ids": ["REPLAY_OPENING_30M"],
        "grouped_metric_counts": {"REGIME_RISK_ON": 3},
        "non_actionable": True,
    }


def _calibration_context():
    return {
        "section_id": "calibration-context-1",
        "source_artifact_ids": ["calibration-pack-1"],
        "has_regime_attachment": True,
        "candidates_generated_by_regime": {"REGIME_RISK_ON": 5},
        "blocked_candidates_by_regime": {"REGIME_RISK_OFF": 2},
        "report_only_candidates_by_regime": {},
        "coverage_by_regime": {"REGIME_RISK_ON": 1.0},
        "non_actionable": True,
    }


def _paper_shadow_context():
    return {
        "section_id": "paper-shadow-context-1",
        "source_artifact_ids": ["paper-shadow-journal-1"],
        "has_regime_attachment": True,
        "journal_entry_ids": ["paper-shadow-entry-1"],
        "candidate_ids": ["candidate-1"],
        "regime_context_marker": "PRESERVED",
        "non_actionable": True,
    }


def _outcome_review_context():
    return {
        "section_id": "outcome-review-context-1",
        "source_artifact_ids": ["outcome-review-report-1"],
        "has_regime_attachment": True,
        "favorable_count_by_regime": {"REGIME_RISK_ON": 2},
        "adverse_count_by_regime": {"REGIME_RISK_OFF": 1},
        "neutral_count_by_regime": {},
        "inconclusive_count_by_regime": {},
        "report_only_count_by_regime": {},
        "blocked_confirmed_count_by_regime": {},
        "insufficient_data_count_by_regime": {},
        "non_actionable": True,
    }


def _advisory_context():
    return {
        "section_id": "advisory-context-1",
        "source_artifact_ids": ["advisory-context-bundle-1"],
        "has_regime_attachment": True,
        "regime_distribution_summary": {"REGIME_RISK_ON": 1},
        "outcome_label_summary_by_regime": {"REGIME_RISK_ON": {"OUTCOME_FAVORABLE": 2}},
        "blocked_report_only_non_actionable_summary_by_regime": {},
        "data_quality_summary_by_regime": {},
        "deterministic_regime_summary": "Risk-on context preserved for advisory explanation only.",
        "non_actionable": True,
    }


def _distillation_context():
    return {
        "section_id": "distillation-context-1",
        "source_artifact_ids": ["distillation-dataset-pack-1"],
        "has_regime_attachment": True,
        "primary_regime_label_feature": "REGIME_RISK_ON",
        "secondary_regime_label_features": ["REGIME_INDEX_UPTREND"],
        "regime_evidence_strength_feature": "EVIDENCE_STRONG",
        "regime_data_quality_feature": [],
        "regime_report_only_marker": False,
        "regime_stale_marker": False,
        "regime_conditioned_label_distribution_metadata": {"LABEL_FAVORABLE_OBSERVATION": 3},
        "training_only": True,
        "non_actionable": True,
    }


def regime_aware_integration_fixture_payload(
    tmp_path,
    *,
    config: dict | None = None,
    regime_payload: dict | None = None,
):
    report = _market_regime_report_payload(tmp_path, regime_payload)
    classification = _market_regime_classification_payload(tmp_path, regime_payload)
    return {
        "schema_version": "4.12-domestic-regime-aware-integration-fixture",
        "fixture_id": "domestic-regime-aware-integration-fixture-1",
        "created_at": "2026-06-18T11:00:00+09:00",
        "regime_aware_integration_config": config or regime_aware_integration_config_payload(),
        "regime_aware_input_set": {
            "input_set_id": "domestic-regime-aware-input-set-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_summary": {"market_id": "KRX", "country": "KR", "base_currency": "KRW"},
            "market_regime_report": report,
            "market_regime_classification": classification,
            "primary_regime_label": report["primary_regime_label"],
            "secondary_regime_labels": report["secondary_regime_labels"],
            "evidence_strength_bucket": report["evidence_strength_bucket"],
            "data_quality_flags": report["data_quality_flags"],
            "missing_evidence_summary": report["missing_evidence_summary"],
            "stale_evidence_summary": report["stale_evidence_summary"],
            "report_only": report["report_only"],
            "source_trace_references": report["source_trace_references"],
            "candidate_evaluation_context": _candidate_evaluation_context(),
            "replay_context": _replay_context(),
            "calibration_context": _calibration_context(),
            "paper_shadow_context": _paper_shadow_context(),
            "outcome_review_context": _outcome_review_context(),
            "advisory_context": _advisory_context(),
            "distillation_context": _distillation_context(),
        },
    }


def test_domestic_regime_aware_integration_fixture_loads_valid_input(tmp_path):
    fixture = load_domestic_regime_aware_integration_fixture(
        write(
            tmp_path,
            "domestic_regime_aware_integration_fixture.json",
            regime_aware_integration_fixture_payload(tmp_path),
        )
    )
    assert fixture.regime_aware_integration_config.strategy_track.value == "DOMESTIC_KR"
    assert fixture.regime_aware_input_set.market_regime_report.report_id


def test_domestic_regime_aware_integration_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_domestic_regime_aware_integration_fixture(
            write(
                tmp_path,
                "domestic_regime_aware_integration_fixture.txt",
                regime_aware_integration_fixture_payload(tmp_path),
            )
        )


def test_domestic_regime_aware_integration_fixture_rejects_missing_strategy_track(tmp_path):
    payload = regime_aware_integration_fixture_payload(tmp_path)
    del payload["regime_aware_integration_config"]["strategy_track"]
    with pytest.raises(ValueError, match="strategy_track"):
        load_domestic_regime_aware_integration_fixture(
            write(tmp_path, "domestic_regime_aware_integration_fixture.json", payload)
        )


def test_domestic_regime_aware_integration_fixture_rejects_missing_market_profile(tmp_path):
    payload = regime_aware_integration_fixture_payload(tmp_path)
    del payload["regime_aware_input_set"]["market_profile_summary"]
    with pytest.raises(ValueError, match="market_profile"):
        load_domestic_regime_aware_integration_fixture(
            write(tmp_path, "domestic_regime_aware_integration_fixture.json", payload)
        )


def test_domestic_regime_aware_integration_fixture_rejects_overseas_track(tmp_path):
    payload = regime_aware_integration_fixture_payload(
        tmp_path,
        config=regime_aware_integration_config_payload(strategy_track="OVERSEAS_US"),
    )
    with pytest.raises(ValueError, match="DOMESTIC_KR"):
        load_domestic_regime_aware_integration_fixture(
            write(tmp_path, "domestic_regime_aware_integration_fixture.json", payload)
        )


def test_domestic_regime_aware_integration_fixture_rejects_unsafe_trigger_attempt(tmp_path):
    payload = regime_aware_integration_fixture_payload(tmp_path)
    payload["regime_aware_input_set"]["data_quality_flags"] = ["UNSAFE_TRIGGER_ATTEMPT"]
    with pytest.raises(ValueError, match="unsafe trigger"):
        load_domestic_regime_aware_integration_fixture(
            write(tmp_path, "domestic_regime_aware_integration_fixture.json", payload)
        )
