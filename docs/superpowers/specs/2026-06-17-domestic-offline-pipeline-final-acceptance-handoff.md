# v4.13 Domestic Offline Pipeline Final Acceptance and Handoff

## Scope

v4.13 is the final v4 stabilization, acceptance, documentation, and handoff
milestone.

This milestone does not add new trading logic, new runtime behavior, new
provider integration, or new execution authority. It verifies and documents
the completed v4 offline domestic pipeline as a fixture-only, non-executable
research and review stack before any future v5 work.

v4.13 remains:

- offline
- local fixture-only
- deterministic where the underlying milestone was deterministic
- domestic-track scoped for the v4 pipeline
- shadow/report/advisory context oriented
- non-executable

## Acceptance Baseline

Completed milestones covered by this acceptance pack:

- `v4.0.0-domestic-overseas-strategy-track-separation` -> `d6d430d`
- `v4.1.0-market-profile-fee-tax-fx-net-profit-calculator` -> `3df8289`
- `v4.2.0-domestic-kiwoom-realtime-data-track` -> `45b071c`
- `v4.3.0-domestic-realtime-scanner-integration` -> `8d18dee`
- `v4.4.0-domestic-scanner-candidate-evaluation-pipeline` -> `910e423`
- `v4.5.0-domestic-realtime-scanner-replay-evaluation-harness` -> `d089028`
- `v4.6.0-domestic-replay-policy-calibration-promotion-gate` -> `f46e878`
- `v4.7.0-domestic-paper-shadow-decision-journal` -> `b29f946`
- `v4.8.0-domestic-paper-shadow-outcome-labeling-review` -> `4124a25`
- `v4.9.0-domestic-shadow-review-advisory-context-pack` -> `ffba7c1`
- `v4.10.0-local-llm-training-only-distillation-dataset-pack` -> `c860b08`
- `v4.11.0-domestic-market-regime-evidence-layer` -> `0bdfbd2`
- `v4.12.0-domestic-regime-aware-offline-pipeline-integration` -> `46f368c`
- related prompt-pack foundation:
  `v3.12.0-offline-prompt-pack-advisory-task-suite` -> `656c7ea`

Known baseline from the completed milestones:

- working tree was previously reported clean
- v4.12 targeted tests passed
- v4.12 system smoke completed
- full `python3.11 -m pytest -q` was not claimed in the prior milestone
- Kiwoom/broker/API/account/order/network/LIVE/PROD paths were not used
- real market data was not fetched
- prompt packs and prompt stubs were not executed
- ML training was not run
- cloud LLMs and local model runtimes were not called

## v4 Milestone Map

### v4.0 Domestic/Overseas Strategy Track Separation

- tag: `v4.0.0-domestic-overseas-strategy-track-separation` -> `d6d430d`
- added top-level mandatory `StrategyTrack` and track-first routing
- required `StrategyTrack -> MarketProfile -> track-aware evaluation`
- prevented silent assumption sharing between `DOMESTIC_KR` and
  `OVERSEAS_US`

### v4.1 MarketProfile Fee/Tax/FX/Net-Profit Calculator

- tag: `v4.1.0-market-profile-fee-tax-fx-net-profit-calculator` -> `3df8289`
- added track-aware fee, tax, FX, and net-profit calculation models
- enforced `REPORT_ONLY` default for placeholder or needs-evidence cost
  profiles
- kept non-actionable profitability context separate from trade approval

### v4.2 Domestic Kiwoom Realtime Data Track

- tag: `v4.2.0-domestic-kiwoom-realtime-data-track` -> `45b071c`
- added domestic-only normalized realtime event track design and
  implementation boundary
- preserved `DOMESTIC_KR` only behavior and rejected `OVERSEAS_US`
- made stale realtime data default to `FAIL_CLOSED`

### v4.3 Domestic Realtime Scanner Integration

- tag: `v4.3.0-domestic-realtime-scanner-integration` -> `8d18dee`
- integrated normalized realtime events into scanner candidate generation
- introduced granular scanner states such as `SCANNER_READY`,
  `REPORT_ONLY_STALE`, and `BLOCKED_QUALITY`
- preserved v3.3-compatible `DISCOVER` / `WATCH` / `EXCLUDE` as report-level
  compatibility only

### v4.4 Domestic Scanner Candidate Evaluation Pipeline

