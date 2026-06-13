# v2.8.0 Real-Time Market Data Foundation And Dynamic Watchlist Design

## Goal

Add a read-only, deterministic realtime market-data foundation that supports
shallow universe monitoring, rolling intraday metrics, automatic Hot Watchlist
promotion, and intraday paper/research candidate signals.

This phase does not add broker, order, account, balance, position, OrderIntent,
or live-execution functionality. It is the Realtime Monitoring stage of the
long-term execution roadmap.

## Architecture

```text
MarketUniverseRegistry
-> RealtimeMarketDataProvider
-> MarketDataEvent stream
-> symbol+region 1-minute rolling buckets
-> RollingMarketMetrics
-> DynamicWatchlist
-> persisted WatchlistEntry + RealtimeMonitorRun
-> JSON CLI result / optional summary file
```

Raw events are memory-only by default. The database stores monitor-run audit
records and the latest watchlist state, centered on rolling metrics rather
than full tick history.

No external network provider is implemented. The only providers are
deterministic mock and local replay.

## Core Models

### MarketRegion

Values: `US`, `KR`, `UNKNOWN`.

### MarketDataEventType

Values: `TRADE`, `QUOTE`, `BAR_1M`, `BAR_5M`, `SNAPSHOT`, `MARKET_STATUS`,
`UNKNOWN`.

### MarketDataEvent

Fields:

- `symbol`
- `region`
- `event_type`
- `event_time`
- `price`, `open`, `high`, `low`, `close`
- `volume`, `dollar_volume`
- `bid`, `ask`
- `source_name`
- `raw_payload_json`

Symbols are normalized to uppercase. Empty symbols are rejected by the model.
Numeric market fields remain nullable.

### RollingMarketMetrics

Fields follow the requested contract:

- last price and 1m/5m/15m return
- 1m/5m/15m volume
- 5m dollar volume
- relative volume
- 15m high/low and breakout flag
- bad-tick warning
- source and warnings

### Watchlist Models

`WatchlistStatus`: `CANDIDATE`, `HOT`, `COOLING`, `REMOVED`, `BLOCKED`.

`WatchlistEntry` stores the latest rolling metrics in `metrics_json`.

`IntradayCandidateSignal` is a memory/CLI result object containing symbol,
region, status, score, reasons, metrics, warnings, and generated time. It is
research output only and is not persisted as an order or signal-to-execution
record.

### RealtimeMonitorRun

Uses the requested lifecycle and count fields with statuses `CREATED`,
`COMPLETED`, `PARTIAL`, `FAILED`, and `DISABLED`.

## Universe Registry

`MarketUniverseRegistry` normalizes and deduplicates `(symbol, region)` entries
while preserving input order. It enforces configured `max_symbols`.

Unknown regions and empty symbols are not sent to providers. They are recorded
as blocked/warning inputs where possible.

The CLI `--symbols` value is a comma-separated list. The configured CLI region
is applied to each symbol.

## Provider Interface

```python
class RealtimeMarketDataProvider:
    provider_name: str
    region: MarketRegion

    def iter_events(
        self,
        symbols: list[str],
        start: datetime | None,
        end: datetime | None,
    ) -> Iterable[MarketDataEvent]:
        ...
```

### MockRealtimeMarketDataProvider

Generates deterministic `BAR_1M` events without network calls. For each symbol,
it creates a fixed history followed by a higher-volume/current bar so tests and
smoke runs can calculate rolling metrics and promote a subset of symbols.

### LocalReplayMarketDataProvider

Reads CSV or JSON records using existing local file helpers. It:

- validates records independently
- filters requested symbols and provider region
- filters optional start/end times
- sorts valid events by `event_time`
- never performs network calls

Invalid replay records are collected as provider warnings rather than aborting
all valid events.

## Rolling 1-Minute Buckets

Metrics are calculated independently per `(symbol, region)`.

Event timestamps are floored to one-minute buckets. `BAR_1M.volume` is used
directly. Trade events in the same minute are aggregated by summing valid
volumes and dollar volumes and updating OHLC/last price. Other event types may
update price/quote state but do not create valid volume unless volume is
present.

Events are processed in timestamp order. No metric reads future buckets.

Price selection uses `close`, then `price`, then the previous last price.
Returns compare the current last price with the latest valid price available
at or before the 1m, 5m, and 15m cutoffs. If no prior price exists, the return
is `None`.

Volume windows sum valid positive bucket volumes for the current bucket and
the preceding window. Non-positive or missing volumes do not contribute.

`high_15m` and `low_15m` use valid highs/lows or price fallbacks from the last
15 minutes.

`breakout_15m` is true when the current last price is strictly greater than the
highest valid price from preceding 15-minute buckets. The current bucket is
excluded from the breakout benchmark.

## Relative Volume Contract

```text
relative_volume =
current 1-minute bucket volume
/
average volume of up to 15 immediately preceding valid 1-minute buckets
```

Rules:

