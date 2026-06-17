from __future__ import annotations

from stock_risk_mcp.domestic_realtime_engine import (
    build_domestic_realtime_quality_report,
    normalize_domestic_realtime_events,
)
from stock_risk_mcp.domestic_scanner_models import (
    DOMESTIC_SCANNER_METADATA,
    DomesticScannerFixture,
    LiquiditySignal,
    PriceMomentumSignal,
    ScannerCandidate,
    ScannerCandidateState,
    ScannerConfigValidationReport,
    ScannerDataQualityGate,
    ScannerDecisionReport,
    ScannerDiscoveryCompatibility,
    ScannerInputSnapshot,
    VolumeSpikeSignal,
    WatchlistUpdatePlan,
)


def build_domestic_scanner_validation_report(fixture: DomesticScannerFixture) -> ScannerConfigValidationReport:
    return ScannerConfigValidationReport(
        config_id=fixture.scanner_config.config_id,
        strategy_track=fixture.scanner_config.strategy_track,
        provider_id=fixture.domestic_realtime_fixture.provider_profile.provider_id,
        market_id=fixture.domestic_realtime_fixture.strategy_request.market_profile.market_id,
    )


def build_domestic_scanner_snapshots(fixture: DomesticScannerFixture) -> list[ScannerInputSnapshot]:
    normalized = normalize_domestic_realtime_events(fixture.domestic_realtime_fixture)
    quality = build_domestic_realtime_quality_report(fixture.domestic_realtime_fixture)
    snapshots: list[ScannerInputSnapshot] = []
    for index, (event, item, quality_snapshot) in enumerate(
        zip(fixture.domestic_realtime_fixture.events, normalized, quality.scanner_input_snapshots)
    ):
        snapshots.append(
            ScannerInputSnapshot(
                snapshot_id=f"{fixture.run_id}-snapshot-{index + 1}",
                strategy_track=fixture.scanner_config.strategy_track,
                provider_id=item["provider_id"],
                symbol=item["symbol"],
                event_type=item["event_type"],
                price=item["price"],
                volume=item["volume"],
                best_bid=item["best_bid"],
                best_ask=item["best_ask"],
                bid_size=item["bid_size"],
                ask_size=item["ask_size"],
                volume_spike_ratio=item["volume_spike_ratio"],
                freshness_status=quality_snapshot.freshness_status,
                report_only=quality_snapshot.report_only,
                preserved_quality_flags=item["data_quality_flags"],
                fixture_source_marker=item["source_fixture_id"],
            )
        )
    return snapshots


def _volume_signal(snapshot: ScannerInputSnapshot, threshold: float) -> VolumeSpikeSignal:
    return VolumeSpikeSignal(
        symbol=snapshot.symbol,
        observed_volume=snapshot.volume,
        baseline_volume=(snapshot.volume / snapshot.volume_spike_ratio) if snapshot.volume and snapshot.volume_spike_ratio else None,
        spike_ratio=snapshot.volume_spike_ratio,
        threshold=threshold,
        signal_pass=(snapshot.volume_spike_ratio or 0) >= threshold,
        freshness_status=snapshot.freshness_status,
        quality_flags=list(snapshot.preserved_quality_flags),
    )


def _momentum_signal(snapshot: ScannerInputSnapshot, threshold: float) -> PriceMomentumSignal:
    reference = snapshot.best_bid or snapshot.price
    change_pct = None
    signal_pass = False
    if snapshot.price is not None and reference not in (None, 0):
        change_pct = ((snapshot.price - reference) / reference) * 100
        signal_pass = change_pct >= (threshold / 100)
    return PriceMomentumSignal(
        symbol=snapshot.symbol,
        recent_price=snapshot.price,
        reference_price=reference,
        price_change_pct=change_pct,
        threshold=threshold,
        direction="UP" if (change_pct or 0) >= 0 else "DOWN",
        signal_pass=signal_pass,
        quality_flags=list(snapshot.preserved_quality_flags),
    )


def _liquidity_signal(snapshot: ScannerInputSnapshot, max_spread_pct: float, min_size: float) -> LiquiditySignal:
    spread_pct = None
    signal_pass = False
    if snapshot.best_bid not in (None, 0) and snapshot.best_ask is not None and snapshot.price not in (None, 0):
        spread_pct = (snapshot.best_ask - snapshot.best_bid) / snapshot.price
        signal_pass = (
            spread_pct <= max_spread_pct
            and (snapshot.bid_size or 0) >= min_size
            and (snapshot.ask_size or 0) >= min_size
        )
    return LiquiditySignal(
        symbol=snapshot.symbol,
        best_bid=snapshot.best_bid,
        best_ask=snapshot.best_ask,
        spread_pct=spread_pct,
        bid_size=snapshot.bid_size,
        ask_size=snapshot.ask_size,
        signal_pass=signal_pass,
        quality_flags=list(snapshot.preserved_quality_flags),
    )


