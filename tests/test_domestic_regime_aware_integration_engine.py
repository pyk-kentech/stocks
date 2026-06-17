import pytest

from stock_risk_mcp.domestic_regime_aware_integration_engine import (
    build_domestic_regime_aware_gap_report,
    build_domestic_regime_aware_integration_report,
    build_domestic_regime_aware_safety_report,
)
from stock_risk_mcp.domestic_regime_aware_integration_fixture import (
    load_domestic_regime_aware_integration_fixture,
)
from tests.test_domestic_realtime_fixture import write
from tests.test_domestic_regime_aware_integration_fixture import (
    regime_aware_integration_config_payload,
    regime_aware_integration_fixture_payload,
)


def _load(tmp_path, payload):
    return load_domestic_regime_aware_integration_fixture(
        write(tmp_path, "domestic_regime_aware_integration_fixture.json", payload)
    )


def test_domestic_regime_aware_integration_builds_valid_full_report(tmp_path):
    report = build_domestic_regime_aware_integration_report(
        _load(tmp_path, regime_aware_integration_fixture_payload(tmp_path))
    )
    assert report.primary_regime_label.value == "REGIME_RISK_ON"
    assert report.context_reference.source_market_regime_report_id


def test_domestic_regime_aware_integration_has_mandatory_sub_context_sections(tmp_path):
    report = build_domestic_regime_aware_integration_report(
        _load(tmp_path, regime_aware_integration_fixture_payload(tmp_path))
    )
    assert report.candidate_evaluation_context.section_id
    assert report.replay_context.section_id
    assert report.calibration_context.section_id
    assert report.paper_shadow_context.section_id
    assert report.outcome_review_context.section_id
    assert report.advisory_context.section_id
    assert report.distillation_context.section_id


def test_domestic_regime_aware_integration_generates_candidate_evaluation_context(tmp_path):
    report = build_domestic_regime_aware_integration_report(
        _load(tmp_path, regime_aware_integration_fixture_payload(tmp_path))
    )
    assert report.candidate_evaluation_context.primary_regime_label.value == "REGIME_RISK_ON"


def test_domestic_regime_aware_integration_generates_replay_context(tmp_path):
    report = build_domestic_regime_aware_integration_report(
        _load(tmp_path, regime_aware_integration_fixture_payload(tmp_path))
    )
    assert report.replay_context.regime_report_id


def test_domestic_regime_aware_integration_generates_calibration_context(tmp_path):
    report = build_domestic_regime_aware_integration_report(
        _load(tmp_path, regime_aware_integration_fixture_payload(tmp_path))
    )
    assert report.calibration_context.coverage_by_regime["REGIME_RISK_ON"] == 1.0


def test_domestic_regime_aware_integration_generates_paper_shadow_context(tmp_path):
    report = build_domestic_regime_aware_integration_report(
        _load(tmp_path, regime_aware_integration_fixture_payload(tmp_path))
    )
    assert report.paper_shadow_context.journal_entry_ids == ["paper-shadow-entry-1"]


def test_domestic_regime_aware_integration_generates_outcome_review_context(tmp_path):
    report = build_domestic_regime_aware_integration_report(
        _load(tmp_path, regime_aware_integration_fixture_payload(tmp_path))
    )
    assert report.outcome_review_context.favorable_count_by_regime["REGIME_RISK_ON"] == 2


def test_domestic_regime_aware_integration_generates_advisory_context(tmp_path):
    report = build_domestic_regime_aware_integration_report(
        _load(tmp_path, regime_aware_integration_fixture_payload(tmp_path))
    )
    assert report.advisory_context.regime_distribution_summary["REGIME_RISK_ON"] == 1


def test_domestic_regime_aware_integration_generates_distillation_context(tmp_path):
    report = build_domestic_regime_aware_integration_report(
        _load(tmp_path, regime_aware_integration_fixture_payload(tmp_path))
    )
    assert report.distillation_context.primary_regime_label_feature.value == "REGIME_RISK_ON"


def test_domestic_regime_aware_integration_builds_gap_report(tmp_path):
    report = build_domestic_regime_aware_gap_report(
        _load(tmp_path, regime_aware_integration_fixture_payload(tmp_path))
    )
    assert report.gap_categories == []


def test_domestic_regime_aware_integration_builds_safety_report(tmp_path):
    report = build_domestic_regime_aware_safety_report(
        _load(tmp_path, regime_aware_integration_fixture_payload(tmp_path))
    )
    assert report.safety_boundary.order_creation_allowed is False
    assert report.safety_boundary.ml_training_allowed is False


