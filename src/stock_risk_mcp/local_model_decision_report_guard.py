from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.local_model_benchmark_models import LocalModelBenchmarkReport
from stock_risk_mcp.local_model_decision_report_models import LocalModelBenchmarkPackFixture


def validate_pack_structure(pack: LocalModelBenchmarkPackFixture, pack_file: str | None = None) -> dict:
    base = Path(pack_file).resolve().parent if pack_file else None
    refs = [Path(item) if not base else (base / item) for item in pack.benchmark_report_files]
    exists = [ref.exists() for ref in refs]
    return {
        "report_count": len(refs),
        "all_reports_exist": all(exists),
        "unique_report_refs": len({str(ref) for ref in refs}) == len(refs),
        "required_language_tags": [item.value for item in pack.required_language_tags],
        "required_domain_tags": [item.value for item in pack.required_domain_tags],
    }


def extract_language_tags(report: LocalModelBenchmarkReport) -> set[str]:
    tags: set[str] = set()
    for item in report.evaluations:
        tags.update(item.audit_metadata.get("language_tags", []))
    return tags


def extract_domain_tags(report: LocalModelBenchmarkReport) -> set[str]:
    tags: set[str] = set()
    for item in report.evaluations:
        tags.update(item.audit_metadata.get("domain_tags", []))
    return tags


def coverage_complete(pack: LocalModelBenchmarkPackFixture, reports: list[LocalModelBenchmarkReport]) -> dict:
    language_tags: set[str] = set()
    domain_tags: set[str] = set()
    for report in reports:
        language_tags.update(extract_language_tags(report))
        domain_tags.update(extract_domain_tags(report))
    required_languages = {item.value for item in pack.required_language_tags}
    required_domains = {item.value for item in pack.required_domain_tags}
    return {
        "language_tags_present": sorted(language_tags),
        "domain_tags_present": sorted(domain_tags),
        "missing_language_tags": sorted(required_languages - language_tags),
        "missing_domain_tags": sorted(required_domains - domain_tags),
        "coverage_complete": required_languages.issubset(language_tags) and required_domains.issubset(domain_tags),
    }
