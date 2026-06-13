# Provider Normalization Layer Design

## Scope

Transform already-downloaded or local provider CSV/JSON files into the
normalized schemas accepted by the Unified Import Pipeline. Normalizers never
write business data directly to SQLite and never make network requests.

## Architecture

Each `BaseNormalizer` reads one raw file, maps configured provider columns,
validates rows, applies an optional as-of cutoff, and writes one normalized
CSV/JSON file. `provider_normalization.py` isolates source failures, aggregates
results into a `NormalizeRun`, optionally persists the audit record, and can
pass successful outputs to Unified Import.

The default registry contains generic price, news, dilution, flow, and FX CSV
normalizers. TOSS and compliance remain modeled extension points because this
phase does not define their provider-specific mapping contracts.

## Status And Storage

- `COMPLETED`: all requested sources produced output without row errors.
- `PARTIAL`: at least one output exists and another source or row failed.
- `FAILED`: inputs were requested but no usable output exists.
- `NO_INPUT`: no sources were configured.

Normalize runs and per-source results are persisted only when requested.
Normalized files are reproducible artifacts. FX import stores normalized rows
in `fx_rates`, but FX is not connected to risk sizing or operational pipeline
decisions in this phase.

## Safety

Output names must be plain file names and cannot escape the output directory.
Raw files remain unchanged. Missing required values become row errors; future
rows become skips; optional price OHLC values fall back to close with warnings.
