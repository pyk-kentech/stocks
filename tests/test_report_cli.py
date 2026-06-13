import json
from datetime import date, datetime

from stock_risk_mcp.cli import main
from stock_risk_mcp.pipeline_run import PipelineMode, PipelineRun, PipelineRunStatus
from stock_risk_mcp.candidate_universe import CandidateSource, ScanRun, ScanRunStatus
from stock_risk_mcp.policy_evaluation_suite import PolicyEvaluationDecision, PolicyEvaluationSuiteResult
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.replay_snapshot import ReplayBasketSnapshot


def test_report_cli_output_file_success_and_optional_save(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    _save_pipeline(db)
    output = tmp_path / "pipeline.md"

    result = _run(capsys, [
        "report-pipeline", "--db", str(db), "--pipeline-run-id", "pipe-1",
        "--format", "markdown", "--output-file", str(output), "--save",
    ])

    assert output.exists()
    assert result["output_file_requested"] is True
    assert result["output_file_saved"] is True
    assert result["output_file_error"] is None
    assert RiskRepository(db).count_rows("analysis_reports") == 1


def test_report_cli_output_file_failure_warns_and_saves_only_when_requested(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    _save_pipeline(db)
    invalid_output = tmp_path / "directory"
    invalid_output.mkdir()

    unsaved = _run(capsys, [
        "report-pipeline", "--db", str(db), "--pipeline-run-id", "pipe-1",
        "--format", "json", "--output-file", str(invalid_output),
    ])
    saved = _run(capsys, [
        "report-pipeline", "--db", str(db), "--pipeline-run-id", "pipe-1",
        "--format", "json", "--output-file", str(invalid_output), "--save",
    ])

    assert unsaved["output_file_saved"] is False
    assert unsaved["output_file_error"]
    assert any("failed to write output file" in warning for warning in unsaved["report"]["warnings"])
    assert RiskRepository(db).count_rows("analysis_reports") == 1
    stored = RiskRepository(db).list_analysis_reports()[0]
    assert any("failed to write output file" in warning for warning in stored.warnings)
    assert saved["saved_to_analysis_reports"] is True


def test_scan_basket_policy_and_saved_report_cli_commands(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    repository = RiskRepository(db)
    repository.save_scan_run(ScanRun(
        scan_run_id="scan-1", as_of_date=date(2026, 6, 13), source=CandidateSource.MANUAL_LIST,
        universe_size=0, included_count=0, watch_count=0, excluded_count=0,
        status=ScanRunStatus.COMPLETED, created_at=datetime(2026, 6, 13),
    ))
    repository.save_replay_basket_snapshot(ReplayBasketSnapshot(
        run_id="replay-1", basket_id="basket-1", decision="REVIEW", scoring_mode="FIXED_RULES",
        snapshot_json={"basket_id": "basket-1", "decision": "REVIEW", "allocations": [], "blocked": [], "risk_summary": {}},
    ))
    repository.save_policy_evaluation_suite(PolicyEvaluationSuiteResult(
        suite_id="suite-1", baseline_policy_id="base", baseline_policy_version="v1",
        candidate_policy_id="candidate", candidate_policy_version="v2", replay_run_count=0,
        completed_pair_count=0, no_data_replay_count=0, incomplete_pair_count=0, no_data_rate=0,
        recommendation=PolicyEvaluationDecision.NEED_MORE_DATA, created_at=datetime(2026, 6, 13),
    ))

    scan = _run(capsys, ["report-scan", "--db", str(db), "--scan-run-id", "scan-1"])
    basket = _run(capsys, ["report-basket", "--db", str(db), "--basket-id", "basket-1"])
    policy = _run(capsys, ["report-policy-suite", "--db", str(db), "--suite-id", "suite-1", "--save"])
    reports = _run(capsys, ["reports", "--db", str(db)])
    shown = _run(capsys, ["report-show", "--db", str(db), "--report-id", policy["report"]["report_id"]])

    assert scan["report"]["report_type"] == "CANDIDATE_SCAN"
    assert basket["report"]["report_type"] == "BASKET_PLAN"
    assert policy["report"]["report_type"] == "POLICY_EVALUATION"
    assert reports["reports"]
    assert shown["report_id"] == policy["report"]["report_id"]


def _save_pipeline(db):
    RiskRepository(db).save_pipeline_run(PipelineRun(
        pipeline_run_id="pipe-1", mode=PipelineMode.SCAN_ONLY, as_of_date=date(2026, 6, 13),
        status=PipelineRunStatus.COMPLETED, candidate_count=0, included_count=0, watch_count=0,
        basket_allocation_count=0, alert_count=0, created_at=datetime(2026, 6, 13),
    ))


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)
