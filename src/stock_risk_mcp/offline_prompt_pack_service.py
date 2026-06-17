from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.offline_prompt_pack_engine import (
    build_prompt_pack_coverage_report,
    build_prompt_pack_gap_report,
    validate_prompt_pack,
)
from stock_risk_mcp.offline_prompt_pack_fixture import load_offline_prompt_pack_fixture
from stock_risk_mcp.offline_prompt_pack_models import (
    PromptPackGapReport,
    PromptPackValidationReport,
    PromptTaskCoverageReport,
)


def run_prompt_pack_validate(fixture_file, output_file=None):
    pack = load_offline_prompt_pack_fixture(fixture_file)
    report = validate_prompt_pack(pack)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_prompt_pack_show(fixture_file):
    return load_offline_prompt_pack_fixture(fixture_file)


def run_prompt_pack_coverage_report(fixture_file, output_file=None):
    pack = load_offline_prompt_pack_fixture(fixture_file)
    report = build_prompt_pack_coverage_report(pack, validate_prompt_pack(pack))
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def run_prompt_pack_gap_report(fixture_file, output_file=None):
    pack = load_offline_prompt_pack_fixture(fixture_file)
    report = build_prompt_pack_gap_report(pack, validate_prompt_pack(pack))
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def load_prompt_pack_validation_report(path):
    try:
        return PromptPackValidationReport.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid prompt pack validation report: {exc}") from exc


def load_prompt_pack_coverage_report(path):
    try:
        return PromptTaskCoverageReport.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid prompt pack coverage report: {exc}") from exc


def load_prompt_pack_gap_report(path):
    try:
        return PromptPackGapReport.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid prompt pack gap report: {exc}") from exc
