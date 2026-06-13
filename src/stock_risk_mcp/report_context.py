from __future__ import annotations

from stock_risk_mcp.candidate_universe import CandidateDecision
from stock_risk_mcp.pipeline_run import AlertSeverity
from stock_risk_mcp.report_templates import suggested_questions


def pipeline_context(repository, pipeline_run_id: str, language: str = "en") -> dict:
    run = repository.get_pipeline_run(pipeline_run_id)
    rank = {AlertSeverity.CRITICAL: 4, AlertSeverity.HIGH: 3, AlertSeverity.WARNING: 2, AlertSeverity.INFO: 1}
    alerts = sorted(repository.list_pipeline_alerts(pipeline_run_id), key=lambda item: rank[item.severity], reverse=True)
    context = {
        "source_type": "pipeline_run", "source_id": pipeline_run_id,
        "pipeline_run": run.model_dump(mode="json"), "alerts": [item.model_dump(mode="json") for item in alerts],
        "metrics": {
            "status": run.status.value, "candidate_count": run.candidate_count, "included_count": run.included_count,
            "watch_count": run.watch_count, "basket_allocation_count": run.basket_allocation_count,
            "alert_count": len(alerts),
        },
        "warnings": [*run.notes, *([run.error] if run.error else [])],
        "suggested_questions_for_llm": suggested_questions(language),
    }
    if run.scan_run_id:
        context["scan"] = scan_context(repository, run.scan_run_id, language)
    if run.basket_id:
        try:
            context["basket"] = basket_context(repository, run.basket_id, language)
        except LookupError:
            context["warnings"].append(f"Linked basket was not found: {run.basket_id}")
        paper_result = repository.get_basket_backtest_result(run.basket_id)
        if paper_result is not None:
            context["paper_result"] = paper_result.model_dump(mode="json")
    if run.evaluation_suite_id:
        context["policy_evaluation"] = policy_context(repository, run.evaluation_suite_id, language)
    return context


def scan_context(repository, scan_run_id: str, language: str = "en") -> dict:
    run = repository.get_scan_run(scan_run_id)
    results = repository.list_candidate_scan_results(scan_run_id)
    top = sorted(
        [item for item in results if item.decision == CandidateDecision.INCLUDE],
        key=lambda item: item.score, reverse=True,
    )[:10]
    warning_candidates = [
        {"ticker": item.ticker, "decision": item.decision.value, "warnings": item.warnings}
        for item in results if item.warnings
    ]
    return {
        "source_type": "scan_run", "source_id": scan_run_id, "scan_run": run.model_dump(mode="json"),
        "metrics": {
            "universe_size": run.universe_size, "included_count": run.included_count,
            "watch_count": run.watch_count, "excluded_count": run.excluded_count,
        },
        "top_candidates": [item.model_dump(mode="json") for item in top],
        "warning_candidates": warning_candidates,
        "signal_enrichment": [
            {"ticker": item.ticker, **item.metadata["signal_enrichment"]}
            for item in results if "signal_enrichment" in item.metadata
        ],
        "warnings": run.notes,
        "suggested_questions_for_llm": suggested_questions(language),
    }


def basket_context(repository, basket_id: str, language: str = "en") -> dict:
    try:
        basket = repository.get_basket_plan(basket_id)
        payload = basket.model_dump(mode="json")
        warnings = list(basket.risk_summary.warnings)
        official = True
    except LookupError:
        snapshot = repository.get_replay_basket_snapshot_by_basket_id(basket_id)
        if snapshot is None:
            raise LookupError(f"Basket not found: {basket_id}")
        payload = snapshot.snapshot_json
        warnings = ["This may be a replay-only basket that is not stored in basket_plans."]
        official = False
    allocations = payload.get("allocations", [])
    blocked = payload.get("blocked", [])
    risk = payload.get("risk_summary", {})
    return {
        "source_type": "basket_plan" if official else "replay_basket_snapshot", "source_id": basket_id,
        "basket": payload, "allocations": allocations, "blocked_candidates": blocked,
        "metrics": {
            "decision": payload.get("decision"), "allocation_count": len(allocations),
            "blocked_count": len(blocked), "total_allocated_loss": risk.get("total_allocated_loss"),
            "total_notional_value": risk.get("total_notional_value"),
        },
        "warnings": warnings, "suggested_questions_for_llm": suggested_questions(language),
    }


def policy_context(repository, suite_id: str, language: str = "en") -> dict:
    suite = repository.get_policy_evaluation_suite(suite_id)
    return {
        "source_type": "policy_evaluation_suite", "source_id": suite_id,
        "suite": suite.model_dump(mode="json"),
        "metrics": {
            "objective_delta": suite.objective_delta, "return_delta_pct": suite.return_delta_pct,
            "win_rate_delta": suite.win_rate_delta, "recommendation": suite.recommendation.value,
            "completed_pair_count": suite.completed_pair_count, "no_data_rate": suite.no_data_rate,
        },
        "warnings": [*suite.notes, "Policy recommendation does not approve or activate a policy."],
        "suggested_questions_for_llm": suggested_questions(language),
    }
