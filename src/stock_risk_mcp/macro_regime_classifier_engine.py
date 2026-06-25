from __future__ import annotations

from stock_risk_mcp.macro_regime_provider_models import (
    CanonicalMacroRegimeSnapshot,
    CanonicalRegimeClassification,
    MacroRegimeClassificationLabel,
    MacroRegimeEventWindowReport,
)


def build_macro_regime_classification(
    snapshot: CanonicalMacroRegimeSnapshot,
    event_window_report: MacroRegimeEventWindowReport,
) -> CanonicalRegimeClassification:
    if snapshot.blocking_gap_categories:
        return CanonicalRegimeClassification(
            classification_id=f"{snapshot.snapshot_id}-CLASSIFICATION",
            label=MacroRegimeClassificationLabel.MACRO_DATA_GAP,
            confidence_bucket="LOW",
            rationale="critical macro inputs remain missing",
            supporting_series_ids=[],
            blocking_gap_categories=snapshot.blocking_gap_categories,
        )

    if event_window_report.active_window_count:
        return CanonicalRegimeClassification(
            classification_id=f"{snapshot.snapshot_id}-CLASSIFICATION",
            label=MacroRegimeClassificationLabel.MACRO_EVENT_RISK,
            confidence_bucket="HIGH",
            rationale="active macro event window is in force",
            supporting_series_ids=[window.event_id for window in event_window_report.windows if window.active],
            blocking_gap_categories=[],
        )

    score = 0
    supporting: list[str] = []

    for point in (snapshot.nq, snapshot.es):
        if point and point.pct_change_1d is not None:
            supporting.append(point.series_id.value)
            if point.pct_change_1d > 0.25:
                score += 1
            elif point.pct_change_1d < -0.25:
                score -= 1

    if snapshot.vix:
        supporting.append(snapshot.vix.series_id.value)
        if snapshot.vix.value >= 25 or (snapshot.vix.pct_change_1d is not None and snapshot.vix.pct_change_1d >= 3.0):
            score -= 2
        elif snapshot.vix.value <= 18:
            score += 1

    if snapshot.dollar_strength and snapshot.dollar_strength.pct_change_1d is not None:
        supporting.append(snapshot.dollar_strength.series_id.value)
        if snapshot.dollar_strength.pct_change_1d >= 0.4:
            score -= 1
        elif snapshot.dollar_strength.pct_change_1d <= -0.4:
            score += 1

    if snapshot.us10y:
        supporting.append(snapshot.us10y.series_id.value)
        if snapshot.us10y.value >= 4.5:
            score -= 1
        elif snapshot.us10y.value <= 3.8:
            score += 1

    if snapshot.usdkrw and snapshot.usdkrw.pct_change_1d is not None:
        supporting.append(snapshot.usdkrw.series_id.value)
        if snapshot.usdkrw.pct_change_1d >= 0.4:
            score -= 1
        elif snapshot.usdkrw.pct_change_1d <= -0.4:
            score += 1

    if score >= 2:
        label = MacroRegimeClassificationLabel.MACRO_RISK_ON
        confidence = "MEDIUM"
        rationale = "cross-asset macro inputs lean constructive"
    elif score <= -2:
        label = MacroRegimeClassificationLabel.MACRO_RISK_OFF
        confidence = "MEDIUM"
        rationale = "cross-asset macro inputs lean defensive"
    else:
        label = MacroRegimeClassificationLabel.MACRO_MIXED
        confidence = "LOW"
        rationale = "cross-asset macro inputs remain mixed"

    return CanonicalRegimeClassification(
        classification_id=f"{snapshot.snapshot_id}-CLASSIFICATION",
        label=label,
        confidence_bucket=confidence,
        rationale=rationale,
        supporting_series_ids=supporting,
        blocking_gap_categories=[],
    )
