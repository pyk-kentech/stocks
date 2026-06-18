from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.historical_data_engine import (
    build_historical_data_gap_report,
    build_historical_data_manifest,
    build_historical_data_quality_report,
    build_historical_data_validation_report,
    parse_historical_data_records,
)
from stock_risk_mcp.historical_data_fixture import load_historical_data_fixture


def _build_historical_data_reports(fixture):
    records, parse_issues = parse_historical_data_records(
        fixture.source_descriptor,
        ingestion_batch_id=fixture.ingestion_batch_id,
    )
    validation = build_historical_data_validation_report(
        ingestion_config=fixture.ingestion_config,
        source_descriptor=fixture.source_descriptor,
        records=records,
        parse_issues=parse_issues,
        ingestion_batch_id=fixture.ingestion_batch_id,
    )
    quality = build_historical_data_quality_report(
        ingestion_batch_id=fixture.ingestion_batch_id,
        records=records,
        validation_report=validation,
        adjustment_policy=fixture.adjustment_policy,
    )
    gap = build_historical_data_gap_report(
        ingestion_config=fixture.ingestion_config,
        validation_report=validation,
        quality_report=quality,
        ingestion_batch_id=fixture.ingestion_batch_id,
    )
    manifest = build_historical_data_manifest(
        ingestion_config=fixture.ingestion_config,
        source_descriptor=fixture.source_descriptor,
        provider_provenance=fixture.provider_provenance,
        adjustment_policy=fixture.adjustment_policy,
        records=records,
        validation_report=validation,
        quality_report=quality,
        gap_report=gap,
        audit_record_ids=fixture.audit_record_ids,
    )
    return validation, quality, gap, manifest


def run_historical_data_config_validate(fixture_file):
    return load_historical_data_fixture(fixture_file)


def run_historical_data_validate(fixture_file, output_file=None):
    fixture = load_historical_data_fixture(fixture_file)
    validation, _, _, _ = _build_historical_data_reports(fixture)
    if output_file:
        Path(output_file).write_text(validation.model_dump_json(indent=2), encoding="utf-8")
    return validation


def run_historical_data_quality_report(fixture_file, output_file=None):
    fixture = load_historical_data_fixture(fixture_file)
    _, quality, _, _ = _build_historical_data_reports(fixture)
    if output_file:
        Path(output_file).write_text(quality.model_dump_json(indent=2), encoding="utf-8")
    return quality


def run_historical_data_gap_report(fixture_file, output_file=None):
    fixture = load_historical_data_fixture(fixture_file)
    _, _, gap, _ = _build_historical_data_reports(fixture)
    if output_file:
        Path(output_file).write_text(gap.model_dump_json(indent=2), encoding="utf-8")
    return gap


def run_historical_data_manifest_build(fixture_file, output_file=None):
    fixture = load_historical_data_fixture(fixture_file)
    _, _, _, manifest = _build_historical_data_reports(fixture)
    if output_file:
        Path(output_file).write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return manifest
