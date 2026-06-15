# v3.3 Market Universe / Volume Spike Discovery Layer Design

## Scope

v3.3 adds an offline deterministic market discovery scanner. It reads one
explicitly selected local JSON fixture or CSV screener export, validates a
point-in-time market snapshot, calculates reproducible price, volume-spike,
and liquidity evidence, and outputs advisory discovery candidates.

The output is research evidence only. It does not create `StrategyDecision`,
`OrderIntent`, order drafts, trade plans, baskets, orders, executions, or
execution approvals. It does not query SQLite, repository, provider, realtime,
broker, Kiwoom, account, credential, token, PROD, or LIVE paths. It does not
use external network or scraping.

v3.3 does not reuse or modify the existing persisted `candidate_scanner`,
`CandidateScanResult`, `SetupGrader`, trade-plan pipeline, or v3.2 technical
evidence scoring. Those components have broader dependencies or different
purposes. The v3.3 scanner is a separate pure fixture-to-result boundary.

## Architecture

v3.3 uses focused new modules:

- `market_discovery_models.py` defines strict config, normalized snapshot,
  evidence, classification, candidate, and result models.
- `market_discovery_fixture.py` reads and validates one exact local JSON or CSV
  input file and normalizes both formats into the same strict fixture model.
- `market_discovery_scoring.py` calculates deterministic evidence, scores,
  classifications, reasons, and warnings from normalized rows.
- `market_discovery_service.py` coordinates exact-file loading, checksum,
  scanning, ranking, and optional exact local JSON result output.

Only CLI registration, system-smoke integration, tests, and documentation may
modify existing files. Core discovery modules must not import database,
repository, provider, realtime, broker, Kiwoom, account, order, strategy
decision, credential, token, network, scraping, PROD, or LIVE modules.

No SQLite audit or storage is added. No directory discovery, environment
variable lookup, credential lookup, provider invocation, URL input, or remote
input is allowed.

## Input Modes

The scanner accepts exactly one explicit `--fixture-file` path. Supported file
extensions are `.json` and `.csv`, matched case-insensitively. Any other
extension is a JSON-safe validation error.

Both formats describe the same point-in-time screener snapshot. The loader
reads only the selected file and does not inspect its parent directory or
discover related files.

## JSON Fixture Contract

The strict JSON fixture is:

```json
{
  "schema_version": "3.3",
  "as_of_timestamp": "2026-01-01T16:00:00+00:00",
  "scanner_config": {
    "min_price": 1.0,
    "max_price": 100.0,
    "min_price_change_pct": 2.0,
    "min_volume_spike_ratio": 1.5,
    "min_dollar_volume_spike_ratio": 1.5,
    "min_average_dollar_volume_20d": 10000000,
    "max_candidates": 100
  },
  "rows": [
    {
      "ticker": "ABC",
      "observed_at": "2026-01-01T15:59:00+00:00",
      "price": 12.5,
      "previous_close": 12.0,
      "volume": 2500000,
      "average_volume_20d": 1000000,
      "average_dollar_volume_20d": 15000000
    }
  ]
}
```

Unknown fields are rejected at every model level.

## CSV Screener Export Contract

The strict CSV header is exactly:

```csv
schema_version,as_of_timestamp,min_price,max_price,min_price_change_pct,min_volume_spike_ratio,min_dollar_volume_spike_ratio,min_average_dollar_volume_20d,max_candidates,ticker,observed_at,price,previous_close,volume,average_volume_20d,average_dollar_volume_20d
```

Every CSV row repeats `schema_version`, `as_of_timestamp`, and all scanner
config fields. Repeated values must be identical across every row after strict
type parsing. `max_price` may be an empty cell on every row to mean no maximum.
A mixture of empty and non-empty `max_price` values is invalid.

CSV headers must match the required header names exactly. Missing, unknown, or
duplicate headers are validation errors. Blank lines may be ignored by the
standard CSV parser, but an otherwise empty CSV is invalid.

The CSV loader converts rows into the same normalized fixture model used by
JSON before scoring. Given equivalent normalized inputs, JSON and CSV must
produce equivalent classifications, scores, reasons, warnings, and ranking.

## Strict Validation

Validation requires:

- schema version exactly `3.3`
- timezone-aware `as_of_timestamp` and row `observed_at`
- every `observed_at <= as_of_timestamp`
- at least one row
- unique normalized ticker values
- ticker values trimmed, uppercased, and non-empty
- finite positive `price` and `previous_close`
- finite non-negative `volume`
- finite positive `average_volume_20d`
- finite positive `average_dollar_volume_20d`
- finite positive `min_price`
- optional finite `max_price` greater than or equal to `min_price`
- finite positive `min_price_change_pct`
- finite positive volume-spike thresholds
- finite positive minimum average dollar volume
- integer `max_candidates` from 1 through 1000
- no unknown JSON fields or CSV columns

