# Operational Pipeline And Watch Loop Design

## Goal

Compose the existing Candidate Scanner, Signal Enrichment, Basket Engine,
Paper Trading, Replay Snapshot, Policy Replay, and Policy Evaluation Suite into
local paper-trading operational workflows.

## Architecture

`operational_pipeline.py` is a staged coordinator that calls existing domain
services directly. `pipeline_run.py` stores execution state, `alerts.py`
creates deterministic alerts, `pipeline_report.py` builds summaries, and
`watch_loop.py` performs explicitly requested repeated execution.

## Execution Contract

- Every invocation creates and stores a PipelineRun, then updates it through
  RUNNING to a terminal status.
- Scan failure and policy evaluation failure produce FAILED.
- No eligible candidates produces NO_CANDIDATES.
- Basket, replay, or paper failures after a successful scan produce PARTIAL.
- Exceptions create PIPELINE_ERROR alerts and are recorded in run notes/error.
- The coordinator does not place orders, call external APIs, or request
  realtime data.

## Paper Storage Contract

- `save_basket=false`, `paper_trade=true`: compute paper outcome in memory,
  do not store basket/paper rows, and record the in-memory note.
- `save_basket=true`, `paper_trade=true`: store basket, paper trades, and
  basket backtest result, and record the persisted note.
- `paper_trade=false`: skip paper calculation and storage.
- Replay snapshot persistence is independent. A replay-only basket ID may not
  exist in official basket tables and this boundary is recorded in notes.

## Policy Evaluation Contract

Use explicit ReplayRun IDs or the latest five ReplayRuns, run the existing
baseline/candidate replay batch and completed-pair suite evaluation, store the
suite, and emit a recommendation alert. Do not create promotion proposals or
change policy status.

## Watch Loop Contract

One-shot execution remains the default. The explicit watch-loop command runs
independent PipelineRuns at the requested interval until max_iterations or
KeyboardInterrupt. It never places orders.
