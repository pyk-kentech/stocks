from __future__ import annotations

from stock_risk_mcp.macro_regime_provider_models import (
    CanonicalMacroRegimeSnapshot,
    CanonicalRegimeClassification,
    MacroRegimeClassificationLabel,
    MacroRegimeEventWindowReport,
    MacroRegimePipelineResult,
    MacroRegimeV7IntegrationReport,
    MacroRegimeV8IntegrationReport,
)


def build_macro_regime_v7_integration_report(
    snapshot: CanonicalMacroRegimeSnapshot,
    classification: CanonicalRegimeClassification,
    event_window_report: MacroRegimeEventWindowReport,
) -> MacroRegimeV7IntegrationReport:
    if classification.label == MacroRegimeClassificationLabel.MACRO_RISK_ON:
        market_context = "RISK_ON_COMPATIBLE"
        sizing_context = "CONSTRUCTIVE_BUT_REPORT_ONLY"
        breadth_context = "LEADERSHIP_CONFIRMATION_PREFERRED"
    elif classification.label == MacroRegimeClassificationLabel.MACRO_RISK_OFF:
        market_context = "RISK_OFF_COMPATIBLE"
        sizing_context = "SIZE_REDUCTION_CONTEXT"
        breadth_context = "OUTLIER_FILTER_TIGHTENED"
    elif classification.label == MacroRegimeClassificationLabel.MACRO_EVENT_RISK:
        market_context = "EVENT_RISK_CONTEXT"
        sizing_context = "EVENT_SIZE_RESTRAINT_CONTEXT"
        breadth_context = "EVENT_NOISE_FILTER_TIGHTENED"
    elif classification.label == MacroRegimeClassificationLabel.MACRO_DATA_GAP:
        market_context = "MACRO_DATA_GAP_CONTEXT"
        sizing_context = "DEFENSIVE_DATA_GAP_CONTEXT"
        breadth_context = "LOW_CONFIDENCE_ROUTING_CONTEXT"
    else:
        market_context = "MIXED_MACRO_CONTEXT"
        sizing_context = "NEUTRAL_SIZING_CONTEXT"
        breadth_context = "ROUTING_CONFIRMATION_REQUIRED"

    event_context = "EVENT_WINDOW_CLEAR"
    if event_window_report.active_window_count:
        event_context = "ACTIVE_EVENT_WINDOW_CONTEXT"
    elif event_window_report.upcoming_window_count:
        event_context = "UPCOMING_EVENT_WINDOW_CONTEXT"

    return MacroRegimeV7IntegrationReport(
        report_id=f"{snapshot.snapshot_id}-V7-INTEGRATION-REPORT",
        market_regime_context=market_context,
        sizing_risk_context=sizing_context,
        event_risk_context=event_context,
        breadth_routing_context=breadth_context,
        blocking_gap_categories=classification.blocking_gap_categories,
    )


def build_macro_regime_v8_integration_report(
    snapshot: CanonicalMacroRegimeSnapshot,
    classification: CanonicalRegimeClassification,
    event_window_report: MacroRegimeEventWindowReport,
) -> MacroRegimeV8IntegrationReport:
    if classification.label == MacroRegimeClassificationLabel.MACRO_RISK_OFF:
        macro_bias = "DEFENSIVE_MACRO_OVERLAY"
    elif classification.label == MacroRegimeClassificationLabel.MACRO_RISK_ON:
        macro_bias = "CONSTRUCTIVE_MACRO_OVERLAY"
    elif classification.label == MacroRegimeClassificationLabel.MACRO_EVENT_RISK:
        macro_bias = "EVENT_RISK_MACRO_OVERLAY"
    elif classification.label == MacroRegimeClassificationLabel.MACRO_DATA_GAP:
        macro_bias = "MACRO_DATA_GAP_OVERLAY"
    else:
        macro_bias = "MIXED_MACRO_OVERLAY"

    event_overlay = "NO_EVENT_OVERLAY"
    if event_window_report.active_window_count:
        event_overlay = "ACTIVE_EVENT_OVERLAY"
    elif event_window_report.upcoming_window_count:
        event_overlay = "UPCOMING_EVENT_OVERLAY"

    return MacroRegimeV8IntegrationReport(
        report_id=f"{snapshot.snapshot_id}-V8-INTEGRATION-REPORT",
        domestic_snapshot_macro_context="V8_DOMESTIC_SNAPSHOT_MACRO_CONTEXT",
        macro_bias=macro_bias,
        event_overlay=event_overlay,
        attachable_to_v8_snapshot=True,
        blocking_gap_categories=classification.blocking_gap_categories,
    )


def build_macro_regime_pipeline_result(
    snapshot: CanonicalMacroRegimeSnapshot,
    classification: CanonicalRegimeClassification,
    provider_capability_report,
    freshness_report,
    conflict_report,
    event_window_report,
    gap_report,
    safety_report,
) -> MacroRegimePipelineResult:
    return MacroRegimePipelineResult(
        snapshot=snapshot,
        classification=classification,
        provider_capability_report=provider_capability_report,
        freshness_report=freshness_report,
        conflict_report=conflict_report,
        event_window_report=event_window_report,
        v7_integration_report=build_macro_regime_v7_integration_report(snapshot, classification, event_window_report),
        v8_integration_report=build_macro_regime_v8_integration_report(snapshot, classification, event_window_report),
        gap_report=gap_report,
        safety_report=safety_report,
    )