- tag: `v4.4.0-domestic-scanner-candidate-evaluation-pipeline` -> `910e423`
- evaluated domestic scanner candidates with deterministic blocked,
  report-only, and non-actionable paths
- kept profitability, evidence, quality, and safety context explicit
- remained non-executable and scanner/report oriented only

### v4.5 Domestic Realtime Scanner Replay Evaluation Harness

- tag: `v4.5.0-domestic-realtime-scanner-replay-evaluation-harness` ->
  `d089028`
- added event-level replay traces plus derived window-level summaries
- preserved step-by-step reproducibility for scanner and evaluation behavior
- kept replay output offline diagnostics only

### v4.6 Domestic Replay Policy Calibration and Promotion Gate

- tag: `v4.6.0-domestic-replay-policy-calibration-promotion-gate` ->
  `f46e878`
- added hybrid single-run comparison plus calibration-pack aggregation
- required promotion gating at the pack level, not the single-report level
- kept all promotion output advisory and non-activating

### v4.7 Domestic Paper-Shadow Decision Journal

- tag: `v4.7.0-domestic-paper-shadow-decision-journal` -> `b29f946`
- added candidate-level non-executable journal entries
- preserved direct traceability to scanner candidates and evaluation outcomes
- kept scenario and window summaries in review layers only

### v4.8 Domestic Paper-Shadow Outcome Labeling and Review

- tag: `v4.8.0-domestic-paper-shadow-outcome-labeling-review` -> `4124a25`
- added offline outcome labeling and review over paper-shadow decisions
- kept observation and review semantics separate from execution semantics
- preserved blocked/report-only/non-actionable interpretation

### v4.9 Domestic Shadow Review Advisory Context Pack

- tag: `v4.9.0-domestic-shadow-review-advisory-context-pack` -> `ffba7c1`
- added review-report-level advisory context bundles
- required structured counts plus short deterministic summaries only
- kept the bundle non-executable and disallowed order-like wording

### v4.10 Local LLM Training-Only Distillation Dataset Pack

- tag: `v4.10.0-local-llm-training-only-distillation-dataset-pack` ->
  `c860b08`
- added training-only distillation dataset pack schema, builder, and validator
- kept records fixture-derived and non-runtime
- did not perform real dataset generation, training, or model execution

### v4.11 Domestic Market Regime Evidence Layer

- tag: `v4.11.0-domestic-market-regime-evidence-layer` -> `0bdfbd2`
- added fixture-only regime evidence and regime classification context
- kept regime evidence standalone and non-executable
- did not introduce live regime detection

### v4.12 Domestic Regime-Aware Offline Pipeline Integration

- tag: `v4.12.0-domestic-regime-aware-offline-pipeline-integration` ->
  `46f368c`
- attached v4.11 regime evidence across the existing domestic offline
  pipeline
- preserved context-only integration into candidate evaluation, replay,
  calibration, paper-shadow, outcome review, advisory context, and
  distillation dataset artifacts
- kept regime context as evidence only, not execution authority

## Design And Implementation Traceability

The v4 line included both design and implementation milestones. The approval
and spec documents live under `docs/superpowers/specs/`, while the tags above
identify the implementation-ready release points.

For v4.0 through v4.12, the tag pointers above should be treated as the
authoritative completed milestone references. Where a milestone had a prior
design-only commit, that design established the boundary and safety rules, and
the tagged implementation commit realized that scope.

v4.13 itself is a documentation and acceptance milestone. It is not a feature
implementation milestone.

## Final Architecture Summary

The full v4 offline domestic flow is:

`StrategyTrack`
-> `MarketProfile`
-> domestic realtime event fixture normalization
-> scanner candidate fixture
-> candidate evaluation
-> replay evaluation
-> calibration/promotion gate
-> paper-shadow journal
-> outcome labeling/review
-> advisory context bundle
-> training-only distillation dataset pack
-> market regime evidence
-> regime-aware offline integration

Interpreted as a v4 architecture summary:

1. `StrategyTrack` is the mandatory first routing key.
2. `MarketProfile` resolves track-specific assumptions before downstream
   evaluation.
3. Domestic realtime fixtures are normalized and quality-checked.
4. Scanner integration produces domestic scanner/report/watchlist candidates,
   not executable intents.
5. Candidate evaluation attaches profitability, evidence, safety, and
   non-actionable context.
6. Replay and calibration layers evaluate offline behavior and promotion
   evidence without activating runtime behavior.
