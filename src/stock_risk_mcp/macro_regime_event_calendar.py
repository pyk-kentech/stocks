from __future__ import annotations

from datetime import timedelta

from stock_risk_mcp.macro_regime_provider_models import (
    CanonicalMacroEvent,
    CanonicalMacroEventWindow,
    MacroRegimeEventWindowReport,
)


def build_macro_regime_event_window_report(
    pipeline_id: str,
    anchor_at,
    events: list[CanonicalMacroEvent],
) -> MacroRegimeEventWindowReport:
    windows: list[CanonicalMacroEventWindow] = []
    active_window_count = 0
    upcoming_window_count = 0
    for event in events:
        starts_at = event.event_time - timedelta(minutes=max(event.pre_event_block_window_minutes, event.pre_event_reduce_window_minutes))
        ends_at = event.event_time + timedelta(minutes=max(event.post_event_cooldown_minutes, event.event_active_window_minutes))
        if anchor_at < starts_at:
            phase = "UPCOMING"
            active = False
            upcoming_window_count += 1
        elif starts_at <= anchor_at <= event.event_time + timedelta(minutes=event.event_active_window_minutes):
            phase = "ACTIVE"
            active = True
            active_window_count += 1
        elif anchor_at <= ends_at:
            phase = "COOLDOWN"
            active = True
            active_window_count += 1
        else:
            phase = "PASSED"
            active = False
        windows.append(
            CanonicalMacroEventWindow(
                window_id=f"{event.event_id}-WINDOW",
                event_id=event.event_id,
                event_type=event.event_type,
                starts_at=starts_at,
                event_time=event.event_time,
                ends_at=ends_at,
                phase=phase,
                active=active,
                source_ref=event.source_ref,
            )
        )
    return MacroRegimeEventWindowReport(
        report_id=f"{pipeline_id}-EVENT-WINDOW-REPORT",
        windows=windows,
        active_window_count=active_window_count,
        upcoming_window_count=upcoming_window_count,
    )
