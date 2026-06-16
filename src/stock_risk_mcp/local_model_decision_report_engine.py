from __future__ import annotations

from collections import defaultdict

from stock_risk_mcp.local_model_benchmark_models import BenchmarkEligibility, LocalModelBenchmarkReport
from stock_risk_mcp.local_model_decision_report_guard import coverage_complete, extract_domain_tags, extract_language_tags
from stock_risk_mcp.local_model_decision_report_models import (
    DecisionRecommendationStatus,
    LocalModelBackendDecisionReport,
    LocalModelBenchmarkPackFixture,
    LocalModelCandidatePackSummary,
    LocalModelDecisionRankingEntry,
    LocalModelReportTraceSummary,
)


HARD_FAILS = {
    BenchmarkEligibility.FAIL_SCHEMA,
    BenchmarkEligibility.FAIL_SAFETY,
    BenchmarkEligibility.FAIL_ADVISORY_BOUNDARY,
    BenchmarkEligibility.FAIL_EXECUTION_AUTHORITY_HALLUCINATION,
    BenchmarkEligibility.FAIL_REAL_MODEL_CALLED,
    BenchmarkEligibility.FAIL_EXTERNAL_NETWORK,
    BenchmarkEligibility.FAIL_CLOUD_BACKEND,
    BenchmarkEligibility.FAIL_MODEL_DOWNLOAD,
    BenchmarkEligibility.FAIL_UNSUPPORTED_BACKEND,
    BenchmarkEligibility.FAIL_MISSING_DATA_AWARENESS,
}


def _candidate_summary(candidate_model_id: str, evaluations_by_report: list[tuple[str, object]]) -> LocalModelCandidatePackSummary:
    report_count = len(evaluations_by_report)
    eligible_count = sum(item.eligibility_result == BenchmarkEligibility.ELIGIBLE for _, item in evaluations_by_report)
    hard_fail_evals = [(ref, item) for ref, item in evaluations_by_report if item.eligibility_result in HARD_FAILS]
    final_eligibility = BenchmarkEligibility.ELIGIBLE if not hard_fail_evals and report_count > 0 else (
        hard_fail_evals[0][1].eligibility_result if hard_fail_evals else BenchmarkEligibility.FAIL_SCHEMA
    )
    fail_reason_counts: dict[str, int] = defaultdict(int)
    per_domain: dict[str, list[float]] = defaultdict(list)
    per_language: dict[str, list[float]] = defaultdict(list)
    schema_scores = []
    safety_failures = 0
    advisory_failures = 0
    missing_data_success = 0
    parse_successes = 0
    overall_scores = []
    language_coverage: set[str] = set()
    domain_coverage: set[str] = set()
    for _, item in evaluations_by_report:
        overall_scores.append(item.overall_suitability_score)
        schema_scores.append(item.schema_validity_score)
        parse_successes += int(item.parse_success)
        missing_data_success += int(item.missing_data_awareness_score == 1.0)
        safety_failures += int(item.eligibility_result == BenchmarkEligibility.FAIL_SAFETY)
        advisory_failures += int(item.eligibility_result == BenchmarkEligibility.FAIL_ADVISORY_BOUNDARY)
        for reason in item.fail_gate_reasons:
            fail_reason_counts[reason] += 1
        for tag in item.audit_metadata.get("domain_tags", []):
            domain_coverage.add(tag)
            per_domain[tag].append(item.overall_suitability_score)
        for tag in item.audit_metadata.get("language_tags", []):
            language_coverage.add(tag)
            per_language[tag].append(item.overall_suitability_score)
    return LocalModelCandidatePackSummary(
        candidate_model_id=candidate_model_id,
        report_count_seen=report_count,
        eligible_report_count=eligible_count,
        hard_fail_count=len(hard_fail_evals),
        final_pack_eligibility=final_eligibility,
        eligibility_stability_across_reports=eligible_count / report_count if report_count else 0.0,
        average_overall_score=sum(overall_scores) / report_count if report_count else 0.0,
        per_domain_score={key: sum(vals) / len(vals) for key, vals in per_domain.items()},
        per_language_score={key: sum(vals) / len(vals) for key, vals in per_language.items()},
        schema_reliability=sum(schema_scores) / report_count if report_count else 0.0,
        safety_failure_rate=safety_failures / report_count if report_count else 0.0,
        advisory_boundary_failure_rate=advisory_failures / report_count if report_count else 0.0,
        missing_data_awareness_rate=missing_data_success / report_count if report_count else 0.0,
        json_parse_success_rate=parse_successes / report_count if report_count else 0.0,
        fail_reason_counts=dict(fail_reason_counts),
        language_coverage=sorted(language_coverage),
        domain_coverage=sorted(domain_coverage),
    )


