from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from stock_risk_mcp.dynamic_watchlist import DynamicWatchlist, WatchlistPromotionRule
from stock_risk_mcp.market_universe import MarketUniverseRegistry
from stock_risk_mcp.realtime_market_data import (
    MarketRegion,
    RealtimeMonitorResult,
    RealtimeMonitorRun,
    RealtimeMonitorRunStatus,
)
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.rolling_market_metrics import RollingMarketMetricsCalculator


def run_realtime_monitor(
    repository: RiskRepository,
    provider,
    symbols: list[str],
    region: MarketRegion,
    *,
    output_dir: str | Path | None = None,
    max_events: int = 10_000,
    max_symbols: int = 500,
    max_hot_watchlist_size: int = 20,
    min_dollar_volume_5m: float = 1_000_000,
    as_of: datetime | None = None,
) -> RealtimeMonitorResult:
    now = as_of or datetime.now()
    universe = MarketUniverseRegistry(max_symbols=max_symbols).register(symbols, region)
    warnings = list(universe.warnings)
    errors: list[str] = []
    calculator = RollingMarketMetricsCalculator()
    processed = 0
    try:
        for event in provider.iter_events(universe.symbols, None, as_of):
            if processed >= max_events:
                warnings.append(f"max_events limit applied: {max_events}")
                break
            calculator.add(event)
            processed += 1
    except Exception as exc:
        errors.append(str(exc))
    warnings.extend(getattr(provider, "warnings", []))

    metrics = []
    for symbol in universe.symbols:
        try:
            metrics.append(calculator.latest(symbol, region))
        except LookupError:
            warnings.append(f"no valid events for {symbol}")
    previous = {entry.symbol: entry for entry in repository.list_watchlist_entries()}
    entries, signals = DynamicWatchlist(WatchlistPromotionRule(
        min_dollar_volume_5m=min_dollar_volume_5m,
        max_hot_watchlist_size=max_hot_watchlist_size,
    )).evaluate(metrics, previous)
    for entry in entries:
        repository.upsert_watchlist_entry(entry)

    if processed == 0:
        status = RealtimeMonitorRunStatus.FAILED
    elif errors or warnings:
        status = RealtimeMonitorRunStatus.PARTIAL
    else:
        status = RealtimeMonitorRunStatus.COMPLETED
    run = RealtimeMonitorRun(
        as_of=now,
        status=status,
        provider_name=provider.provider_name,
        universe_count=len(universe.symbols),
        processed_event_count=processed,
        candidate_count=len(entries),
        hot_watchlist_count=sum(entry.status.value == "HOT" for entry in entries),
        warnings=list(dict.fromkeys(warnings)),
        errors=errors,
        completed_at=datetime.now(),
    )
    repository.save_realtime_monitor_run(run)
    result = RealtimeMonitorResult(run=run, watchlist_entries=entries, signals=signals)
    if output_dir is not None:
        try:
            output_path = Path(output_dir) / "realtime_monitor_summary.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
            result = result.model_copy(update={"output_path": str(output_path)})
        except Exception as exc:
            updated_run = run.model_copy(update={"warnings": [*run.warnings, f"failed to write summary: {exc}"]})
            result = result.model_copy(update={"run": updated_run})
    return result
