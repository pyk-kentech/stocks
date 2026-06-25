from __future__ import annotations

from collections import defaultdict

from stock_risk_mcp.kiwoom_readonly_snapshot_guard import validate_kiwoom_readonly_snapshot_metadata_safety
from stock_risk_mcp.kiwoom_readonly_snapshot_models import (
    CanonicalDomesticStockSnapshot,
    KiwoomReadonlySnapshotCompletenessReport,
    KiwoomReadonlySnapshotComposerResult,
    KiwoomReadonlySnapshotConfig,
    KiwoomReadonlySnapshotConflictEntry,
    KiwoomReadonlySnapshotConflictReport,
    KiwoomReadonlySnapshotFreshnessEntry,
    KiwoomReadonlySnapshotFreshnessReport,
    KiwoomReadonlySnapshotGapEntry,
    KiwoomReadonlySnapshotGapReport,
    KiwoomReadonlySnapshotReadiness,
    KiwoomReadonlySnapshotSourceCoverageEntry,
    KiwoomReadonlySnapshotSourceCoverageReport,
    KiwoomReadonlySnapshotSummaryReport,
    KiwoomReadonlySnapshotV710IntegrationReport,
    KiwoomReadonlySnapshotV712IntegrationReport,
    KiwoomReadonlySnapshotV713IntegrationReport,
    KiwoomReadonlyDomesticStockSnapshotReport,
)


SOURCE_NAMES = (
    "OHLCV",
    "RANK",
    "OUTLIER",
    "QUOTE",
    "ORDERBOOK",
    "LIQUIDITY",
    "BASIC_INFO",
    "INVESTOR_FLOW",
    "PROGRAM_FLOW",
    "THEME_LEADERSHIP",
    "THEME_MEMBERSHIP",
    "ETF_TREND",
    "SECTOR_CAPABILITY",
)


