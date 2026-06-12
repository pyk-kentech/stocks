# Signal Enrichment Layer Design

## Goal

Enrich Candidate Scanner results with local news, dilution, Toss portfolio, and
foreign/institution flow signals without external requests, realtime data,
orders, or replacement of Risk Engine hard blocks.

## Architecture

Signal file modules normalize CSV/JSON records into `TickerSignal`. The
repository stores and retrieves normalized signals. `SignalEnricher` merges
cutoff-safe DB and file signals, removes duplicates with file precedence, and
adjusts CandidateScanResult score, decision, reasons, warnings, and metadata.

## Merge And Cutoff Contract

- Use only signals whose `observed_at` date is on or before `as_of_date`.
- `scan-candidates` merges DB signals and specified file signals by default.
- `--ignore-db-signals` uses only specified file signals.
- Dedupe key: ticker, signal_type, observed_at, source_name, raw_event_type,
  title.
- File signals replace DB signals with the same dedupe key.
- Report DB, file, pre-dedupe merged, and final deduped counts in CLI output
  and ScanRun notes.

## Enrichment Contract

- Clamp adjusted candidate score to 0 through 100.
- A CRITICAL negative signal changes the candidate decision to EXCLUDE.
- A HIGH negative signal lowers only an existing INCLUDE candidate to WATCH.
- Positive signals never promote an existing EXCLUDE candidate.
- No signals leaves existing scanner behavior unchanged.
- TOSS_PORTFOLIO signal score_delta is clamped to -10 through +10.

## Storage Contract

- `ingest-signals` stores normalized file signals.
- `scan-candidates --save-signals` stores only file signals read for that scan.
- Existing DB signals are never re-saved by a scan.
- Repository-level dedupe prevents storage of an existing dedupe key and
  reports saved and skipped counts.
- Candidate scan persistence remains controlled by the existing `--save`.

## Safety

Signal Enrichment provides conservative auxiliary score adjustments. It is not
a buy recommendation and does not replace compliance, dilution, or other Risk
Engine hard blocks.
