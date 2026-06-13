from datetime import date, datetime

from stock_risk_mcp.analysis_report import (
    build_candidate_scan_report, build_pipeline_summary_report, build_policy_evaluation_report,
)
from stock_risk_mcp.candidate_universe import CandidateDecision, CandidateScanResult, CandidateSource, ScanRun, ScanRunStatus
from stock_risk_mcp.pipeline_run import AlertSeverity, AlertType, PipelineAlert, PipelineMode, PipelineRun, PipelineRunStatus
from stock_risk_mcp.models import BacktestOutcome
from stock_risk_mcp.paper_trading import BasketBacktestResult
from stock_risk_mcp.policy_evaluation_suite import PolicyEvaluationDecision, PolicyEvaluationSuiteResult
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.replay_snapshot import ReplayBasketSnapshot
from stock_risk_mcp.analysis_report import build_basket_plan_report


def test_pipeline_and_scan_reports_include_stored_evidence(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    scan = ScanRun(
        scan_run_id="scan-1", as_of_date=date(2026, 6, 13), source=CandidateSource.MANUAL_LIST,
        universe_size=2, included_count=1, watch_count=0, excluded_count=1,
        status=ScanRunStatus.COMPLETED, created_at=datetime(2026, 6, 13),
    )
    repository.save_scan_run(scan)
    repository.save_candidate_scan_results([
        CandidateScanResult(scan_run_id="scan-1", ticker="AAA", as_of_date=scan.as_of_date, decision=CandidateDecision.INCLUDE, score=90, metadata={"signal_enrichment": {"total_score_delta": 5}}),
        CandidateScanResult(scan_run_id="scan-1", ticker="BBB", as_of_date=scan.as_of_date, decision=CandidateDecision.EXCLUDE, score=10, warnings=["Critical dilution warning"]),
    ])
    run = PipelineRun(
        pipeline_run_id="pipe-1", mode=PipelineMode.SCAN_ONLY, as_of_date=scan.as_of_date,
        scan_run_id="scan-1", basket_id="basket-paper", status=PipelineRunStatus.COMPLETED, candidate_count=2,
        included_count=1, watch_count=0, basket_allocation_count=0, alert_count=1,
        created_at=datetime(2026, 6, 13),
    )
    repository.save_pipeline_run(run)
    repository.save_basket_backtest_result(BasketBacktestResult(
        basket_id="basket-paper", horizon_days=10, entry_date=date(2026, 6, 13),
        total_notional_value=1000, total_allocated_loss=10, realized_pnl=50, realized_return_pct=5,
        win_count=1, loss_count=0, flat_count=0, no_data_count=0, closed_trade_count=1,
        outcome=BacktestOutcome.WIN, created_at=datetime(2026, 6, 13),
    ))
    repository.save_pipeline_alerts([PipelineAlert(
        alert_id="alert-1", pipeline_run_id="pipe-1", alert_type=AlertType.SIGNAL_CRITICAL,
        severity=AlertSeverity.CRITICAL, ticker="BBB", title="Risk", message="Critical signal",
        created_at=datetime(2026, 6, 13),
    )])

    pipeline_report = build_pipeline_summary_report(repository, "pipe-1")
    scan_report = build_candidate_scan_report(repository, "scan-1")

    assert pipeline_report.context_json["alerts"][0]["severity"] == "CRITICAL"
    assert pipeline_report.context_json["paper_result"]["realized_return_pct"] == 5
    assert scan_report.key_metrics["included_count"] == 1
    assert scan_report.context_json["top_candidates"][0]["ticker"] == "AAA"
    assert build_pipeline_summary_report(repository, "pipe-1", "ko").title == "파이프라인 요약 보고서"


def test_policy_report_contains_delta_recommendation_and_status_warning(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    suite = PolicyEvaluationSuiteResult(
        suite_id="suite-1", baseline_policy_id="base", baseline_policy_version="v1",
        candidate_policy_id="candidate", candidate_policy_version="v2", replay_run_count=5,
        completed_pair_count=5, no_data_replay_count=0, incomplete_pair_count=0,
        objective_delta=6, return_delta_pct=2, win_rate_delta=0.1, no_data_rate=0,
        recommendation=PolicyEvaluationDecision.ACCEPT, created_at=datetime(2026, 6, 13),
    )
    repository.save_policy_evaluation_suite(suite)

    report = build_policy_evaluation_report(repository, "suite-1")

    assert report.key_metrics["objective_delta"] == 6
    assert report.key_metrics["recommendation"] == "ACCEPT"
    assert any("does not approve or activate" in warning for warning in report.warnings)


def test_basket_report_uses_replay_snapshot_and_warns_when_not_official(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    repository.save_replay_basket_snapshot(ReplayBasketSnapshot(
        run_id="replay-1", basket_id="replay-basket", decision="REVIEW", scoring_mode="FIXED_RULES",
        snapshot_json={
            "basket_id": "replay-basket", "decision": "REVIEW",
            "allocations": [{"ticker": "AAA"}], "blocked": [{"ticker": "BBB"}],
            "risk_summary": {"total_allocated_loss": 10, "total_notional_value": 1000},
        },
    ))

    report = build_basket_plan_report(repository, "replay-basket")

    assert report.key_metrics["allocation_count"] == 1
    assert report.key_metrics["blocked_count"] == 1
    assert any("replay-only" in warning for warning in report.warnings)
