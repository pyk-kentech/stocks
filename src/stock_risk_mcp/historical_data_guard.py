from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.historical_data_models import HistoricalDataSourceDescriptor, HistoricalDataSourceType, HistoricalGapCategory


def build_historical_data_issue(
    category: HistoricalGapCategory,
    message: str,
    *,
    row_number: int | None = None,
    field_name: str | None = None,
) -> dict[str, object]:
    issue: dict[str, object] = {
        "category": category.value,
        "message": message,
    }
    if row_number is not None:
        issue["row_number"] = row_number
    if field_name is not None:
        issue["field_name"] = field_name
    return issue


def validate_historical_data_source_path(
    source_descriptor: HistoricalDataSourceDescriptor,
) -> tuple[Path | None, list[dict[str, object]]]:
    issues: list[dict[str, object]] = []
    local_file_path = source_descriptor.local_file_path.strip()
    lowered = local_file_path.lower()

    if source_descriptor.source_type not in {
        HistoricalDataSourceType.LOCAL_CSV,
        HistoricalDataSourceType.LOCAL_JSONL,
    }:
        issues.append(
            build_historical_data_issue(
                HistoricalGapCategory.UNSUPPORTED_SOURCE_TYPE,
                "source_type must remain local_csv or local_jsonl",
            )
        )
        return None, issues

    if lowered.startswith(("http://", "https://")) or "://" in lowered:
        issues.append(
            build_historical_data_issue(
                HistoricalGapCategory.REMOTE_FETCH_NOT_ALLOWED,
                "historical source path must remain local-only",
            )
        )
        return None, issues

    path = Path(local_file_path)
    if not path.exists():
        issues.append(
            build_historical_data_issue(
                HistoricalGapCategory.MISSING_HISTORICAL_DATA_FILE,
                "historical source file does not exist",
            )
        )
        return None, issues
    if not path.is_file():
        issues.append(
            build_historical_data_issue(
                HistoricalGapCategory.UNSAFE_SOURCE_PATH,
                "historical source path must reference a regular file",
            )
        )
        return None, issues

    expected_suffix = ".csv" if source_descriptor.source_type == HistoricalDataSourceType.LOCAL_CSV else ".jsonl"
    if path.suffix.lower() != expected_suffix:
        issues.append(
            build_historical_data_issue(
                HistoricalGapCategory.UNSAFE_SOURCE_PATH,
                f"historical source file must use {expected_suffix}",
            )
        )
        return None, issues
    return path, issues
