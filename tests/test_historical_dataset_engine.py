import copy
import csv
import json

import pytest

from stock_risk_mcp.historical_dataset_engine import (
    build_historical_dataset_assembly,
    export_historical_dataset_csv,
    export_historical_dataset_json,
    export_historical_dataset_jsonl,
)
from stock_risk_mcp.historical_dataset_models import HistoricalDatasetAssemblyInput
from tests.test_historical_dataset_models import historical_dataset_fixture_payload


def build_input(payload=None):
    return HistoricalDatasetAssemblyInput.model_validate(payload or historical_dataset_fixture_payload())


def _assembly_payload():
    payload = historical_dataset_fixture_payload()
    payload["records"] = []
    payload["export_manifest"]["record_count"] = 0
    payload["quality_report"]["record_count"] = 0
    payload["quality_report"]["valid_record_count"] = 0
    return payload


def test_build_historical_dataset_assembly_succeeds_and_preserves_feature_outcome_separation():
    result = build_historical_dataset_assembly(build_input(_assembly_payload()))

    assert len(result.records) == 1
    record = result.records[0]
    feature_dump = record.feature_block.model_dump(mode="json")
    outcome_dump = record.outcome_block.model_dump(mode="json")
    assert record.replay_window_id == "WINDOW-1"
    assert record.scanner_replay_candidate_seed_id == "SEED-1"
    assert record.outcome_observation_id == "OBSERVATION-INPUT-1"
    assert "outcome_label" not in feature_dump
    assert "forward_return_pct" not in feature_dump
    assert "max_favorable_excursion_pct" not in feature_dump
    assert outcome_dump["outcome_label"] == "OUTCOME_REPORT_ONLY"
    assert outcome_dump["forward_return_pct"] == 0.01


def test_build_historical_dataset_assembly_does_not_mutate_scanner_replay_input():
    observation_input = build_input(_assembly_payload())
    before = copy.deepcopy(observation_input.scanner_replay_input.model_dump(mode="json"))

    result = build_historical_dataset_assembly(observation_input)

    after = observation_input.scanner_replay_input.model_dump(mode="json")
    assert before == after
    assert result.scanner_replay_input.model_dump(mode="json") == before


def test_build_historical_dataset_assembly_reports_missing_replay_window_gap():
    payload = _assembly_payload()
    payload["replay_window_bundle"]["windows"] = []

    result = build_historical_dataset_assembly(build_input(payload))

    assert result.records == []
    assert any(gap.gap_category.value == "DATASET_MISSING_REPLAY_WINDOW" for gap in result.gap_report.gaps)


def test_build_historical_dataset_assembly_reports_missing_outcome_observation_gap():
    payload = _assembly_payload()
    payload["historical_outcome_observation_input"]["metric_sets"] = []

    result = build_historical_dataset_assembly(build_input(payload))

    assert result.records == []
    assert any(gap.gap_category.value == "DATASET_MISSING_OUTCOME_OBSERVATION" for gap in result.gap_report.gaps)


def test_build_historical_dataset_assembly_reports_missing_lineage_gap():
    payload = _assembly_payload()
    payload["replay_window_bundle"]["windows"][0]["source_manifest_ids"] = []

    result = build_historical_dataset_assembly(build_input(payload))

    assert any(gap.gap_category.value == "DATASET_SOURCE_LINEAGE_MISSING" for gap in result.gap_report.gaps)
    assert result.quality_report.missing_lineage_count == 1


def test_build_historical_dataset_assembly_detects_leakage_risk():
    payload = _assembly_payload()
    payload["scanner_replay_input"]["replay_context"]["attached_event_context_summary"] = "OUTCOME_FAVORABLE"

    result = build_historical_dataset_assembly(build_input(payload))

    assert result.records == []
    assert any(gap.gap_category.value == "DATASET_FEATURE_OUTCOME_LEAKAGE_DETECTED" for gap in result.gap_report.gaps)
    assert result.quality_report.leakage_risk_count == 1


def test_build_historical_dataset_assembly_generates_export_manifest():
    result = build_historical_dataset_assembly(build_input(_assembly_payload()))

    manifest = result.export_manifest
    assert manifest.record_count == 1
    assert manifest.symbol_count == 1
    assert manifest.market_count == 1
    assert manifest.feature_schema_version == "5.4-HISTORICAL-DATASET-FEATURE-BLOCK"
    assert manifest.outcome_schema_version == "5.4-HISTORICAL-DATASET-OUTCOME-BLOCK"
    assert manifest.quality_report_id == result.quality_report.quality_report_id
    assert manifest.gap_report_id == result.gap_report.gap_report_id
    assert manifest.safety_report_id == result.safety_report.safety_report_id


def test_historical_dataset_export_json_jsonl_and_csv_helpers(tmp_path):
    result = build_historical_dataset_assembly(build_input(_assembly_payload()))
    json_file = tmp_path / "dataset.json"
    jsonl_file = tmp_path / "dataset.jsonl"
    csv_file = tmp_path / "dataset.csv"

    export_historical_dataset_json(result, json_file)
    export_historical_dataset_jsonl(result, jsonl_file)
    export_historical_dataset_csv(result, csv_file)

    json_payload = json.loads(json_file.read_text(encoding="utf-8"))
    jsonl_lines = [json.loads(line) for line in jsonl_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    with csv_file.open("r", encoding="utf-8", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))

    assert json_payload["records"][0]["record_id"] == "DATASET-RECORD-1"
    assert len(jsonl_lines) == 1
    assert jsonl_lines[0]["record_id"] == "DATASET-RECORD-1"
    assert csv_rows[0]["record_id"] == "DATASET-RECORD-1"
    assert csv_rows[0]["feature_known_event_context_summary"] == "known-at-replay"


def test_historical_dataset_export_helpers_reject_parquet(tmp_path):
    result = build_historical_dataset_assembly(build_input(_assembly_payload()))

    with pytest.raises(ValueError, match="parquet"):
        export_historical_dataset_json(result, tmp_path / "dataset.parquet")