def _trace_summary(report_ref: str, report: LocalModelBenchmarkReport) -> LocalModelReportTraceSummary:
    return LocalModelReportTraceSummary(
        report_ref=report_ref,
        run_id=report.run_id,
        language_tags=sorted(extract_language_tags(report)),
        domain_tags=sorted(extract_domain_tags(report)),
        candidate_eligibility_snapshot={item.candidate_model_id: item.eligibility_result.value for item in report.evaluations},
        top_candidate_ids=[item.candidate_model_id for item in report.rankings[:1]],
        failed_candidate_ids=[item.candidate_model_id for item in report.evaluations if item.eligibility_result != BenchmarkEligibility.ELIGIBLE],
    )


def _recommendation(pack: LocalModelBenchmarkPackFixture, summaries: list[LocalModelCandidatePackSummary], coverage: dict) -> DecisionRecommendationStatus:
    eligible = [item for item in summaries if item.final_pack_eligibility == BenchmarkEligibility.ELIGIBLE]
    if not eligible:
        return DecisionRecommendationStatus.NO_ELIGIBLE_BACKEND
    if len(pack.benchmark_report_files) < 2 or not coverage["coverage_complete"]:
        return DecisionRecommendationStatus.NEEDS_MORE_BENCHMARKS
    if max(item.average_overall_score for item in eligible) < 0.7:
        return DecisionRecommendationStatus.MOCK_ONLY_READY
    return DecisionRecommendationStatus.CANDIDATE_SHORTLIST_READY


def run_local_model_decision_report(
    pack: LocalModelBenchmarkPackFixture,
    reports: list[LocalModelBenchmarkReport],
    report_refs_by_run_id: dict[str, str],
) -> LocalModelBackendDecisionReport:
    candidate_reports: dict[str, list[tuple[str, object]]] = defaultdict(list)
    trace_reports = []
    for report in reports:
        trace_reports.append(_trace_summary(report_refs_by_run_id.get(report.run_id, report.run_id), report))
        for evaluation in report.evaluations:
            candidate_reports[evaluation.candidate_model_id].append((report.run_id, evaluation))
    summaries = [_candidate_summary(candidate_id, items) for candidate_id, items in candidate_reports.items()]
    coverage = coverage_complete(pack, reports)
    recommendation = _recommendation(pack, summaries, coverage)
    eligible = sorted(
        [item for item in summaries if item.final_pack_eligibility == BenchmarkEligibility.ELIGIBLE],
        key=lambda item: (-item.average_overall_score, item.candidate_model_id),
    )
    rankings = [
        LocalModelDecisionRankingEntry(
            rank=index + 1,
            candidate_model_id=item.candidate_model_id,
            average_overall_score=item.average_overall_score,
            final_pack_eligibility=item.final_pack_eligibility,
        )
        for index, item in enumerate(eligible)
    ]
    shortlisted = [item.model_dump(mode="json") for item in eligible if recommendation == DecisionRecommendationStatus.CANDIDATE_SHORTLIST_READY]
    rejected = [item.model_dump(mode="json") for item in summaries if item.final_pack_eligibility != BenchmarkEligibility.ELIGIBLE]
    return LocalModelBackendDecisionReport(
        pack_id=pack.pack_id,
        report_count=len(reports),
        candidate_count=len(summaries),
        eligible_candidate_count=len(eligible),
        recommendation_status=recommendation,
        shortlisted_candidates=shortlisted,
        rejected_candidates=rejected,
        trace_reports=trace_reports,
        coverage_summary=coverage,
        aggregation_summary={
            "ranked_candidates": [item.model_dump(mode="json") for item in rankings],
            "candidate_summaries": [item.model_dump(mode="json") for item in summaries],
        },
        created_at=pack.created_at,
    )
