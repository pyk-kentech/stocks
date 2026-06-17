from stock_risk_mcp.domestic_distillation_dataset_engine import (
    build_domestic_distillation_dataset_gap_report,
    build_domestic_distillation_dataset_pack,
    build_domestic_distillation_dataset_safety_report,
    build_domestic_distillation_dataset_validation_report,
)
from stock_risk_mcp.domestic_distillation_dataset_fixture import load_domestic_distillation_dataset_fixture
from tests.test_domestic_distillation_dataset_fixture import (
    distillation_config_payload,
    distillation_dataset_fixture_payload,
    distillation_policy_payload,
)
from tests.test_domestic_realtime_fixture import write


def _load(tmp_path, payload):
    return load_domestic_distillation_dataset_fixture(
        write(tmp_path, "domestic_distillation_dataset_fixture.json", payload)
    )


def test_domestic_distillation_dataset_builds_primary_records_from_sub_summaries(tmp_path):
    fixture = _load(tmp_path, distillation_dataset_fixture_payload(tmp_path))
    pack = build_domestic_distillation_dataset_pack(fixture)
    record_types = {record.record_type.value for record in pack.records}
    assert "SCENARIO_FAMILY_RECORD" in record_types
    assert "REPLAY_WINDOW_RECORD" in record_types
    assert "OBSERVATION_HORIZON_RECORD" in record_types


def test_domestic_distillation_dataset_optionally_includes_bundle_aggregate_record(tmp_path):
    fixture = _load(tmp_path, distillation_dataset_fixture_payload(tmp_path))
    pack = build_domestic_distillation_dataset_pack(fixture)
    assert any(record.record_type.value == "BUNDLE_AGGREGATE_RECORD" for record in pack.records)


def test_domestic_distillation_dataset_records_preserve_required_markers(tmp_path):
    fixture = _load(tmp_path, distillation_dataset_fixture_payload(tmp_path))
    pack = build_domestic_distillation_dataset_pack(fixture)
    assert all(record.training_only is True for record in pack.records)
    assert all(record.runtime_decision_allowed is False for record in pack.records)
    assert all(record.llm_runtime_allowed is False for record in pack.records)
    assert all(record.cloud_llm_called is False for record in pack.records)
    assert all(record.local_model_runtime_called is False for record in pack.records)
    assert all(record.non_executable is True for record in pack.records)


def test_domestic_distillation_dataset_builds_validation_report(tmp_path):
    fixture = _load(tmp_path, distillation_dataset_fixture_payload(tmp_path))
    report = build_domestic_distillation_dataset_validation_report(fixture)
    assert report.valid is True
    assert report.training_only_metadata_present is True


def test_domestic_distillation_dataset_builds_gap_report(tmp_path):
    payload = distillation_dataset_fixture_payload(tmp_path)
    payload["training_only_distillation_input_set"]["scenario_family_coverage"] = []
    fixture = _load(tmp_path, payload)
    report = build_domestic_distillation_dataset_gap_report(fixture)
    assert "INSUFFICIENT_SCENARIO_COVERAGE" in report.gap_categories


def test_domestic_distillation_dataset_builds_safety_report(tmp_path):
    fixture = _load(tmp_path, distillation_dataset_fixture_payload(tmp_path))
    report = build_domestic_distillation_dataset_safety_report(fixture)
    assert report.safety_boundary.runtime_decision_allowed is False
    assert report.safety_boundary.llm_runtime_allowed is False


def test_domestic_distillation_dataset_detects_missing_primary_label_policy(tmp_path):
    payload = distillation_dataset_fixture_payload(
        tmp_path,
        policy=distillation_policy_payload(allowed_primary_labels=[]),
    )
    fixture = _load(tmp_path, payload)
    report = build_domestic_distillation_dataset_validation_report(fixture)
    assert report.valid is False
    assert "MISSING_PRIMARY_LABEL" in report.block_reasons


def test_domestic_distillation_dataset_detects_prompt_execution_attempt(tmp_path):
    payload = distillation_dataset_fixture_payload(tmp_path)
    payload["training_only_distillation_input_set"]["prompt_stub_execution_requested"] = True
    fixture = _load(tmp_path, payload)
    report = build_domestic_distillation_dataset_validation_report(fixture)
    assert report.valid is False
    assert "PROMPT_EXECUTION_NOT_ALLOWED" in report.block_reasons


def test_domestic_distillation_dataset_detects_llm_runtime_marker(tmp_path):
    payload = distillation_dataset_fixture_payload(
        tmp_path,
        config=distillation_config_payload(),
    )
    payload["training_only_distillation_config"]["llm_runtime_allowed"] = True
    fixture = _load(tmp_path, payload)
    report = build_domestic_distillation_dataset_gap_report(fixture)
    assert "LLM_RUNTIME_NOT_ALLOWED" in report.gap_categories


def test_domestic_distillation_dataset_detects_unsafe_label_pattern(tmp_path):
    payload = distillation_dataset_fixture_payload(
        tmp_path,
        policy=distillation_policy_payload(allowed_primary_labels=["BUY"]),
    )
    fixture = _load(tmp_path, payload)
    report = build_domestic_distillation_dataset_validation_report(fixture)
    assert report.valid is False
    assert "UNSAFE_LABEL_DETECTED" in report.block_reasons
