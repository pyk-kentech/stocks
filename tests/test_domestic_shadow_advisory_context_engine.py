from stock_risk_mcp.domestic_shadow_advisory_context_engine import (
    build_domestic_shadow_advisory_context_bundle,
    build_domestic_shadow_advisory_context_gap_report,
    build_domestic_shadow_advisory_context_safety_report,
    build_domestic_shadow_advisory_context_validation_report,
)
from stock_risk_mcp.domestic_shadow_advisory_context_fixture import load_domestic_shadow_advisory_context_fixture
from tests.test_domestic_realtime_fixture import write
from tests.test_domestic_shadow_advisory_context_fixture import (
    advisory_context_config_payload,
    advisory_context_policy_payload,
    shadow_advisory_context_fixture_payload,
)


def _load(tmp_path, payload):
    return load_domestic_shadow_advisory_context_fixture(
        write(tmp_path, "domestic_shadow_advisory_context_fixture.json", payload)
    )


def test_domestic_shadow_advisory_context_builds_one_bundle_per_outcome_review_report(tmp_path):
    fixture = _load(tmp_path, shadow_advisory_context_fixture_payload(tmp_path))
    bundle = build_domestic_shadow_advisory_context_bundle(fixture)
    assert bundle.source_outcome_review_report_id == fixture.shadow_review_advisory_input_set.outcome_review_report.review_report_id


def test_domestic_shadow_advisory_context_has_mandatory_sub_summaries(tmp_path):
    fixture = _load(tmp_path, shadow_advisory_context_fixture_payload(tmp_path))
    bundle = build_domestic_shadow_advisory_context_bundle(fixture)
    assert bundle.scenario_family_sub_summaries
    assert bundle.replay_window_sub_summaries
    assert bundle.observation_horizon_sub_summaries


def test_domestic_shadow_advisory_context_generates_structured_counts_and_short_summaries(tmp_path):
    fixture = _load(tmp_path, shadow_advisory_context_fixture_payload(tmp_path))
    bundle = build_domestic_shadow_advisory_context_bundle(fixture)
    assert bundle.review_level_summary["total_outcome_labels"] >= 1
    assert "summary_text" in bundle.review_level_summary
    assert len(bundle.review_level_summary["summary_text"]) <= fixture.advisory_context_policy.deterministic_summary_length_cap


def test_domestic_shadow_advisory_context_generates_training_only_metadata(tmp_path):
    fixture = _load(tmp_path, shadow_advisory_context_fixture_payload(tmp_path))
    bundle = build_domestic_shadow_advisory_context_bundle(fixture)
    assert bundle.training_only_context is True
    assert bundle.llm_training_context_allowed is True
    assert bundle.llm_runtime_allowed is False
    assert bundle.cloud_llm_called is False
    assert bundle.local_model_runtime_called is False


def test_domestic_shadow_advisory_context_no_long_prompt_ready_blocks(tmp_path):
    fixture = _load(tmp_path, shadow_advisory_context_fixture_payload(tmp_path))
    bundle = build_domestic_shadow_advisory_context_bundle(fixture)
    sections = [bundle.review_level_summary]
    sections.extend(bundle.scenario_family_sub_summaries)
    sections.extend(bundle.replay_window_sub_summaries)
    sections.extend(bundle.observation_horizon_sub_summaries)
    assert all(len(section["summary_text"]) <= fixture.advisory_context_policy.deterministic_summary_length_cap for section in sections)


def test_domestic_shadow_advisory_context_builds_validation_report(tmp_path):
    fixture = _load(tmp_path, shadow_advisory_context_fixture_payload(tmp_path))
    report = build_domestic_shadow_advisory_context_validation_report(fixture)
    assert report.valid is True
    assert report.training_only_metadata_present is True


