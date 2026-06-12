# Candidate Scanner And Universe Builder Design

## Goal

Build a local, as-of-date candidate universe from DB, file, or manual ticker
sources using existing indicator, setup, TradePlan, compliance, and basket
logic. Scanner output is a research universe, not a buy recommendation.

## Architecture

- `candidate_universe.py`: load and deduplicate DB/file/manual ticker universes
- `candidate_filters.py`: pure score, hard-exclude, and decision rules
- `candidate_scanner.py`: analyze one ticker through the existing pipeline
- `scan_pipeline.py`: orchestrate a full scan and optional persistence
- `scan_run.py`: models and downstream basket/replay conversions

All price analysis uses `AsOfPriceHistoryProvider.get_history_until`; the scan
never uses forward bars or calculates outcomes.

## Universe And Data Rules

- DB universe: distinct tickers with price history on or before `as_of_date`
- File universe: distinct tickers from the local price file
- Manual universe: only explicitly supplied tickers
- Every ticker still requires at least 120 bars on or before `as_of_date`
- Insufficient data creates an `EXCLUDE` result with a clear reason

## Candidate Analysis

For each ticker:

1. Load as-of history.
2. Calculate IndicatorSet.
3. Grade SetupSignal using fixed rules or selected StrategyPolicy.
4. Regenerate TradePlan.
5. Apply CandidateScanPolicy scoring and hard exclusions.
6. Produce CandidateScanResult.

The full regenerated TradePlan is preserved inside result metadata for
downstream basket conversion. Scan metadata also records source and policy mode.

## Compliance

Existing local `compliance_records` are used when available. Any record for a
ticker means noncompliant for scanner filtering. Missing records are treated as
unknown, produce a warning, and do not immediately exclude the ticker.

## Ranking And Limits

Apply the specified scoring and hard-exclude rules. Clamp scores to 0-100.
Sort all results by score descending. `max_candidates` limits the combined
INCLUDE/WATCH set; overflow candidates become EXCLUDE with a limit reason.

## Persistence

Add `scan_runs` and `candidate_scan_results`. Scanner output remains memory-only
unless `--save` is supplied.

## Downstream Conversion

- scan-to-basket converts saved INCLUDE results, plus WATCH when requested, from
  metadata TradePlans into BasketCandidates. It saves an official basket only
  with `--save-basket`.
- scan-to-replay-snapshot creates a replay run and ReplayCandidateSnapshots from
  saved INCLUDE results, plus WATCH when requested. It does not create an
  official basket.

Replay candidate metadata preserves scan score, decision, reasons, warnings,
setup fields, and TradePlan data.

## CLI

Add:

- `scan-candidates`
- `scan-runs`
- `scan-results`
- `scan-to-basket`
- `scan-to-replay-snapshot`

Policy selection reuses existing active/explicit policy flags. Defaults remain
fixed-rules and memory-only.

## Errors And Status

- Empty universe -> `NO_DATA`
- Per-ticker analysis error -> EXCLUDE result and continue
- Unexpected full pipeline error -> save `FAILED` run when persistence is
  enabled, then re-raise

## Safety

No external API, web request, realtime request, outcome calculation, or real
order execution is added. Compliance unknown is documented, and scan results do
not guarantee investment performance.
