from __future__ import annotations

from datetime import timedelta

from stock_risk_mcp.domestic_realtime_models import (
    DomesticRealtimeFixture,
    DomesticRealtimePlanReport,
    RealtimeDataQualityReport,
    RealtimeQualityStatus,
    RealtimeScannerInputSnapshot,
)


def build_domestic_realtime_plan_report(fixture: DomesticRealtimeFixture) -> DomesticRealtimePlanReport:
    symbol_count = len(fixture.subscription_plan.symbols)
    max_symbols = fixture.subscription_limit.max_subscribed_symbols
    overflow = fixture.subscription_plan.symbols[max_symbols:] if symbol_count > max_symbols else []
    return DomesticRealtimePlanReport(
        plan_id=fixture.subscription_plan.plan_id,
        provider_id=fixture.provider_profile.provider_id,
        strategy_track=fixture.subscription_plan.strategy_track,
        symbol_count=symbol_count,
        max_subscribed_symbols=max_symbols,
        limit_exceeded=symbol_count > max_symbols,
        fallback_applied=fixture.subscription_plan.fallback_mode,
        overflow_symbols=overflow,
        subscription_plan=fixture.subscription_plan.model_dump(mode="json"),
    )


def _normalize_event(fixture: DomesticRealtimeFixture, event) -> dict:
    lag = (event.received_timestamp - event.provider_timestamp).total_seconds()
    age = (fixture.created_at - event.provider_timestamp).total_seconds()
    flags = list(event.data_quality_flags)
    if event.provider_timestamp > event.received_timestamp and fixture.staleness_policy.impossible_timestamp_rejection:
        flags.append("IMPOSSIBLE_TIMESTAMP")
    if lag > fixture.staleness_policy.maximum_provider_to_received_lag_seconds:
        flags.append("TIMESTAMP_MISMATCH")
    if age > fixture.staleness_policy.maximum_event_age_seconds:
        flags.append("STALE_EVENT")
    baseline = event.baseline_volume or 0.0
    spike_ratio = (event.volume / baseline) if baseline and event.volume is not None else None
    return {
        "provider_id": event.provider_id,
        "track": event.strategy_track.value,
        "market_id": event.market_id,
        "symbol": event.symbol,
        "event_type": event.event_type.value,
        "provider_timestamp": event.provider_timestamp.isoformat(),
        "received_timestamp": event.received_timestamp.isoformat(),
        "price": event.price,
        "volume": event.volume,
        "cumulative_volume": event.cumulative_volume,
        "best_bid": event.best_bid,
        "best_ask": event.best_ask,
        "bid_size": event.bid_size,
        "ask_size": event.ask_size,
        "data_quality_flags": sorted(set(flags)),
        "source_fixture_id": event.source_fixture_id,
        "volume_spike_ratio": spike_ratio,
    }


def normalize_domestic_realtime_events(fixture: DomesticRealtimeFixture) -> list[dict]:
    return [_normalize_event(fixture, event) for event in fixture.events]


def build_domestic_realtime_quality_report(fixture: DomesticRealtimeFixture) -> RealtimeDataQualityReport:
    normalized = normalize_domestic_realtime_events(fixture)
    stale_count = 0
    invalid_count = 0
    incomplete_count = 0
    block_reasons: list[str] = []
    warnings: list[str] = []
    snapshots: list[RealtimeScannerInputSnapshot] = []
    for event, item in zip(fixture.events, normalized):
        flags = set(item["data_quality_flags"])
        if "ORDER_TRIGGER_ATTEMPT" in flags:
            block_reasons.append("ORDER_TRIGGER_ATTEMPT")
        if "IMPOSSIBLE_TIMESTAMP" in flags or "TIMESTAMP_MISMATCH" in flags:
            invalid_count += 1
        if "STALE_EVENT" in flags:
            stale_count += 1
        if event.price is None or event.volume is None:
            incomplete_count += 1
        snapshots.append(
            RealtimeScannerInputSnapshot(
                strategy_track=fixture.strategy_request.strategy_track,
                market_profile=fixture.strategy_request.market_profile,
                provider_id=fixture.provider_profile.provider_id,
                symbol=event.symbol,
                freshness_status="STALE" if "STALE_EVENT" in flags else "FRESH",
                quality_status=RealtimeQualityStatus.REPORT_ONLY_STALE if "STALE_EVENT" in flags and fixture.report_only_mode and fixture.staleness_policy.allow_report_only_downgrade else (
                    RealtimeQualityStatus.FAILED_STALE if "STALE_EVENT" in flags else RealtimeQualityStatus.READY
                ),
                report_only=fixture.report_only_mode,
                volume_spike_ratio=item["volume_spike_ratio"],
            )
        )
    if block_reasons:
        quality_status = RealtimeQualityStatus.FAILED_INVALID
    elif stale_count:
        if fixture.report_only_mode and fixture.staleness_policy.allow_report_only_downgrade:
            quality_status = RealtimeQualityStatus.REPORT_ONLY_STALE
            warnings.append("STALE_DATA_REPORT_ONLY")
        else:
            quality_status = RealtimeQualityStatus.FAILED_STALE
            block_reasons.append("STALE_DATA_FAIL_CLOSED")
    elif invalid_count:
        quality_status = RealtimeQualityStatus.FAILED_INVALID
        block_reasons.append("INVALID_TIMESTAMP")
    else:
        quality_status = RealtimeQualityStatus.READY
    return RealtimeDataQualityReport(
        provider_id=fixture.provider_profile.provider_id,
        strategy_track=fixture.strategy_request.strategy_track,
        market_id=fixture.strategy_request.market_profile.market_id,
        symbol_count=len({event.symbol for event in fixture.events}),
        event_count=len(fixture.events),
        stale_event_count=stale_count,
        invalid_timestamp_count=invalid_count,
        incomplete_field_count=incomplete_count,
        quality_status=quality_status,
        warnings=warnings,
        block_reasons=sorted(set(block_reasons)),
        scanner_input_snapshots=snapshots,
    )