def test_domestic_shadow_advisory_context_builds_gap_report(tmp_path):
    payload = shadow_advisory_context_fixture_payload(
        tmp_path,
        policy=advisory_context_policy_payload(),
    )
    payload["shadow_review_advisory_input_set"]["scenario_family_coverage"] = []
    fixture = _load(tmp_path, payload)
    report = build_domestic_shadow_advisory_context_gap_report(fixture)
    assert "INSUFFICIENT_SCENARIO_COVERAGE" in report.gap_categories


def test_domestic_shadow_advisory_context_builds_safety_report(tmp_path):
    fixture = _load(tmp_path, shadow_advisory_context_fixture_payload(tmp_path))
    report = build_domestic_shadow_advisory_context_safety_report(fixture)
    assert report.safety_boundary.order_creation_allowed is False
    assert report.safety_boundary.llm_runtime_allowed is False


def test_domestic_shadow_advisory_context_detects_insufficient_symbol_coverage(tmp_path):
    payload = shadow_advisory_context_fixture_payload(tmp_path)
    payload["shadow_review_advisory_input_set"]["symbol_coverage"] = []
    fixture = _load(tmp_path, payload)
    report = build_domestic_shadow_advisory_context_validation_report(fixture)
    assert report.valid is False
    assert "INSUFFICIENT_SYMBOL_COVERAGE" in report.block_reasons


def test_domestic_shadow_advisory_context_detects_insufficient_observation_window_coverage(tmp_path):
    payload = shadow_advisory_context_fixture_payload(tmp_path)
    payload["shadow_review_advisory_input_set"]["observation_window_coverage"] = []
    fixture = _load(tmp_path, payload)
    report = build_domestic_shadow_advisory_context_gap_report(fixture)
    assert "INSUFFICIENT_OBSERVATION_WINDOW_COVERAGE" in report.gap_categories


def test_domestic_shadow_advisory_context_detects_executable_wording(tmp_path):
    payload = shadow_advisory_context_fixture_payload(tmp_path, advisory_context_markers=["BUY_NOW"])
    fixture = _load(tmp_path, payload)
    report = build_domestic_shadow_advisory_context_validation_report(fixture)
    assert report.valid is False
    assert "EXECUTABLE_WORDING_DETECTED" in report.block_reasons


def test_domestic_shadow_advisory_context_detects_unsafe_evidence_item_type(tmp_path):
    payload = shadow_advisory_context_fixture_payload(
        tmp_path,
        policy=advisory_context_policy_payload(allowed_evidence_item_types=["BUY_SIGNAL"]),
    )
    fixture = _load(tmp_path, payload)
    report = build_domestic_shadow_advisory_context_validation_report(fixture)
    assert report.valid is False
    assert "UNSAFE_EVIDENCE_ITEM_TYPE" in report.block_reasons


def test_domestic_shadow_advisory_context_detects_unsupported_advisory_task(tmp_path):
    payload = shadow_advisory_context_fixture_payload(tmp_path, supported_advisory_task_names=["UNKNOWN_TASK"])
    fixture = _load(tmp_path, payload)
    report = build_domestic_shadow_advisory_context_validation_report(fixture)
    assert report.valid is False
    assert "ADVISORY_TASK_UNSUPPORTED" in report.block_reasons


def test_domestic_shadow_advisory_context_detects_missing_training_only_marker(tmp_path):
    payload = shadow_advisory_context_fixture_payload(
        tmp_path,
        config=advisory_context_config_payload(training_only_context=False),
    )
    fixture = _load(tmp_path, payload)
    report = build_domestic_shadow_advisory_context_validation_report(fixture)
    assert report.valid is False
    assert "MISSING_TRAINING_ONLY_MARKER" in report.block_reasons


def test_domestic_shadow_advisory_context_detects_forbidden_llm_runtime_marker(tmp_path):
    payload = shadow_advisory_context_fixture_payload(
        tmp_path,
        config=advisory_context_config_payload(llm_runtime_allowed=True),
    )
    fixture = _load(tmp_path, payload)
    report = build_domestic_shadow_advisory_context_gap_report(fixture)
    assert "LLM_RUNTIME_NOT_ALLOWED" in report.gap_categories

