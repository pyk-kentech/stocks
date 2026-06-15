from __future__ import annotations

import hashlib
from pathlib import Path

from stock_risk_mcp.llm_feature_fixture import load_llm_outcome_fixture, load_llm_signal_fixture
from stock_risk_mcp.llm_feature_models import LLMSignalEvaluationReport
from stock_risk_mcp.llm_signal_evaluation import build_feature_store_result, evaluate_llm_signals
from stock_risk_mcp.repository import RiskRepository


def _checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_feature_store(signal_fixture_file, db_path=None, output_file=None):
    fixture = load_llm_signal_fixture(signal_fixture_file)
    result = build_feature_store_result(fixture, _checksum(signal_fixture_file))
    if db_path:
        repository = RiskRepository(db_path)
        repository.save_llm_prompt_version(fixture.prompt_version)
        repository.save_llm_model_version(fixture.model_version, fixture.created_at)
        repository.save_llm_feature_store_result(result, fixture.created_at)
    if output_file:
        Path(output_file).write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result


def run_signal_evaluation(signal_fixture_file, outcome_fixture_file, db_path=None, output_file=None):
    signals = load_llm_signal_fixture(signal_fixture_file)
    outcomes = load_llm_outcome_fixture(outcome_fixture_file)
    report = evaluate_llm_signals(signals, outcomes, _checksum(signal_fixture_file), _checksum(outcome_fixture_file))
    if db_path:
        repository = RiskRepository(db_path)
        repository.save_llm_prompt_version(signals.prompt_version)
        repository.save_llm_model_version(signals.model_version, signals.created_at)
        repository.save_llm_signal_evaluations(signals.run_id, report.evaluations, outcomes.created_at)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def load_llm_signal_evaluation_report(path):
    try:
        return LLMSignalEvaluationReport.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid LLM signal evaluation report: {exc}") from exc