def _state_for_snapshot(
    fixture: DomesticScannerFixture,
    snapshot: ScannerInputSnapshot,
    volume_signal: VolumeSpikeSignal,
    momentum_signal: PriceMomentumSignal,
    liquidity_signal: LiquiditySignal,
) -> tuple[ScannerCandidateState, ScannerDiscoveryCompatibility, list[str], list[str]]:
    flags = set(snapshot.preserved_quality_flags)
    warnings: list[str] = []
    blocks: list[str] = []
    if snapshot.strategy_track.value != "DOMESTIC_KR":
        return ScannerCandidateState.REJECTED_NON_DOMESTIC, ScannerDiscoveryCompatibility.EXCLUDE, warnings, ["NON_DOMESTIC_TRACK"]
    if "ORDER_TRIGGER_ATTEMPT" in flags:
        return ScannerCandidateState.REJECTED_UNSAFE_TRIGGER, ScannerDiscoveryCompatibility.EXCLUDE, warnings, ["ORDER_TRIGGER_ATTEMPT"]
    if snapshot.price is None or snapshot.volume is None:
        return ScannerCandidateState.INSUFFICIENT_DATA, ScannerDiscoveryCompatibility.WATCH, warnings, ["MISSING_REQUIRED_FIELDS"]
    if snapshot.freshness_status == "STALE":
        if snapshot.report_only and fixture.domestic_realtime_fixture.staleness_policy.allow_report_only_downgrade:
            warnings.append("STALE_DATA_REPORT_ONLY")
            return ScannerCandidateState.REPORT_ONLY_STALE, ScannerDiscoveryCompatibility.WATCH, warnings, blocks
        return ScannerCandidateState.BLOCKED_QUALITY, ScannerDiscoveryCompatibility.EXCLUDE, warnings, ["STALE_DATA_FAIL_CLOSED"]
    if "IMPOSSIBLE_TIMESTAMP" in flags or "TIMESTAMP_MISMATCH" in flags:
        return ScannerCandidateState.BLOCKED_QUALITY, ScannerDiscoveryCompatibility.EXCLUDE, warnings, ["INVALID_TIMESTAMP"]

    score = 0
    if volume_signal.signal_pass:
        score += 40
    if momentum_signal.signal_pass:
        score += 35
    if liquidity_signal.signal_pass:
        score += 25

    if volume_signal.signal_pass and liquidity_signal.signal_pass:
        return ScannerCandidateState.WATCHLIST_ADD, ScannerDiscoveryCompatibility.WATCH, warnings, blocks
    if not liquidity_signal.signal_pass and not volume_signal.signal_pass:
        return ScannerCandidateState.WATCHLIST_REMOVE, ScannerDiscoveryCompatibility.EXCLUDE, warnings, ["LOW_LIQUIDITY_OR_ACTIVITY"]
    if score > 0:
        compatibility = ScannerDiscoveryCompatibility.DISCOVER if score >= 70 else ScannerDiscoveryCompatibility.WATCH
        return ScannerCandidateState.SCANNER_READY, compatibility, warnings, blocks
    return ScannerCandidateState.INSUFFICIENT_DATA, ScannerDiscoveryCompatibility.EXCLUDE, warnings, ["NO_SCANNER_SIGNALS"]


