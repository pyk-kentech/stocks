from stock_risk_mcp.local_model_decision_report_engine import run_local_model_decision_report
from stock_risk_mcp.local_model_decision_report_models import LocalModelBenchmarkPackFixture
from stock_risk_mcp.local_model_benchmark_models import LocalModelBenchmarkReport
from tests.test_local_model_decision_report_fixture import benchmark_pack_fixture_payload, benchmark_report_payload


def pack_fixture(value=None):
    return LocalModelBenchmarkPackFixture.model_validate(value or benchmark_pack_fixture_payload())


def report(value):
    return LocalModelBenchmarkReport.model_validate(value)


def test_pack_level_aggregation_can_shortlist_only_with_full_coverage():
    reports = [
        report(benchmark_report_payload("ko", language_tags=["KOREAN"], domain_tags=["TECHNICAL_EVIDENCE"], overall_score=0.82)),
        report(benchmark_report_payload("en", language_tags=["ENGLISH"], domain_tags=["RISK_EXPLANATION"], overall_score=0.84)),
        report(benchmark_report_payload("mixed", language_tags=["MIXED"], domain_tags=["MISSING_DATA", "ASSUMPTION_CHALLENGE"], overall_score=0.86)),
    ]
    decision = run_local_model_decision_report(pack_fixture(), reports, {"ko": "ko", "en": "en", "mixed": "mixed"})
    assert decision.recommendation_status == "CANDIDATE_SHORTLIST_READY"
    assert decision.eligible_candidate_count == 1
    assert decision.shortlisted_candidates[0]["candidate_model_id"] == "mock-qwen-7b-q4"


def test_single_report_is_not_enough_to_recommend_backend():
    reports = [report(benchmark_report_payload("only", language_tags=["KOREAN"], domain_tags=["TECHNICAL_EVIDENCE"], overall_score=0.9))]
    decision = run_local_model_decision_report(pack_fixture(benchmark_pack_fixture_payload(report_files=["only.json"])), reports, {"only": "only.json"})
    assert decision.recommendation_status == "NEEDS_MORE_BENCHMARKS"


def test_hard_fail_persistence_keeps_candidate_ineligible():
    reports = [
        report(benchmark_report_payload("ko", language_tags=["KOREAN"], domain_tags=["TECHNICAL_EVIDENCE"])),
        report(benchmark_report_payload("en", eligibility_result="FAIL_SAFETY", language_tags=["ENGLISH"], domain_tags=["RISK_EXPLANATION"], overall_score=0.95)),
        report(benchmark_report_payload("mixed", language_tags=["MIXED"], domain_tags=["MISSING_DATA", "ASSUMPTION_CHALLENGE"])),
    ]
    decision = run_local_model_decision_report(pack_fixture(), reports, {"ko": "ko", "en": "en", "mixed": "mixed"})
    assert decision.recommendation_status == "NO_ELIGIBLE_BACKEND"
    assert decision.shortlisted_candidates == []
    assert decision.rejected_candidates[0]["final_pack_eligibility"] == "FAIL_SAFETY"


def test_no_loose_majority_voting():
    reports = [
        report(benchmark_report_payload("ko", language_tags=["KOREAN"], domain_tags=["TECHNICAL_EVIDENCE"])),
        report(benchmark_report_payload("en", language_tags=["ENGLISH"], domain_tags=["RISK_EXPLANATION"])),
        report(benchmark_report_payload("mixed", eligibility_result="FAIL_ADVISORY_BOUNDARY", language_tags=["MIXED"], domain_tags=["MISSING_DATA", "ASSUMPTION_CHALLENGE"], overall_score=0.99)),
    ]
    decision = run_local_model_decision_report(pack_fixture(), reports, {"ko": "ko", "en": "en", "mixed": "mixed"})
    assert decision.recommendation_status == "NO_ELIGIBLE_BACKEND"


def test_supporting_evidence_includes_single_report_summaries_and_failed_candidates():
    reports = [
        report(benchmark_report_payload("ko", language_tags=["KOREAN"], domain_tags=["TECHNICAL_EVIDENCE"])),
        report(benchmark_report_payload("en", eligibility_result="FAIL_MISSING_DATA_AWARENESS", language_tags=["ENGLISH"], domain_tags=["RISK_EXPLANATION"], overall_score=0.75)),
        report(benchmark_report_payload("mixed", language_tags=["MIXED"], domain_tags=["MISSING_DATA", "ASSUMPTION_CHALLENGE"])),
    ]
    decision = run_local_model_decision_report(pack_fixture(), reports, {"ko": "ko", "en": "en", "mixed": "mixed"})
    assert len(decision.trace_reports) == 3
    assert decision.rejected_candidates[0]["candidate_model_id"] == "mock-qwen-7b-q4"


def test_mock_only_ready_when_safe_but_not_shortlist_ready():
    reports = [
        report(benchmark_report_payload("ko", language_tags=["KOREAN"], domain_tags=["TECHNICAL_EVIDENCE"], overall_score=0.65)),
        report(benchmark_report_payload("en", language_tags=["ENGLISH"], domain_tags=["RISK_EXPLANATION"], overall_score=0.66)),
        report(benchmark_report_payload("mixed", language_tags=["MIXED"], domain_tags=["MISSING_DATA", "ASSUMPTION_CHALLENGE"], overall_score=0.67)),
    ]
    decision = run_local_model_decision_report(pack_fixture(), reports, {"ko": "ko", "en": "en", "mixed": "mixed"})
    assert decision.recommendation_status == "MOCK_ONLY_READY"