1. Calculation is independent per `(symbol, region)`.
2. The current bucket is excluded from the denominator.
3. Only preceding buckets are used; future data is never read.
4. Up to 15 previous buckets with positive volume are used.
5. Missing, blank, zero, or negative previous volumes are excluded.
6. If no valid previous bucket exists, `relative_volume=None`.
7. One previous valid bucket is sufficient; fewer than 15 adds
   `low_history_for_relative_volume`.
8. Current volume at or below zero adds `bad_volume` and produces
   `relative_volume=None`.
9. A denominator average at or below zero produces `None`.
10. Mock and replay providers use the same rolling calculator.
11. No daily average, external market data, or provider benchmark is used.

## Bad Tick Handling

An event sets `halt_or_bad_tick_warning` and adds warnings when:

- selected price is zero or negative
- supplied volume is zero or negative
- event time is earlier than the most recently processed event for that
  symbol/region

Bad-price events do not update valid price state. Non-positive volume does not
enter volume calculations. A warned symbol cannot be promoted to HOT during
that monitor run.

## Dynamic Watchlist

Default HOT eligibility uses any of:

- `return_5m_pct >= 3.0`
- `relative_volume >= 3.0`
- `dollar_volume_5m >= configured_min_dollar_volume`
- `breakout_15m` and `relative_volume >= 2.0`

`relative_volume=None` cannot satisfy relative-volume conditions.

Promotion is blocked when:

- symbol is missing
- region is UNKNOWN
- last price is missing or non-positive
- current/available volume is missing or non-positive
- bad-tick warning exists

Eligible symbols are scored deterministically:

```text
score =
max(return_5m_pct, 0)
+ min(relative_volume or 0, 10)
+ min(dollar_volume_5m / configured_min_dollar_volume, 10)
+ 2 when breakout_15m else 0
- 10 per warning
```

When configured minimum dollar volume is zero, the dollar-volume contribution
is zero.

Only the highest-scoring `max_hot_watchlist_size` eligible symbols become HOT.
Other valid observed symbols are CANDIDATE. Invalid/bad-tick symbols are
BLOCKED. Existing HOT entries not selected in a later run become COOLING.

The score is monitoring priority only. It is not a buy score or execution
instruction.

## Monitor Orchestration

`run_realtime_monitor`:

1. validates and limits the universe
2. consumes at most `max_events`
3. updates rolling metrics in memory
4. builds candidate signals
5. selects the dynamic watchlist
6. upserts watchlist entries
7. saves a `RealtimeMonitorRun`
8. optionally writes `realtime_monitor_summary.json`

Provider exceptions are isolated. If no events can be processed, status is
`FAILED`. Valid events plus provider/record errors produce `PARTIAL`.
Otherwise status is `COMPLETED`.

## Persistence

Add the requested tables:

- `realtime_monitor_runs`
- `watchlist_entries`

Repository methods:

- `save_realtime_monitor_run`
- `get_realtime_monitor_run`
- `list_realtime_monitor_runs`
- `upsert_watchlist_entry`
- `get_watchlist_entry`
- `list_watchlist_entries`

Raw market events and rolling metric histories are not persisted in v2.8.

## CLI

Add:

- `run-realtime-monitor`
- `watchlist-list`
- `realtime-runs`
- `realtime-show`

`run-realtime-monitor` supports:

- `--provider mock|local-replay`
- `--region US|KR`
- `--symbols AAPL,NVDA,TSLA`
- `--replay-file` for local replay
- `--max-events`
- `--max-symbols`
- `--max-hot-watchlist-size`
- `--min-dollar-volume-5m`
- `--output-dir`

The CLI returns JSON without traceback for expected provider/replay failures.
No network or live execution option is added.

## Safety Boundaries

- read-only market data only
- no broker/order/account/balance/position endpoint
- no OrderIntent in v2.8
- no real orders or automatic execution in v2.8
- no external network provider
- no default raw tick persistence
- rate limits represented by `max_events`, `max_symbols`, and max HOT size
- provider failures do not crash unrelated processing
- existing Provider Packs, Risk Engine, FX pipeline, and system smoke remain
  unchanged
- long-term execution safety roadmap remains documented

## Testing

Tests cover:

- models and validation
- universe normalization, dedupe, and maximum size
- deterministic mock provider
- local CSV/JSON replay, sorting, filters, and invalid-row isolation
- 1m/5m/15m returns and volumes
- relative volume with 15 previous buckets
- one previous bucket with low-history warning
- no previous valid bucket produces `None`
- current zero/negative volume warning
- denominator excludes zero/negative volume
- current bucket excluded from denominator
- mock and replay produce identical metrics for identical events
- bad price/tick handling
- HOT promotion by return, relative volume, dollar volume, and breakout
- `relative_volume=None` does not trigger its promotion rule
- max HOT size ranking
- blocked and cooling behavior
- repository round trips and upserts
- all four CLI commands
- no network calls
- no order/broker/account implementation
- existing Provider Pack regression tests
- full pytest, compileall, diff check, and system smoke