def test_domestic_regime_aware_integration_missing_regime_report_fails_closed_by_default(tmp_path):
    payload = regime_aware_integration_fixture_payload(tmp_path)
    del payload["regime_aware_input_set"]["market_regime_report"]
    fixture = _load(tmp_path, payload)
    with pytest.raises(ValueError, match="MISSING_MARKET_REGIME_REPORT"):
        build_domestic_regime_aware_integration_report(fixture)


def test_domestic_regime_aware_integration_missing_regime_report_allows_explicit_report_only_mode(tmp_path):
    payload = regime_aware_integration_fixture_payload(
        tmp_path,
        config=regime_aware_integration_config_payload(report_only_integration_mode=True),
    )
    del payload["regime_aware_input_set"]["market_regime_report"]
    del payload["regime_aware_input_set"]["market_regime_classification"]
    fixture = _load(tmp_path, payload)
    report = build_domestic_regime_aware_integration_report(fixture)
    assert report.report_only is True
    assert report.non_executable is True


def test_domestic_regime_aware_integration_stale_regime_context_fails_closed_by_default(tmp_path):
    payload = regime_aware_integration_fixture_payload(tmp_path)
    payload["regime_aware_input_set"]["market_regime_report"]["stale_evidence_summary"] = {
        "core_evidence_stale": True
    }
    fixture = _load(tmp_path, payload)
    with pytest.raises(ValueError, match="STALE_REGIME_CONTEXT"):
        build_domestic_regime_aware_integration_report(fixture)


def test_domestic_regime_aware_integration_stale_regime_context_allows_explicit_report_only_mode(tmp_path):
    payload = regime_aware_integration_fixture_payload(
        tmp_path,
        config=regime_aware_integration_config_payload(report_only_integration_mode=True),
    )
    payload["regime_aware_input_set"]["market_regime_report"]["stale_evidence_summary"] = {
        "core_evidence_stale": True
    }
    fixture = _load(tmp_path, payload)
    report = build_domestic_regime_aware_integration_report(fixture)
    assert report.report_only is True
    assert report.context_reference.report_only is True


def test_domestic_regime_aware_integration_missing_primary_regime_label_fails_closed(tmp_path):
    payload = regime_aware_integration_fixture_payload(tmp_path)
    del payload["regime_aware_input_set"]["primary_regime_label"]
    with pytest.raises(ValueError, match="primary_regime_label"):
        _load(tmp_path, payload)


def test_domestic_regime_aware_integration_track_mismatch_fails_closed(tmp_path):
    payload = regime_aware_integration_fixture_payload(tmp_path)
    payload["regime_aware_input_set"]["market_regime_report"]["strategy_track"] = "OVERSEAS_US"
    fixture = _load(tmp_path, payload)
    report = build_domestic_regime_aware_gap_report(fixture)
    assert "REGIME_CONTEXT_TRACK_MISMATCH" in report.gap_categories


def test_domestic_regime_aware_integration_market_profile_mismatch_fails_closed(tmp_path):
    payload = regime_aware_integration_fixture_payload(tmp_path)
    payload["regime_aware_input_set"]["market_regime_report"]["market_profile_id"] = "NASDAQ"
    fixture = _load(tmp_path, payload)
    report = build_domestic_regime_aware_gap_report(fixture)
    assert "REGIME_CONTEXT_MARKET_PROFILE_MISMATCH" in report.gap_categories


def test_domestic_regime_aware_integration_missing_downstream_section_fails_closed(tmp_path):
    payload = regime_aware_integration_fixture_payload(tmp_path)
    del payload["regime_aware_input_set"]["advisory_context"]
    with pytest.raises(ValueError, match="advisory_context"):
        _load(tmp_path, payload)


def test_domestic_regime_aware_integration_insufficient_coverage_gap(tmp_path):
    payload = regime_aware_integration_fixture_payload(tmp_path)
    payload["regime_aware_input_set"]["replay_context"]["has_regime_attachment"] = False
    fixture = _load(tmp_path, payload)
    report = build_domestic_regime_aware_gap_report(fixture)
    assert "INSUFFICIENT_REGIME_COVERAGE" in report.gap_categories


def test_domestic_regime_aware_integration_detects_executable_wording(tmp_path):
    payload = regime_aware_integration_fixture_payload(tmp_path)
    payload["regime_aware_input_set"]["source_trace_references"] = ["ORDER_SIGNAL"]
    fixture = _load(tmp_path, payload)
    report = build_domestic_regime_aware_gap_report(fixture)
    assert "EXECUTABLE_WORDING_DETECTED" in report.gap_categories
