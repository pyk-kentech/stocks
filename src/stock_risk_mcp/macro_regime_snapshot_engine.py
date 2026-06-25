from __future__ import annotations

from datetime import datetime

from stock_risk_mcp.macro_regime_event_calendar import build_macro_regime_event_window_report
from stock_risk_mcp.macro_regime_provider_client import parse_mocked_provider_payload
from stock_risk_mcp.macro_regime_provider_guard import validate_macro_regime_metadata_safety
from stock_risk_mcp.macro_regime_provider_models import (
    CanonicalMacroRegimeSnapshot,
    CanonicalMacroSeriesPoint,
    MacroRegimeConflictEntry,
    MacroRegimeConflictReport,
    MacroRegimeFreshnessEntry,
    MacroRegimeFreshnessReport,
    MacroRegimeGapEntry,
    MacroRegimeGapReport,
    MacroRegimePipelineInput,
    MacroRegimeProvider,
    MacroRegimeProviderCapability,
    MacroRegimeProviderCapabilityReport,
    MacroRegimeProviderCapabilityRow,
    MacroRegimeProviderStatus,
    MacroRegimeSafetyReport,
    MacroRegimeSeriesId,
    MacroRegimeSnapshotReadiness,
)


_CRITICAL_SERIES = (
    MacroRegimeSeriesId.NQ_CONTINUOUS,
    MacroRegimeSeriesId.ES_CONTINUOUS,
    MacroRegimeSeriesId.VIX,
    MacroRegimeSeriesId.DOLLAR_STRENGTH,
    MacroRegimeSeriesId.US10Y,
    MacroRegimeSeriesId.USDKRW,
)

_SERIES_TO_CAPABILITY = {
    MacroRegimeSeriesId.NQ_CONTINUOUS: MacroRegimeProviderCapability.NQ_FUTURES,
    MacroRegimeSeriesId.ES_CONTINUOUS: MacroRegimeProviderCapability.ES_FUTURES,
    MacroRegimeSeriesId.VIX: MacroRegimeProviderCapability.VIX,
    MacroRegimeSeriesId.DOLLAR_STRENGTH: MacroRegimeProviderCapability.DOLLAR_STRENGTH,
    MacroRegimeSeriesId.US10Y: MacroRegimeProviderCapability.US10Y,
    MacroRegimeSeriesId.USDKRW: MacroRegimeProviderCapability.USDKRW,
}


