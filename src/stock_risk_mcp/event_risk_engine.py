from __future__ import annotations

from datetime import timedelta

from stock_risk_mcp.event_risk_guard import validate_event_risk_metadata_safety
from stock_risk_mcp.event_risk_models import (
    EconomicCalendarSnapshotReport,
    EventCalendarProviderReadinessReport,
    EventRestrictionReport,
    EventRiskDecision,
    EventRiskGapEntry,
    EventRiskGapReport,
    EventRiskInput,
    EventRiskLeakageReport,
    EventRiskSummaryReport,
    EventType,
    EventWindowPolicy,
    EventWindowReport,
    PositionSizingEventAdjustmentReport,
)


def _gap(input_id: str, suffix: str, category: str, severity: str, message: str) -> EventRiskGapEntry:
    return EventRiskGapEntry(
        gap_id=f"{input_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def _safe_ref_present(value: str | None) -> bool:
    return bool(value and str(value).strip())


def _match_window(position_input: EventRiskInput, event_type: EventType) -> EventWindowPolicy | None:
    for window in position_input.event_windows:
        if window.event_type == event_type:
            return window
    return None


def build_event_risk_review(event_input: EventRiskInput) -> EventRiskInput:
    for audit in event_input.audit_records:
        validate_event_risk_metadata_safety(
            {"source_path": audit.source_path, "operator_context": audit.operator_context},
            context="event risk audit",
        )

    gap_entries: list[EventRiskGapEntry] = []
    violations: list[str] = []
    matched_event_ids: list[str] = []
    matched_window_id: str | None = None
    phase = "NONE"
    decision = EventRiskDecision.ALLOW
    decision_reason = "no relevant event restriction"
    event_size_multiplier = 1.0
    restriction_flags: list[str] = []
    future_knowledge_leakage = False
    future_actual_leakage = False
    missing_available_at = event_input.available_at is None

    provider_ready = _safe_ref_present(event_input.provider_readiness_ref) and event_input.provider_readiness_level not in {"GAP", "REJECTED"}
    calendar_ready = _safe_ref_present(event_input.calendar_source_ref) and _safe_ref_present(event_input.calendar_provider_ref) and event_input.available_at is not None
    stale_calendar = bool(event_input.calendar_max_age_minutes and event_input.calendar_freshness_minutes > event_input.calendar_max_age_minutes)
    if not provider_ready:
        gap_entries.append(_gap(event_input.event_risk_review_id, "PROVIDER-GAP", "CALENDAR_PROVIDER_READINESS_GAP", "WARNING", "calendar provider readiness is missing or invalid"))
    if not calendar_ready:
        gap_entries.append(_gap(event_input.event_risk_review_id, "CALENDAR-GAP", "MISSING_CALENDAR_EVIDENCE", "WARNING", "calendar evidence is incomplete"))
    if stale_calendar:
        gap_entries.append(_gap(event_input.event_risk_review_id, "STALE-CALENDAR", "STALE_CALENDAR", "WARNING", "calendar freshness exceeds configured maximum"))
    if missing_available_at:
        gap_entries.append(_gap(event_input.event_risk_review_id, "MISSING-AVAILABLE-AT", "MISSING_AVAILABLE_AT", "BLOCKING", "available_at is missing"))
    if any("real_order" in ref.lower() or "order_payload" in ref.lower() for ref in event_input.source_refs):
        violations.append("EXECUTABLE_ORDER_OBJECT_PRESENT")

    for event in event_input.events:
        if event.available_at and event.available_at > event_input.decision_timestamp:
            future_knowledge_leakage = True
        if event.actual_value is not None and event.scheduled_at > event_input.decision_timestamp:
            future_actual_leakage = True
        if future_knowledge_leakage:
            gap_entries.append(_gap(event_input.event_risk_review_id, "FUTURE-EVENT-KNOWLEDGE", "FUTURE_EVENT_KNOWLEDGE_LEAKAGE", "BLOCKING", "event was not available at decision time"))
        if future_actual_leakage:
            gap_entries.append(_gap(event_input.event_risk_review_id, "FUTURE-ACTUAL-VALUE", "FUTURE_ACTUAL_VALUE_LEAKAGE", "BLOCKING", "actual value leaked before scheduled release"))
        window = _match_window(event_input, event.event_type)
        if not window:
            continue
        delta_minutes = (event.scheduled_at - event_input.decision_timestamp).total_seconds() / 60
        applies_market = event_input.market in event.affected_markets or event.market_scope in {"GLOBAL", event_input.market}
        if not applies_market:
            continue
        if event.event_type == EventType.EARNINGS and not event_input.is_single_name:
            continue
        if event.event_type == EventType.BOK_RATE_DECISION and event_input.country_scope != "KR":
            continue
        if delta_minutes >= 0 and delta_minutes <= window.event_active_window_minutes:
            phase = "EVENT_ACTIVE"
            matched_event_ids.append(event.event_id)
            matched_window_id = window.window_id
            event_size_multiplier = min(event_size_multiplier, window.event_size_multiplier)
            if window.reduce_only:
                decision = EventRiskDecision.REDUCE_ONLY
                decision_reason = "event active reduce-only window"
            else:
                decision = EventRiskDecision.EVENT_ACTIVE
                decision_reason = "event active window"
            break
        if delta_minutes < 0 and abs(delta_minutes) <= window.post_event_cooldown_minutes:
            phase = "COOLDOWN"
            matched_event_ids.append(event.event_id)
            matched_window_id = window.window_id
            event_size_multiplier = min(event_size_multiplier, window.event_size_multiplier)
            if event_input.net_exposure_reducing_action:
                decision = EventRiskDecision.ALLOW
                decision_reason = "post-event cooldown permits exposure reduction"
            elif window.reduce_only and not event_input.net_exposure_reducing_action:
                decision = EventRiskDecision.REDUCE_ONLY
                decision_reason = "post-event cooldown reduce-only"
            else:
                decision = EventRiskDecision.COOLDOWN
                decision_reason = "post-event cooldown active"
            break
        if delta_minutes >= 0 and delta_minutes <= window.pre_event_block_window_minutes:
            phase = "PRE_BLOCK"
            matched_event_ids.append(event.event_id)
            matched_window_id = window.window_id
            event_size_multiplier = min(event_size_multiplier, window.event_size_multiplier)
            if not window.new_entry_allowed and event_input.candidate_action_type in {"NEW_ENTRY", "ADD", "ALLOCATE"}:
                decision = EventRiskDecision.BLOCK_NEW_ENTRY
                decision_reason = "pre-event block window active"
            elif window.watch_only:
                decision = EventRiskDecision.WATCH_ONLY
                decision_reason = "pre-event watch-only window active"
            else:
                decision = EventRiskDecision.REDUCE_SIZE
                decision_reason = "pre-event block window requires downgrade"
            break
        if delta_minutes >= 0 and delta_minutes <= window.pre_event_reduce_window_minutes:
            phase = "PRE_REDUCE"
            matched_event_ids.append(event.event_id)
            matched_window_id = window.window_id
            event_size_multiplier = min(event_size_multiplier, window.event_size_multiplier)
            if window.watch_only:
                decision = EventRiskDecision.WATCH_ONLY
                decision_reason = "pre-event watch-only window active"
            else:
                decision = EventRiskDecision.REDUCE_SIZE
                decision_reason = "pre-event reduce-size window active"
            break

    if future_knowledge_leakage or future_actual_leakage or violations:
        decision = EventRiskDecision.BLOCKED
        decision_reason = "blocking leakage or boundary violation detected"
    elif not provider_ready or not calendar_ready:
        decision = EventRiskDecision.DATA_GAP
        decision_reason = "calendar or provider readiness is incomplete"
    elif stale_calendar:
        decision = EventRiskDecision.DATA_GAP
        decision_reason = "calendar is stale"

    if decision == EventRiskDecision.REDUCE_ONLY:
        restriction_flags.append("REDUCE_ONLY")
    if decision == EventRiskDecision.WATCH_ONLY:
        restriction_flags.append("WATCH_ONLY")
    if decision == EventRiskDecision.BLOCK_NEW_ENTRY:
        restriction_flags.append("BLOCK_NEW_ENTRY")
    if event_input.is_single_name and any(event.event_type == EventType.EARNINGS for event in event_input.events):
        restriction_flags.append("SINGLE_NAME_EARNINGS_RESTRICTION")

    adjusted_sizing_decision = event_input.position_sizing_decision or "UNKNOWN"
    if decision in {EventRiskDecision.BLOCK_NEW_ENTRY, EventRiskDecision.WATCH_ONLY, EventRiskDecision.BLOCKED, EventRiskDecision.DATA_GAP}:
        adjusted_sizing_decision = "WATCH_ONLY"
    elif decision == EventRiskDecision.REDUCE_SIZE and adjusted_sizing_decision == "SIZE_READY":
        adjusted_sizing_decision = "REDUCE_SIZE"
    elif decision == EventRiskDecision.REDUCE_ONLY:
        adjusted_sizing_decision = "REDUCE_ONLY"

    summary_report = EventRiskSummaryReport(
        report_id=f"{event_input.event_risk_review_id}-SUMMARY-REPORT",
        decision=decision,
        decision_reason=decision_reason,
        applicable_event_ids=matched_event_ids,
        event_size_multiplier=event_size_multiplier,
        position_sizing_decision_after_gate=adjusted_sizing_decision,
    )
    calendar_snapshot_report = EconomicCalendarSnapshotReport(
        report_id=f"{event_input.event_risk_review_id}-CALENDAR-SNAPSHOT-REPORT",
        event_count=len(event_input.events),
        event_ids=[event.event_id for event in event_input.events],
        stale_calendar=stale_calendar,
    )
    event_window_report = EventWindowReport(
        report_id=f"{event_input.event_risk_review_id}-WINDOW-REPORT",
        matched_window_id=matched_window_id,
        matched_event_id=matched_event_ids[0] if matched_event_ids else None,
        phase=phase,
        event_size_multiplier=event_size_multiplier,
    )
    restriction_report = EventRestrictionReport(
        report_id=f"{event_input.event_risk_review_id}-RESTRICTION-REPORT",
        new_entry_allowed=decision not in {EventRiskDecision.BLOCK_NEW_ENTRY, EventRiskDecision.WATCH_ONLY, EventRiskDecision.BLOCKED},
        position_increase_allowed=decision not in {EventRiskDecision.BLOCK_NEW_ENTRY, EventRiskDecision.REDUCE_ONLY, EventRiskDecision.WATCH_ONLY, EventRiskDecision.BLOCKED},
        reduce_only=decision == EventRiskDecision.REDUCE_ONLY,
        watch_only=decision == EventRiskDecision.WATCH_ONLY,
        restrictions=restriction_flags,
    )
    position_sizing_adjustment_report = PositionSizingEventAdjustmentReport(
        report_id=f"{event_input.event_risk_review_id}-POSITION-SIZING-ADJUSTMENT-REPORT",
        upstream_position_sizing_decision=event_input.position_sizing_decision or "UNKNOWN",
        adjusted_position_sizing_decision=adjusted_sizing_decision,
        adjusted_size_multiplier=event_size_multiplier,
    )
    provider_readiness_report = EventCalendarProviderReadinessReport(
        report_id=f"{event_input.event_risk_review_id}-PROVIDER-READINESS-REPORT",
        provider_ready=provider_ready,
        provider_readiness_level=event_input.provider_readiness_level,
        calendar_ready=calendar_ready,
        stale_calendar=stale_calendar,
        missing_refs=[
            label for label, ready in (
                ("PROVIDER_READINESS_REF", provider_ready),
                ("CALENDAR_SOURCE_REF", _safe_ref_present(event_input.calendar_source_ref)),
                ("CALENDAR_PROVIDER_REF", _safe_ref_present(event_input.calendar_provider_ref)),
                ("AVAILABLE_AT", event_input.available_at is not None),
            ) if not ready
        ],
    )
    leakage_report = EventRiskLeakageReport(
        report_id=f"{event_input.event_risk_review_id}-LEAKAGE-REPORT",
        future_event_knowledge_leakage=future_knowledge_leakage,
        future_actual_value_leakage=future_actual_leakage,
        missing_available_at=missing_available_at,
        findings=[
            finding for finding, active in (
                ("FUTURE_EVENT_KNOWLEDGE_LEAKAGE", future_knowledge_leakage),
                ("FUTURE_ACTUAL_VALUE_LEAKAGE", future_actual_leakage),
                ("MISSING_AVAILABLE_AT", missing_available_at),
            ) if active
        ],
    )
    gap_entries.append(_gap(event_input.event_risk_review_id, "EVENT-RISK-REPORT-GENERATED", "EVENT_RISK_REPORT_GENERATED", "REPORT_ONLY", "event risk report generated"))
    gap_report = EventRiskGapReport(
        gap_report_id=f"{event_input.event_risk_review_id}-GAP-REPORT",
        decision=decision,
        gap_entries=gap_entries,
        blocking_gap_count=sum(1 for entry in gap_entries if entry.severity == "BLOCKING"),
        warning_gap_count=sum(1 for entry in gap_entries if entry.severity == "WARNING"),
        gap_categories=[entry.gap_category for entry in gap_entries],
    )

    return event_input.model_copy(
        update={
            "summary_report": summary_report,
            "calendar_snapshot_report": calendar_snapshot_report,
            "event_window_report": event_window_report,
            "restriction_report": restriction_report,
            "position_sizing_adjustment_report": position_sizing_adjustment_report,
            "provider_readiness_report": provider_readiness_report,
            "leakage_report": leakage_report,
            "gap_report": gap_report,
        }
    )
