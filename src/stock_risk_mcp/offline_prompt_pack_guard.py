from __future__ import annotations

from stock_risk_mcp.offline_prompt_pack_models import (
    OFFLINE_PROMPT_PACK_METADATA,
    REQUIRED_PROFITABILITY_FIELDS,
    PromptPack,
    PromptPackReadinessStatus,
    PromptPackValidationIssue,
    PromptTaskContextClass,
)


def _issue(code: str, message: str, task_id: str | None = None) -> PromptPackValidationIssue:
    return PromptPackValidationIssue(code=code, message=message, task_id=task_id)


def _is_relative_local(path: str) -> bool:
    lowered = path.lower()
    return not (
        path.startswith("/")
        or "://" in path
        or lowered.startswith("cloud:")
        or lowered.startswith("app://")
    )


def validate_prompt_pack_structure(pack: PromptPack) -> list[PromptPackValidationIssue]:
    issues: list[PromptPackValidationIssue] = []
    seen_ids: set[str] = set()
    for task in pack.tasks:
        if task.task_id in seen_ids:
            issues.append(_issue("DUPLICATE_TASK_ID", "duplicate task_id detected", task.task_id))
        seen_ids.add(task.task_id)
        if not _is_relative_local(task.input_fixture_reference):
            issues.append(_issue("NON_DETERMINISTIC_INPUT_REFERENCE", "input_fixture_reference must be deterministic and local", task.task_id))
        if not _is_relative_local(task.scoring_rubric_reference):
            issues.append(_issue("NON_DETERMINISTIC_RUBRIC_REFERENCE", "scoring_rubric_reference must be deterministic and local", task.task_id))

        is_trading = task.task_context_class in {
            PromptTaskContextClass.TRACK_AWARE_ADVISORY,
            PromptTaskContextClass.TRACK_AWARE_PROFITABILITY_ADVISORY,
        }
        if is_trading and not task.supported_tracks:
            issues.append(_issue("TRADING_TASK_MISSING_SUPPORTED_TRACKS", "trading/advisory task must declare supported_tracks", task.task_id))
        if is_trading and len(task.supported_tracks) != 1:
            issues.append(_issue("AMBIGUOUS_TRACK_SUPPORT", "trading/advisory task must resolve to exactly one supported track", task.task_id))
        if is_trading and not task.requires_market_profile:
            issues.append(_issue("TRADING_TASK_MISSING_MARKET_PROFILE_REQUIREMENT", "trading/advisory task must require resolved MarketProfile", task.task_id))

        if task.task_context_class == PromptTaskContextClass.TRACK_AWARE_PROFITABILITY_ADVISORY:
            if not task.requires_profitability_context:
                issues.append(_issue("MISSING_PROFITABILITY_CONTEXT_REQUIREMENTS", "profitability advisory task must require profitability context", task.task_id))
            if not REQUIRED_PROFITABILITY_FIELDS.issubset(set(task.required_profitability_fields)):
                issues.append(_issue("MISSING_PROFITABILITY_CONTEXT_REQUIREMENTS", "profitability advisory task missing required v4.1 context fields", task.task_id))
            if not task.supports_report_only_mode:
                issues.append(_issue("REPORT_ONLY_MODE_REQUIRED", "profitability advisory task must declare report-only compatibility", task.task_id))
        if task.supports_report_only_mode and task.allows_actionable_output:
            issues.append(_issue("REPORT_ONLY_ACTIONABLE_OUTPUT_FORBIDDEN", "report-only or non-actionable profitability context must not allow actionable output", task.task_id))

        if len(task.supported_tracks) == 1:
            track = task.supported_tracks[0].value
            if track == "DOMESTIC_KR" and any(tag.startswith("OVERSEAS_") for tag in task.market_assumption_tags):
                issues.append(_issue("CROSS_TRACK_ASSUMPTION_LEAKAGE", "domestic task must not contain overseas assumption tags", task.task_id))
            if track == "OVERSEAS_US" and any(tag.startswith("DOMESTIC_") for tag in task.market_assumption_tags):
                issues.append(_issue("CROSS_TRACK_ASSUMPTION_LEAKAGE", "overseas task must not contain domestic assumption tags", task.task_id))

    boundary = pack.safety_boundary
    if boundary.order_intent_allowed:
        issues.append(_issue("ORDER_INTENT_FORBIDDEN", "order intent behavior is forbidden"))
    if boundary.order_draft_allowed:
        issues.append(_issue("ORDER_DRAFT_FORBIDDEN", "order draft behavior is forbidden"))
    if boundary.execution_approval_allowed:
        issues.append(_issue("EXECUTION_APPROVAL_FORBIDDEN", "execution approval is forbidden"))
    if boundary.live_prod_allowed:
        issues.append(_issue("LIVE_PROD_FORBIDDEN", "LIVE/PROD behavior is forbidden"))
    if boundary.broker_access_allowed:
        issues.append(_issue("BROKER_ACCESS_FORBIDDEN", "broker access is forbidden"))
    if boundary.account_access_allowed:
        issues.append(_issue("ACCOUNT_ACCESS_FORBIDDEN", "account access is forbidden"))
    if boundary.credential_access_allowed:
        issues.append(_issue("CREDENTIAL_ACCESS_FORBIDDEN", "credential access is forbidden"))
    if boundary.network_access_allowed:
        issues.append(_issue("NETWORK_ACCESS_FORBIDDEN", "network access is forbidden"))
    if boundary.cloud_llm_allowed:
        issues.append(_issue("CLOUD_LLM_FORBIDDEN", "cloud LLM behavior is forbidden"))
    if boundary.model_runtime_allowed:
        issues.append(_issue("MODEL_RUNTIME_FORBIDDEN", "local model runtime behavior is forbidden"))
    return issues


def readiness_from_issues(pack: PromptPack, issues: list[PromptPackValidationIssue]) -> PromptPackReadinessStatus:
    if issues:
        return PromptPackReadinessStatus.PACK_INVALID
    languages = {task.language.value for task in pack.tasks}
    if languages != {"KOREAN", "ENGLISH", "MIXED"}:
        return PromptPackReadinessStatus.PACK_VALID_WITH_GAPS
    return PromptPackReadinessStatus.PACK_READY_FOR_BENCHMARK_FEED