def _gap(pipeline_id: str, suffix: str, category: str, severity: str, message: str) -> MacroRegimeGapEntry:
    return MacroRegimeGapEntry(
        gap_id=f"{pipeline_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def _latest(points: list[CanonicalMacroSeriesPoint]) -> CanonicalMacroSeriesPoint | None:
    if not points:
        return None
    return max(points, key=lambda item: item.observed_at)


def build_macro_regime_snapshot(
    pipeline_input: MacroRegimePipelineInput,
) -> tuple[
    CanonicalMacroRegimeSnapshot,
    MacroRegimeProviderCapabilityReport,
    MacroRegimeFreshnessReport,
    MacroRegimeConflictReport,
    MacroRegimeGapReport,
    MacroRegimeSafetyReport,
    object,
]:
    for audit in pipeline_input.audit_records:
        validate_macro_regime_metadata_safety(
            {"source_path": audit.source_path, "operator_context": audit.operator_context},
            context="macro regime audit",
        )

    series_points = list(pipeline_input.manual_series_points)
    events = list(pipeline_input.manual_events)
    for payload in pipeline_input.mocked_provider_payloads:
        parsed_points, parsed_events = parse_mocked_provider_payload(payload)
        series_points.extend(parsed_points)
        events.extend(parsed_events)

    event_window_report = build_macro_regime_event_window_report(pipeline_input.pipeline_id, pipeline_input.anchor_at, events)
    grouped = {series_id: [point for point in series_points if point.series_id == series_id] for series_id in _CRITICAL_SERIES}
    latest_points = {series_id: _latest(points) for series_id, points in grouped.items()}

    provider_rows: list[MacroRegimeProviderCapabilityRow] = []
    for provider in pipeline_input.provider_definitions:
        for capability in provider.capabilities:
            manual_fixture_supplied = False
            for series_id, mapped_capability in _SERIES_TO_CAPABILITY.items():
                if mapped_capability == capability:
                    manual_fixture_supplied = latest_points.get(series_id) is not None
                    break
            provider_rows.append(
                MacroRegimeProviderCapabilityRow(
                    provider=provider.provider,
                    capability=capability,
                    status=provider.status,
                    manual_fixture_supplied=manual_fixture_supplied,
                    notes=provider.notes,
                )
            )

    freshness_entries: list[MacroRegimeFreshnessEntry] = []
    stale_count = 0
    gap_entries: list[MacroRegimeGapEntry] = []
    blocking_gap_categories: list[str] = []
    for series_id in _CRITICAL_SERIES:
        point = latest_points.get(series_id)
        if point is None:
            category = f"MISSING_{series_id.value}"
            gap_entries.append(_gap(pipeline_input.pipeline_id, category, category, "WARNING", f"{series_id.value} is missing"))
            blocking_gap_categories.append(category)
            freshness_entries.append(MacroRegimeFreshnessEntry(series_id=series_id, stale=False, reason="MISSING"))
            continue
        age_minutes = int(((pipeline_input.anchor_at - (point.available_at or point.observed_at)).total_seconds()) // 60)
        stale = point.stale_flag or age_minutes > pipeline_input.max_data_age_minutes
        if stale:
            stale_count += 1
            gap_entries.append(
                _gap(
                    pipeline_input.pipeline_id,
                    f"{series_id.value}-STALE",
                    "STALE_CRITICAL_DATA",
                    "WARNING",
                    f"{series_id.value} exceeds freshness policy",
                )
            )
        freshness_entries.append(
            MacroRegimeFreshnessEntry(
                series_id=series_id,
                latest_observed_at=point.observed_at,
                latest_available_at=point.available_at,
                stale=stale,
                age_minutes=max(age_minutes, 0),
                reason="STALE" if stale else None,
            )
        )

    conflicts: list[MacroRegimeConflictEntry] = []
    nq = latest_points.get(MacroRegimeSeriesId.NQ_CONTINUOUS)
    es = latest_points.get(MacroRegimeSeriesId.ES_CONTINUOUS)
    vix = latest_points.get(MacroRegimeSeriesId.VIX)
    usdkrw = latest_points.get(MacroRegimeSeriesId.USDKRW)
    if nq and es and nq.pct_change_1d is not None and es.pct_change_1d is not None:
        if nq.pct_change_1d > 0.5 and es.pct_change_1d > 0.5 and vix and vix.value >= 25:
            conflicts.append(
                MacroRegimeConflictEntry(
                    conflict_id=f"{pipeline_input.pipeline_id}-RISK-ON-VIX",
                    field_name="VIX",
                    message="equity futures imply risk-on while VIX remains elevated",
                )
            )
    if usdkrw and nq and usdkrw.pct_change_1d is not None and nq.pct_change_1d is not None:
        if usdkrw.pct_change_1d > 0.5 and nq.pct_change_1d > 0.5:
            conflicts.append(
                MacroRegimeConflictEntry(
                    conflict_id=f"{pipeline_input.pipeline_id}-FX-EQUITY",
                    field_name="USDKRW",
                    message="USDKRW stress conflicts with positive futures direction",
                )
            )

    if conflicts:
        readiness = MacroRegimeSnapshotReadiness.CONFLICT
    elif blocking_gap_categories:
        readiness = MacroRegimeSnapshotReadiness.DATA_GAP
    elif stale_count:
        readiness = MacroRegimeSnapshotReadiness.STALE
    elif event_window_report.active_window_count or event_window_report.upcoming_window_count:
        readiness = MacroRegimeSnapshotReadiness.PARTIAL
    else:
        readiness = MacroRegimeSnapshotReadiness.SNAPSHOT_READY

    gap_entries.append(
        _gap(
            pipeline_input.pipeline_id,
            "REPORT-GENERATED",
            "REPORT_GENERATED",
            "REPORT_ONLY",
            "macro regime snapshot generated",
        )
    )

    snapshot = CanonicalMacroRegimeSnapshot(
        snapshot_id=f"{pipeline_input.pipeline_id}-SNAPSHOT",
        anchor_at=pipeline_input.anchor_at,
        available_at=max(
            [point.available_at or point.observed_at for point in latest_points.values() if point is not None],
            default=pipeline_input.available_at,
        ),
        readiness=readiness,
        nq=latest_points.get(MacroRegimeSeriesId.NQ_CONTINUOUS),
        es=latest_points.get(MacroRegimeSeriesId.ES_CONTINUOUS),
        vix=latest_points.get(MacroRegimeSeriesId.VIX),
        dollar_strength=latest_points.get(MacroRegimeSeriesId.DOLLAR_STRENGTH),
        us10y=latest_points.get(MacroRegimeSeriesId.US10Y),
        usdkrw=latest_points.get(MacroRegimeSeriesId.USDKRW),
        active_event_ids=[window.event_id for window in event_window_report.windows if window.active],
        upcoming_event_ids=[window.event_id for window in event_window_report.windows if window.phase == "UPCOMING"],
        blocking_gap_categories=blocking_gap_categories,
    )
    capability_report = MacroRegimeProviderCapabilityReport(
        report_id=f"{pipeline_input.pipeline_id}-PROVIDER-CAPABILITY-REPORT",
        rows=provider_rows,
    )
    freshness_report = MacroRegimeFreshnessReport(
        report_id=f"{pipeline_input.pipeline_id}-FRESHNESS-REPORT",
        entries=freshness_entries,
        stale_series_count=stale_count,
    )
    conflict_report = MacroRegimeConflictReport(
        report_id=f"{pipeline_input.pipeline_id}-CONFLICT-REPORT",
        conflicts=conflicts,
        conflict_count=len(conflicts),
    )
    gap_report = MacroRegimeGapReport(
        report_id=f"{pipeline_input.pipeline_id}-GAP-REPORT",
        readiness=readiness,
        gap_entries=gap_entries,
    )
    safety_report = MacroRegimeSafetyReport(
        report_id=f"{pipeline_input.pipeline_id}-SAFETY-REPORT",
        findings=[
            "REPORT_ONLY",
            "NO_ACCOUNT_ORDER_PATH",
            "NO_REAL_PROVIDER_CALLS_BY_DEFAULT",
            "DTWEXBGS_IS_FALLBACK_NOT_EXACT_DXY",
        ],
    )
    return snapshot, capability_report, freshness_report, conflict_report, gap_report, safety_report, event_window_report