7. Paper-shadow and outcome-review layers record and label hypothetical
   candidate outcomes without creating executable decisions.
8. Advisory context and distillation dataset layers convert offline artifacts
   into structured downstream research assets only.
9. Market regime evidence and regime-aware integration attach more context to
   the same offline stack without converting it into live operation.

## Safety Boundary Summary

The v4 line is explicitly bounded as follows:

- v4 is fixture-only, offline, shadow/report-only, and non-executable
- v4 does not place orders
- v4 does not create `OrderIntent`
- v4 does not create order drafts
- v4 does not enable execution approval
- v4 does not use `LIVE`
- v4 does not use `PROD`
- v4 does not access accounts, credentials, or tokens
- v4 does not access broker APIs or Kiwoom APIs
- v4 does not fetch real market data
- v4 does not fetch realtime FX
- v4 does not fetch news
- v4 does not connect WebSocket feeds
- v4 does not call cloud LLMs
- v4 does not call local model runtimes
- v4 does not train ML models
- v4 does not execute prompt packs or prompt stubs

These are acceptance constraints, not just implementation preferences.

## Important Clarifications

### v4.10 Distillation Dataset Scope

v4.10 did not create a real large-scale training dataset.

v4.10 implemented the dataset pack schema, builder, and validator using local
fixtures.

Real dataset generation still requires future historical data, replay outputs,
and outcome labels at greater scale.

### v4.11 And v4.12 Regime Context Scope

v4.11 and v4.12 market regime context is fixture-only evidence.

It is not live market regime detection, not realtime regime classification,
and not execution authority.

## Validation Summary

Known targeted validation from the completed milestones:

- v4.9 targeted and adjacent tests passed, but full `pytest` was not claimed
- v4.10 targeted tests and system smoke passed, but full `pytest` was not
  claimed
- v4.11 targeted tests and system smoke passed, but full `pytest` was not
  claimed
- v4.12 targeted tests and system smoke passed, but full `pytest` was not
  claimed

v4.13 full acceptance validation executed:

- `python3.11 -m pytest -q`: `1106 passed in 557.45s (0:09:17)`
- `python3.11 -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`:
  `COMPLETED`
- `git diff --check`: passed

Observed smoke safety flags:

- `real_model_called=false`
- `external_network_calls=false`
- `cloud_backend_used=false`
- `model_downloaded=false`
- `orders_created=false`
- `order_intent_created=false`
- `order_drafts_created=false`
- `execution_approval_enabled=false`
- `live_or_prod_used=false`

## Required Checks For v4.13

Required repository and tag checks:

- `git status --short`
- `git tag --points-at d6d430d`
- `git tag --points-at 3df8289`
- `git tag --points-at 45b071c`
- `git tag --points-at 8d18dee`
- `git tag --points-at 910e423`
- `git tag --points-at d089028`
- `git tag --points-at f46e878`
- `git tag --points-at b29f946`
- `git tag --points-at 4124a25`
- `git tag --points-at ffba7c1`
- `git tag --points-at c860b08`
- `git tag --points-at 0bdfbd2`
- `git tag --points-at 46f368c`
- `git tag --points-at 656c7ea`
- `python3.11 -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`
- `git diff --check`

Optional full-suite validation:

- `python3.11 -m pytest -q`

Do not claim a full-suite pass unless that command completes successfully.

## Recommended v5 Direction

v5 should not start with live trading or real order submission.

Recommended direction:

- do not start live trading
- do not start real orders
- start with read-only historical data ingestion or read-only provider adapter
  design
- keep account, broker, and order execution disabled

Possible v5 sequence:

- `v5.0 Read-Only Historical Market Data Ingestion Foundation`
- `v5.1 Historical Replay Dataset Generation from Real OHLCV Snapshots`
- `v5.2 Offline Outcome Label Generation on Historical Data`
- `v5.3 Training Dataset Export from Historical Replay Outcomes`
- `v5.4 Small Deterministic/ML Scorer Training Sandbox`

All of these should remain non-executable until explicitly approved later.

## Handoff Summary

v4.13 closes the v4 line as an accepted offline domestic pipeline foundation.

The handoff state is:

- v4.0 through v4.12 completed and tagged
- v4 remains fixture-only and non-executable
- no new feature logic added in v4.13
- v5 should begin with read-only historical data foundations, not live trading
