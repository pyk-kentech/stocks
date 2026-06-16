from __future__ import annotations

from stock_risk_mcp.local_llm_advisory_guard import detect_unsafe_output
from stock_risk_mcp.local_llm_advisory_models import AdvisoryBackendType, AdvisoryResultStatus, LocalLLMAdvisoryFixture, LocalLLMAdvisoryResult


def run_local_llm_advisory_fixture(fixture: LocalLLMAdvisoryFixture, fixture_checksum: str) -> LocalLLMAdvisoryResult:
    if fixture.backend.backend_type == AdvisoryBackendType.DISABLED:
        return LocalLLMAdvisoryResult(
            fixture_checksum=fixture_checksum,
            run_id=fixture.run_id,
            created_at=fixture.created_at,
            task_type=fixture.task_type,
            backend_type=fixture.backend.backend_type,
            status=AdvisoryResultStatus.BACKEND_DISABLED,
            refusal_reason="local advisory backend disabled",
        )
    summary_text, bullet_points, risk_classification, missing_items, challenges = build_advisory_payload(fixture)
    unsafe_reason = detect_unsafe_output("\n".join([summary_text or "", *bullet_points, *missing_items, *challenges]))
    if unsafe_reason:
        return LocalLLMAdvisoryResult(
            fixture_checksum=fixture_checksum,
            run_id=fixture.run_id,
            created_at=fixture.created_at,
            task_type=fixture.task_type,
            backend_type=fixture.backend.backend_type,
            status=AdvisoryResultStatus.UNSAFE_OUTPUT_REJECTED,
            refusal_reason=unsafe_reason,
        )
    return LocalLLMAdvisoryResult(
        fixture_checksum=fixture_checksum,
        run_id=fixture.run_id,
        created_at=fixture.created_at,
        task_type=fixture.task_type,
        backend_type=fixture.backend.backend_type,
        status=AdvisoryResultStatus.ADVISORY_RESPONSE,
        summary_text=summary_text,
        bullet_points=bullet_points,
        risk_language_classification=risk_classification,
        missing_data_items=missing_items,
        challenge_points=challenges,
    )


def build_advisory_payload(fixture: LocalLLMAdvisoryFixture):
    texts = fixture.inputs.text_blocks
    if fixture.task_type.value == "SUMMARIZE_TECHNICAL_EVIDENCE":
        return f"Technical evidence summary for {fixture.inputs.ticker or 'UNKNOWN'}", texts[:3], None, [], []
    if fixture.task_type.value == "SUMMARIZE_MARKET_DISCOVERY":
        return "Market discovery evidence summary", texts[:3], None, [], []
    if fixture.task_type.value == "SUMMARIZE_LLM_SIGNAL_EVALUATION":
        return "LLM signal evaluation summary", texts[:3], None, [], []
    if fixture.task_type.value == "EXPLAIN_TRADE_PLAN_RISK":
        return "Trade plan risk explanation", texts[:3], None, [], []
    if fixture.task_type.value == "CHALLENGE_WEAK_ASSUMPTIONS":
        return "Weak assumptions identified", [], None, [], [f"Challenge: {text}" for text in texts[:3]]
    if fixture.task_type.value == "LIST_MISSING_DATA":
        return "Missing data checklist", [], None, [f"Missing data: {text}" for text in texts[:3]], []
    if fixture.task_type.value == "CLASSIFY_ADVISORY_RISK_LANGUAGE":
        classification = "HIGH_RISK_LANGUAGE" if any(term in " ".join(texts).lower() for term in ("uncertain", "volatile", "risk")) else "LOW_RISK_LANGUAGE"
        return "Advisory risk language classification", texts[:3], classification, [], []
    return "Unsupported advisory task", [], None, [], []