Boolean values are not accepted as numeric values. NaN and infinity are not
accepted. Zero baseline values are invalid instead of producing inferred or
infinite ratios.

Invalid fixtures return JSON-safe validation errors and produce no successful
discovery result.

## Normalized Evidence Calculations

Each row is evaluated independently using only fields in that row:

```text
price_change_pct =
  (price - previous_close) / previous_close * 100

volume_spike_ratio =
  volume / average_volume_20d

dollar_volume =
  price * volume

dollar_volume_spike_ratio =
  dollar_volume / average_dollar_volume_20d
```

All calculations use full-precision Python numeric values internally. JSON
output preserves deterministic numeric values without display-only rounding
affecting classification or ranking.

The scanner does not infer missing values, use historical bars, calculate
technical indicators, inspect future data, or access data outside the selected
fixture.

## Filter Conditions

The following conditions are calculated for every row:

- `price_in_range`: price is at least `min_price` and, when configured, no
  greater than `max_price`
- `price_change_pass`: `price_change_pct >= min_price_change_pct`
- `volume_spike_pass`:
  `volume_spike_ratio >= min_volume_spike_ratio`
- `dollar_volume_spike_pass`:
  `dollar_volume_spike_ratio >= min_dollar_volume_spike_ratio`
- `liquidity_pass`:
  `average_dollar_volume_20d >= min_average_dollar_volume_20d`

Price range and liquidity are hard discovery filters. Price change, volume
spike, and dollar-volume spike are advisory momentum conditions.

## Deterministic Scoring

The discovery score is an integer from 0 through 100 with four fixed
components:

- price movement: 0 through 20
- volume spike: 0 through 30
- dollar-volume spike: 0 through 30
- liquidity: 0 through 20

Each component uses a deterministic threshold multiple:

```text
price movement:
  20 when price_change_pct >= 2 * min_price_change_pct
  10 when price_change_pct >= min_price_change_pct
   0 otherwise

volume spike:
  30 when volume_spike_ratio >= 2 * min_volume_spike_ratio
  20 when volume_spike_ratio >= min_volume_spike_ratio
   0 otherwise

dollar-volume spike:
  30 when dollar_volume_spike_ratio >= 2 * min_dollar_volume_spike_ratio
  20 when dollar_volume_spike_ratio >= min_dollar_volume_spike_ratio
   0 otherwise

liquidity:
  20 when average_dollar_volume_20d
          >= 2 * min_average_dollar_volume_20d
  10 when average_dollar_volume_20d
          >= min_average_dollar_volume_20d
   0 otherwise
```

The sum is clamped to 0 through 100. Price range is a hard filter and does not
add a separate score component.

## Classification

Allowed discovery classifications are:

- `DISCOVER`
- `WATCH`
- `EXCLUDE`

Classification is applied in this order:

1. `EXCLUDE` when `price_in_range` or `liquidity_pass` is false.
2. `DISCOVER` when price range and liquidity pass and all three advisory
   momentum conditions pass.
3. `WATCH` when price range and liquidity pass and exactly two of the three
   advisory momentum conditions pass.
4. `EXCLUDE` when fewer than two advisory momentum conditions pass.

This rule makes `WATCH` require two confirmations. A row that only satisfies
one spike or only price change is excluded rather than promoted to the
advisory candidate list.

Normalized reason codes include:

- `PRICE_IN_RANGE`
- `PRICE_BELOW_MINIMUM`
- `PRICE_ABOVE_MAXIMUM`
- `PRICE_CHANGE_CONFIRMED`
- `PRICE_CHANGE_BELOW_MINIMUM`
- `VOLUME_SPIKE_CONFIRMED`
- `VOLUME_SPIKE_BELOW_MINIMUM`
- `DOLLAR_VOLUME_SPIKE_CONFIRMED`
- `DOLLAR_VOLUME_SPIKE_BELOW_MINIMUM`
- `LIQUIDITY_CONFIRMED`
- `LIQUIDITY_BELOW_MINIMUM`

Reasons describe pass and failure evidence. Warnings are reserved for valid
but noteworthy advisory evidence and do not replace validation errors or hard
filters.

## Ranking And Candidate Limit

All evaluated rows are sorted by:

1. classification priority: `DISCOVER`, then `WATCH`, then `EXCLUDE`
2. discovery score descending
3. ticker ascending

The complete sorted evaluation list remains in the output for auditability.