def _gap(config_id: str, suffix: str, category: str, severity: str, message: str) -> KiwoomReadonlySnapshotGapEntry:
    return KiwoomReadonlySnapshotGapEntry(
        gap_id=f"{config_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def _latest(items):
    if not items:
        return None
    return max(items, key=lambda item: item.observed_at)


def _latest_available(items):
    values = [item.available_at for item in items if getattr(item, "available_at", None) is not None]
    if not values:
        return None
    return max(values)


def _group_keys(config: KiwoomReadonlySnapshotConfig) -> list[str]:
    keys: set[str] = set()
    for records in (
        config.canonical_ohlcv_records,
        config.canonical_rank_signals,
        config.canonical_outlier_signals,
        config.canonical_quote_records,
        config.canonical_orderbook_records,
        config.canonical_liquidity_hints,
        config.canonical_basic_info_records,
        config.canonical_investor_flow_signals,
        config.canonical_program_flow_signals,
    ):
        for record in records:
            key = getattr(record, "canonical_instrument_key", None)
            if key:
                keys.add(key)
    for membership in config.canonical_theme_membership_signals:
        if membership.component_stock_code:
            keys.add(f"{membership.component_stock_code}_KRX")
    return sorted(keys)


def _source_entries(config: KiwoomReadonlySnapshotConfig) -> list[KiwoomReadonlySnapshotSourceCoverageEntry]:
    pairs = (
        ("OHLCV", config.canonical_ohlcv_records),
        ("RANK", config.canonical_rank_signals),
        ("OUTLIER", config.canonical_outlier_signals),
        ("QUOTE", config.canonical_quote_records),
        ("ORDERBOOK", config.canonical_orderbook_records),
        ("LIQUIDITY", config.canonical_liquidity_hints),
        ("BASIC_INFO", config.canonical_basic_info_records),
        ("INVESTOR_FLOW", config.canonical_investor_flow_signals),
        ("PROGRAM_FLOW", config.canonical_program_flow_signals),
        ("THEME_LEADERSHIP", config.canonical_theme_leadership_signals),
        ("THEME_MEMBERSHIP", config.canonical_theme_membership_signals),
        ("ETF_TREND", config.canonical_etf_trend_signals),
        ("SECTOR_CAPABILITY", config.canonical_sector_capability_signals),
    )
    return [
        KiwoomReadonlySnapshotSourceCoverageEntry(
            source_name=name,
            present=bool(records),
            record_count=len(records),
        )
        for name, records in pairs
    ]


def _freshness_entries(config: KiwoomReadonlySnapshotConfig) -> list[KiwoomReadonlySnapshotFreshnessEntry]:
    pairs = (
        ("OHLCV", config.canonical_ohlcv_records),
        ("RANK", config.canonical_rank_signals),
        ("OUTLIER", config.canonical_outlier_signals),
        ("QUOTE", config.canonical_quote_records),
        ("ORDERBOOK", config.canonical_orderbook_records),
        ("LIQUIDITY", config.canonical_liquidity_hints),
        ("INVESTOR_FLOW", config.canonical_investor_flow_signals),
        ("PROGRAM_FLOW", config.canonical_program_flow_signals),
    )
    entries: list[KiwoomReadonlySnapshotFreshnessEntry] = []
    for name, records in pairs:
        latest = _latest(records)
        stale = bool(records) and any(getattr(record, "stale_flag", False) for record in records)
        reason = None
        if not records:
            reason = "SOURCE_MISSING"
        elif stale:
            reason = "STALE_FLAG_PRESENT"
        entries.append(
            KiwoomReadonlySnapshotFreshnessEntry(
                source_name=name,
                latest_observed_at=getattr(latest, "observed_at", None) if latest is not None else None,
                stale=stale,
                reason=reason,
            )
        )
    return entries


def _theme_leadership_map(config: KiwoomReadonlySnapshotConfig):
    mapping: dict[str, list] = defaultdict(list)
    for signal in config.canonical_theme_leadership_signals:
        mapping[signal.theme_group_code].append(signal)
    return mapping


def _related_etfs(config: KiwoomReadonlySnapshotConfig) -> list[str]:
    return sorted({item.etf_stock_code for item in config.canonical_etf_trend_signals if item.trend_direction == "UP"})


def _build_snapshot(config: KiwoomReadonlySnapshotConfig, key: str, conflicts: list[KiwoomReadonlySnapshotConflictEntry]):
    provider_symbol = key.removesuffix("_KRX")
    ohlcv = [record for record in config.canonical_ohlcv_records if record.canonical_instrument_key == key]
    ranks = [record for record in config.canonical_rank_signals if record.canonical_instrument_key == key]
    outliers = [record for record in config.canonical_outlier_signals if record.canonical_instrument_key == key]
    quotes = [record for record in config.canonical_quote_records if record.canonical_instrument_key == key]
    orderbooks = [record for record in config.canonical_orderbook_records if record.canonical_instrument_key == key]
    liquidity = [record for record in config.canonical_liquidity_hints if record.canonical_instrument_key == key]
    basics = [record for record in config.canonical_basic_info_records if record.canonical_instrument_key == key]
    investor = [record for record in config.canonical_investor_flow_signals if record.canonical_instrument_key == key]
    program = [record for record in config.canonical_program_flow_signals if record.canonical_instrument_key == key]
    memberships = [record for record in config.canonical_theme_membership_signals if record.component_stock_code == provider_symbol]
    leadership_map = _theme_leadership_map(config)

    latest_quote = _latest(quotes)
    latest_bar = _latest(ohlcv)
    latest_orderbook = _latest(orderbooks)
    latest_liquidity = _latest(liquidity)
    latest_basic = basics[-1] if basics else None
    latest_investor = _latest(investor)
    latest_program = _latest(program)

    reference_price = latest_quote.last_price if latest_quote and latest_quote.last_price is not None else None
    latest_close = latest_bar.close if latest_bar is not None else None
    if reference_price is not None and latest_close is not None and abs(reference_price - latest_close) > 0:
        conflicts.append(
            KiwoomReadonlySnapshotConflictEntry(
                conflict_id=f"{key}-REFERENCE-PRICE",
                canonical_instrument_key=key,
                field_name="REFERENCE_PRICE",
                left_value=str(reference_price),
                right_value=str(latest_close),
            )
        )
    if reference_price is None:
        reference_price = latest_close

    stock_names = {item.stock_name for item in [latest_quote, latest_basic, latest_investor, latest_program] if item and item.stock_name}
    stock_name = sorted(stock_names)[0] if stock_names else None
    rank_types = sorted({item.rank_type for item in ranks})
    outlier_categories = sorted({item.outlier_category for item in outliers if item.outlier_category})
    best_rank = min((item.rank for item in ranks), default=None)
    theme_names = sorted({item.theme_name for item in memberships if item.theme_name})
    leading_theme_names = sorted(
        {
            leader.theme_name
            for membership in memberships
            for leader in leadership_map.get(membership.theme_group_code, [])
        }
    )

    coverage_sources = sum(
        1
        for records in (ohlcv, ranks, outliers, quotes, orderbooks, liquidity, basics, investor, program, memberships)
        if records
    )
    total_sources = 10
    stale_flag = any(
        getattr(record, "stale_flag", False)
        for records in (ohlcv, ranks, outliers, quotes, orderbooks, liquidity, basics, investor, program)
        for record in records
    )
    quality_flags = ["READ_ONLY_ONLY", "OFFLINE_FUSION_ONLY", "KIWOOM_READONLY_SNAPSHOT"]
    if memberships:
        quality_flags.append("THEME_CONTEXT_ATTACHED")
    if latest_liquidity and latest_liquidity.price_liquidity_ready:
        quality_flags.append("LIQUIDITY_READY")

    return CanonicalDomesticStockSnapshot(
        canonical_instrument_key=key,
        provider_symbol=provider_symbol,
        stock_name=stock_name,
        available_at=config.available_at or _latest_available(quotes + ohlcv + investor + program + basics),
        quote_observed_at=getattr(latest_quote, "observed_at", None),
        last_daily_bar_at=getattr(latest_bar, "observed_at", None),
        reference_price=reference_price,
        latest_close_price=latest_close,
        percent_change=getattr(latest_quote, "percent_change", None),
        price_change=getattr(latest_quote, "price_change", None),
        spread=getattr(latest_quote, "spread", None) if latest_quote is not None else getattr(latest_orderbook, "spread", None),
        mid_price=getattr(latest_quote, "mid_price", None) if latest_quote is not None else getattr(latest_orderbook, "mid_price", None),
        last_trade_quantity=getattr(latest_quote, "last_trade_quantity", None),
        top_of_book_imbalance=getattr(latest_orderbook, "top_of_book_imbalance", None),
        latest_volume=getattr(latest_bar, "volume", None),
        liquidity_ready=bool(latest_liquidity and latest_liquidity.price_liquidity_ready),
        rank_types=rank_types,
        best_rank=best_rank,
        outlier_categories=outlier_categories,
        investor_net_buy_amount=getattr(latest_investor, "net_buy_amount", None),
        investor_net_buy_quantity=getattr(latest_investor, "net_buy_quantity", None),
        program_net_amount=getattr(latest_program, "program_net_amount", None),
        listed_shares=getattr(latest_basic, "listed_shares", None),
        market_cap=getattr(latest_basic, "market_cap", None),
        market_cap_weight=getattr(latest_basic, "market_cap_weight", None),
        theme_names=theme_names,
        leading_theme_names=leading_theme_names,
        theme_membership_count=len(memberships),
        related_etf_codes=_related_etfs(config),
        source_coverage_ratio=coverage_sources / total_sources,
        quality_flags=quality_flags,
        stale_flag=stale_flag,
        conflict_flag=any(item.canonical_instrument_key == key for item in conflicts),
        gap_reason=None if coverage_sources >= 4 else "SNAPSHOT_SOURCE_COVERAGE_PARTIAL",
    )


def build_kiwoom_readonly_domestic_stock_snapshot(config: KiwoomReadonlySnapshotConfig) -> KiwoomReadonlySnapshotComposerResult:
    for audit in config.audit_records:
        validate_kiwoom_readonly_snapshot_metadata_safety(
            {"source_path": audit.source_path, "operator_context": audit.operator_context},
            context="kiwoom readonly snapshot audit",
        )

    gaps: list[KiwoomReadonlySnapshotGapEntry] = []
    if config.available_at is None:
        gaps.append(_gap(config.config_id, "AVAILABLE-AT", "MISSING_AVAILABLE_AT", "WARNING", "available_at is missing"))

    source_entries = _source_entries(config)
    covered_source_count = sum(1 for entry in source_entries if entry.present)
    coverage_ratio = covered_source_count / len(SOURCE_NAMES)
    freshness_entries = _freshness_entries(config)
    conflicts: list[KiwoomReadonlySnapshotConflictEntry] = []
    snapshots = [_build_snapshot(config, key, conflicts) for key in _group_keys(config)]

    missing_fields: set[str] = set()
    for snapshot in snapshots:
        if snapshot.reference_price is None:
            missing_fields.add("REFERENCE_PRICE")
        if snapshot.latest_close_price is None:
            missing_fields.add("LATEST_CLOSE_PRICE")
        if snapshot.available_at is None:
            missing_fields.add("AVAILABLE_AT")
    if not snapshots:
        gaps.append(_gap(config.config_id, "SNAPSHOT", "DATA_GAP", "BLOCKING", "no canonical instrument keys were available"))

    if conflicts:
        gaps.append(_gap(config.config_id, "CONFLICT", "CONFLICT", "WARNING", "reference price differs from daily close"))
    stale_count = sum(1 for entry in freshness_entries if entry.stale)
    if stale_count:
        gaps.append(_gap(config.config_id, "STALE", "STALE_SOURCE", "WARNING", "one or more sources are stale"))
    if missing_fields:
        gaps.append(_gap(config.config_id, "COMPLETENESS", "FIELD_GAP", "WARNING", "snapshot has missing fields"))

    if not snapshots:
        readiness = KiwoomReadonlySnapshotReadiness.DATA_GAP
    elif conflicts:
        readiness = KiwoomReadonlySnapshotReadiness.CONFLICT
    elif stale_count:
        readiness = KiwoomReadonlySnapshotReadiness.STALE
    elif config.available_at is None or missing_fields:
        readiness = KiwoomReadonlySnapshotReadiness.PARTIAL
    else:
        readiness = KiwoomReadonlySnapshotReadiness.SNAPSHOT_READY

    return KiwoomReadonlySnapshotComposerResult(
        adapter_result_id=f"{config.config_id}-ADAPTER-RESULT",
        summary_report=KiwoomReadonlySnapshotSummaryReport(
            report_id=f"{config.config_id}-SUMMARY-REPORT",
            readiness=readiness,
            snapshot_count=len(snapshots),
            covered_source_count=covered_source_count,
            total_source_count=len(SOURCE_NAMES),
            message=(
                "snapshot composer produced provider-independent domestic stock snapshots"
                if readiness == KiwoomReadonlySnapshotReadiness.SNAPSHOT_READY
                else "snapshot composer completed with partial coverage, staleness, or conflicts"
            ),
        ),
        source_coverage_report=KiwoomReadonlySnapshotSourceCoverageReport(
            report_id=f"{config.config_id}-SOURCE-COVERAGE-REPORT",
            entries=source_entries,
            coverage_ratio=coverage_ratio,
        ),
        freshness_report=KiwoomReadonlySnapshotFreshnessReport(
            report_id=f"{config.config_id}-FRESHNESS-REPORT",
            entries=freshness_entries,
            stale_source_count=stale_count,
        ),
        completeness_report=KiwoomReadonlySnapshotCompletenessReport(
            report_id=f"{config.config_id}-COMPLETENESS-REPORT",
            snapshot_count=len(snapshots),
            missing_fields=sorted(missing_fields),
        ),
        conflict_report=KiwoomReadonlySnapshotConflictReport(
            report_id=f"{config.config_id}-CONFLICT-REPORT",
            entries=conflicts,
            conflict_count=len(conflicts),
        ),
        domestic_stock_snapshot_report=KiwoomReadonlyDomesticStockSnapshotReport(
            report_id=f"{config.config_id}-DOMESTIC-STOCK-SNAPSHOT-REPORT",
            snapshots=snapshots,
        ),
        v710_integration_report=KiwoomReadonlySnapshotV710IntegrationReport(
            report_id=f"{config.config_id}-V710-INTEGRATION-REPORT",
            v710_price_history_ready=bool(config.canonical_ohlcv_records),
            v710_quote_liquidity_ready=bool(config.canonical_quote_records and config.canonical_liquidity_hints),
        ),
        v712_integration_report=KiwoomReadonlySnapshotV712IntegrationReport(
            report_id=f"{config.config_id}-V712-INTEGRATION-REPORT",
            v712_theme_context_ready=bool(config.canonical_theme_membership_signals and config.canonical_theme_leadership_signals),
            v712_market_context_ready=bool(config.canonical_investor_flow_signals or config.canonical_program_flow_signals),
        ),
        v713_integration_report=KiwoomReadonlySnapshotV713IntegrationReport(
            report_id=f"{config.config_id}-V713-INTEGRATION-REPORT",
            v713_snapshot_ready=bool(snapshots),
            v713_conflict_guard_enabled=True,
        ),
        safety_report=config.safety_report,
        gap_report=KiwoomReadonlySnapshotGapReport(
            gap_report_id=f"{config.config_id}-GAP-REPORT",
            readiness=readiness,
            gap_entries=gaps + [
                _gap(
                    config.config_id,
                    "REPORT-GENERATED",
                    "READONLY_SNAPSHOT_REPORT_GENERATED",
                    "REPORT_ONLY",
                    "kiwoom readonly snapshot report generated",
                )
            ],
        ),
        audit_records=config.audit_records,
    )
