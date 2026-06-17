from __future__ import annotations

from collections import Counter

from stock_risk_mcp.offline_prompt_pack_guard import readiness_from_issues, validate_prompt_pack_structure
from stock_risk_mcp.offline_prompt_pack_models import (
    PromptPack,
    PromptPackGapReport,
    PromptPackReadinessStatus,
    PromptPackValidationReport,
    PromptTaskCoverageReport,
)


def validate_prompt_pack(pack: PromptPack) -> PromptPackValidationReport:
    issues = validate_prompt_pack_structure(pack)
    readiness = readiness_from_issues(pack, issues)
    return PromptPackValidationReport(
        prompt_pack_id=pack.prompt_pack_id,
        valid=not issues,
        readiness_status=readiness,
        issues=issues,
        summary={
            "task_count": len(pack.tasks),
            "issue_count": len(issues),
        },
    )


def build_prompt_pack_coverage_report(pack: PromptPack, validation: PromptPackValidationReport | None = None) -> PromptTaskCoverageReport:
    type_counts = Counter(task.task_type.value for task in pack.tasks)
    language_counts = Counter(task.language.value for task in pack.tasks)
    domain_counts = Counter(task.domain.value for task in pack.tasks)
    trap_counts = Counter(tag.value for task in pack.tasks for tag in task.safety_trap_tags)
    tracks = sorted({track.value for task in pack.tasks for track in task.supported_tracks})
    return PromptTaskCoverageReport(
        prompt_pack_id=pack.prompt_pack_id,
        total_task_count=len(pack.tasks),
        task_count_by_type=dict(type_counts),
        task_count_by_language=dict(language_counts),
        task_count_by_domain=dict(domain_counts),
        safety_trap_count_by_tag=dict(trap_counts),
        supported_tracks_seen=tracks,
    )


def build_prompt_pack_gap_report(pack: PromptPack, validation: PromptPackValidationReport | None = None) -> PromptPackGapReport:
    validation = validation or validate_prompt_pack(pack)
    coverage = build_prompt_pack_coverage_report(pack, validation)
    missing_languages = [name for name in ("KOREAN", "ENGLISH", "MIXED") if coverage.task_count_by_language.get(name, 0) == 0]
    missing_traps = [
        name
        for name in (
            "UNSAFE_INSTRUCTION_REJECTION",
            "ADVISORY_BOUNDARY_REFUSAL",
        )
        if coverage.safety_trap_count_by_tag.get(name, 0) == 0
    ]
    return PromptPackGapReport(
        prompt_pack_id=pack.prompt_pack_id,
        validation_passed=validation.valid,
        readiness_status=validation.readiness_status if not missing_languages and not missing_traps and validation.valid else (
            PromptPackReadinessStatus.PACK_VALID_WITH_GAPS if validation.valid else PromptPackReadinessStatus.PACK_INVALID
        ),
        missing_language_coverage=missing_languages,
        missing_domain_coverage=[],
        missing_safety_trap_coverage=missing_traps,
        issues=[issue.model_dump(mode="json") for issue in validation.issues],
    )