def build_domestic_scanner_candidates(fixture: DomesticScannerFixture) -> ScannerDecisionReport:
    snapshots = build_domestic_scanner_snapshots(fixture)
    candidates: list[ScannerCandidate] = []
    compatibility_counts = {item.value: 0 for item in ScannerDiscoveryCompatibility}
    warnings: list[str] = []
    blocks: list[str] = []
    for index, snapshot in enumerate(snapshots):
        volume_signal = _volume_signal(snapshot, fixture.scanner_config.volume_spike_ratio_threshold)
        momentum_signal = _momentum_signal(snapshot, fixture.scanner_config.price_momentum_pct_threshold)
        liquidity_signal = _liquidity_signal(
            snapshot,
            fixture.scanner_config.max_spread_pct,
            fixture.scanner_config.min_bid_ask_size,
        )
        internal_state, compatibility, item_warnings, item_blocks = _state_for_snapshot(
            fixture,
            snapshot,
            volume_signal,
            momentum_signal,
            liquidity_signal,
        )
        compatibility_counts[compatibility.value] += 1
        warnings.extend(item_warnings)
        blocks.extend(item_blocks)
        candidates.append(
            ScannerCandidate(
                candidate_id=f"{fixture.run_id}-candidate-{index + 1}",
                snapshot_id=snapshot.snapshot_id,
                symbol=snapshot.symbol,
                internal_state=internal_state,
                compatibility_discovery_status=compatibility,
                candidate_reason_codes=[code for code, passed in {
                    "VOLUME_SPIKE": volume_signal.signal_pass,
                    "PRICE_MOMENTUM": momentum_signal.signal_pass,
                    "LIQUIDITY_OK": liquidity_signal.signal_pass,
                }.items() if passed],
                block_reasons=item_blocks,
                warnings=item_warnings,
                preserved_quality_flags=list(snapshot.preserved_quality_flags),
                volume_spike_signal=volume_signal,
                price_momentum_signal=momentum_signal,
                liquidity_signal=liquidity_signal,
                quality_gate=ScannerDataQualityGate(
                    freshness_gate=snapshot.freshness_status,
                    completeness_gate="PASS" if snapshot.price is not None and snapshot.volume is not None else "FAIL",
                    unsafe_trigger_gate="FAIL" if "ORDER_TRIGGER_ATTEMPT" in snapshot.preserved_quality_flags else "PASS",
                    report_only_downgrade_gate="ALLOW" if snapshot.report_only else "DISALLOW",
                    preserved_quality_flags=list(snapshot.preserved_quality_flags),
                    decision_outcome=internal_state.value,
                ),
                watchlist_intent=internal_state.value,
                technical_setup_summary=fixture.technical_context.technical_setup_summary,
                technical_indicator_markers=list(fixture.technical_context.indicator_markers),
                setup_grade=fixture.technical_context.setup_grade,
                evidence_freshness=fixture.technical_context.evidence_freshness,
                profitability_context_summary=fixture.profitability_context.model_dump(mode="json"),
                supported_tracks=list(fixture.advisory_context.supported_tracks),
                prompt_pack_context_marker=fixture.advisory_context.prompt_pack_context_marker,
                advisory_context_allowed=True,
                actionable_approval=False,
            )
        )

    report = ScannerDecisionReport(
        report_id=f"{fixture.run_id}-report",
        strategy_track=fixture.scanner_config.strategy_track,
        market_profile_summary=fixture.domestic_realtime_fixture.strategy_request.market_profile.model_dump(mode="json"),
        provider_profile_summary=fixture.domestic_realtime_fixture.provider_profile.model_dump(mode="json"),
        candidate_count=len(candidates),
        ready_count=sum(item.internal_state == ScannerCandidateState.SCANNER_READY for item in candidates),
        watchlist_add_count=sum(item.internal_state == ScannerCandidateState.WATCHLIST_ADD for item in candidates),
        watchlist_remove_count=sum(item.internal_state == ScannerCandidateState.WATCHLIST_REMOVE for item in candidates),
        blocked_count=sum(item.internal_state in {
            ScannerCandidateState.BLOCKED_QUALITY,
            ScannerCandidateState.REJECTED_NON_DOMESTIC,
            ScannerCandidateState.REJECTED_UNSAFE_TRIGGER,
        } for item in candidates),
        report_only_count=sum(item.internal_state == ScannerCandidateState.REPORT_ONLY_STALE for item in candidates),
        compatibility_decision_counts=compatibility_counts,
        warnings=sorted(set(warnings)),
        block_reasons=sorted(set(blocks)),
        candidates=candidates,
    )
    report.watchlist_update_plan = build_domestic_scanner_watchlist_plan(report)
    report.metadata_json = dict(DOMESTIC_SCANNER_METADATA)
    return report


def build_domestic_scanner_watchlist_plan(report: ScannerDecisionReport) -> WatchlistUpdatePlan:
    additions = [item.symbol for item in report.candidates if item.internal_state in {ScannerCandidateState.WATCHLIST_ADD, ScannerCandidateState.SCANNER_READY}]
    removals = [item.symbol for item in report.candidates if item.internal_state == ScannerCandidateState.WATCHLIST_REMOVE]
    blocked = [item.symbol for item in report.candidates if item.internal_state in {
        ScannerCandidateState.BLOCKED_QUALITY,
        ScannerCandidateState.REJECTED_NON_DOMESTIC,
        ScannerCandidateState.REJECTED_UNSAFE_TRIGGER,
        ScannerCandidateState.INSUFFICIENT_DATA,
    }]
    report_only = [item.symbol for item in report.candidates if item.internal_state == ScannerCandidateState.REPORT_ONLY_STALE]
    retained = [item.symbol for item in report.candidates if item.symbol not in set(additions + removals + blocked + report_only)]
    return WatchlistUpdatePlan(
        plan_id=f"{report.report_id}-watchlist",
        strategy_track=report.strategy_track,
        additions=additions,
        removals=removals,
        retained_symbols=retained,
        blocked_symbols=blocked,
        report_only_symbols=report_only,
        plan_reason_codes=sorted({item.internal_state.value for item in report.candidates}),
        source_candidate_ids=[item.candidate_id for item in report.candidates],
        metadata_json=dict(DOMESTIC_SCANNER_METADATA),
    )


def build_domestic_scanner_quality_report(fixture: DomesticScannerFixture) -> ScannerDecisionReport:
    return build_domestic_scanner_candidates(fixture)