The advisory candidate list contains only `DISCOVER` and `WATCH` rows, sorted
by discovery score descending and then ticker ascending. It is truncated to
`scanner_config.max_candidates`. `EXCLUDE` rows never consume the candidate
limit.

The scanner does not silently change a classification because of the candidate
limit. A valid `DISCOVER` or `WATCH` row outside the limit remains visible with
its original classification in the complete evaluation list.

## Result Models And JSON Output

Strict result models include:

- `MarketDiscoveryConfig`
- `MarketDiscoverySnapshotRow`
- `MarketDiscoveryEvidence`
- `MarketDiscoveryEvaluation`
- `MarketDiscoveryCandidate`
- `MarketDiscoveryResult`

`MarketDiscoveryResult` contains:

- schema version `3.3-result`
- fixture checksum
- fixture format, `JSON` or `CSV`
- `as_of_timestamp`
- normalized scanner config
- complete sorted evaluations
- limited advisory candidates
- summary counts for `DISCOVER`, `WATCH`, and `EXCLUDE`
- safety metadata

Safety metadata contains at least:

```json
{
  "advisory_only": true,
  "external_network_calls": false,
  "scraping_used": false,
  "strategy_decisions_created": false,
  "order_intents_created": false,
  "orders_created": false
}
```

No result field is a recommendation, strategy decision, trade plan, order
draft, OrderIntent, order, or execution request.

## CLI

Add JSON-safe commands:

```bash
python -m stock_risk_mcp.cli market-discovery-run \
  --fixture-file data/market_discovery_fixture.json

python -m stock_risk_mcp.cli market-discovery-run \
  --fixture-file data/screener_export.csv \
  --output-file outputs/market_discovery.json

python -m stock_risk_mcp.cli market-discovery-show \
  --output-file outputs/market_discovery.json
```

`market-discovery-run` reads exactly the selected local fixture and calculates
the discovery result. Without `--output-file`, it prints the strict JSON
result. With `--output-file`, it writes the strict JSON result and prints a
safe summary containing the output path and classification counts.

`market-discovery-show` reads exactly the selected local result JSON, validates
it against the strict result model, and prints it. It does not discover files
or read SQLite.

Invalid input or result files return:

```json
{
  "status": "FAILED",
  "errors": ["JSON-safe validation message"]
}
```

## Safety And Testing

Source-level tests prove the new discovery core modules have no database,
repository, provider, realtime, broker, Kiwoom, account, order,
StrategyDecision, OrderIntent, credential, token, network, scraping, PROD, or
LIVE imports or behavior.

Focused tests cover:

- deterministic evidence calculations
- deterministic scoring, classification, ranking, and candidate limiting
- strict JSON fixture validation
- strict CSV header and repeated-config validation
- equivalent JSON and CSV normalized results
- timezone-aware and as-of timestamp validation
- duplicate ticker rejection
- finite numeric and zero-baseline rejection
- hard price and liquidity filters
- JSON-safe CLI errors and exact result-file loading
- no forbidden core imports
- no external network or scraping
- offline deterministic system smoke

System smoke creates a temporary local JSON fixture, runs discovery, and
verifies `market_discovery_fixture_run=true`. It must not use CSV discovery,
directory scanning, DB/provider/realtime input, external network, or scraping.
`external_network_calls=false` remains required.

Existing v2, v3.0, v3.1, and v3.2 tests must continue to pass.

## Explicit Non-Goals

v3.3 intentionally excludes:

- live market scanning, realtime feeds, providers, APIs, scraping, and network
- SQLite audit, repository reads, and existing persisted scanner integration
- historical OHLCV technical-feature calculation
- v3.2 technical evidence or ABC grade generation
- compliance, news, dilution, flow, account, ledger, or portfolio enrichment
- strategy decisions, trade plans, baskets, replay snapshots, and paper trades
- OrderIntent, order drafts, orders, broker submission, execution, PROD, LIVE
- configurable scoring weights or automatic policy optimization

Future versions may separately define local historical-universe discovery,
technical-evidence enrichment, or explicitly separated persistence without
weakening the pure advisory discovery boundary.

## Success Criteria

The design is implemented successfully when:

- one explicit local JSON or CSV fixture produces deterministic advisory
  discovery output
- equivalent JSON and CSV fixtures produce equivalent normalized results
- validation fails closed for ambiguous, malformed, future, duplicate, or
  non-finite data
- output contains auditable evidence, classifications, ranking, and safety
  metadata
- no SQLite, repository, provider, realtime, broker, Kiwoom, account, order,
  credential, token, network, scraping, PROD, or LIVE path is used
- no StrategyDecision, OrderIntent, order draft, order, or execution is
  created
- system smoke remains offline and deterministic
