# v4.6 Domestic Replay Policy Calibration and Promotion Gate Design

## Scope

v4.6 designs an offline deterministic calibration layer that compares domestic
scanner and evaluation policy configurations using v4.5 replay outputs.

This milestone is design-only.

It does not implement runtime code, does not call Kiwoom APIs, broker APIs, or
external providers, does not access accounts, credentials, tokens, WebSocket
feeds, realtime feeds, FX feeds, or order paths, and does not create
`OrderIntent`, order drafts, execution approvals, `LIVE`, or `PROD` behavior.

It also does not call cloud LLMs or local model runtimes.

v4.6 remains:

- local fixture-only
- offline
- deterministic
- domestic-track only
- calibration/reporting only
- non-executing

## Release Baseline

The completed foundations relevant to this design are:

- `v4.0.0-domestic-overseas-strategy-track-separation` -> `d6d430d`
- `v4.1.0-market-profile-fee-tax-fx-net-profit-calculator` -> `3df8289`
- `v3.12.0-offline-prompt-pack-advisory-task-suite` -> `656c7ea`
- `v4.2.0-domestic-kiwoom-realtime-data-track` -> `45b071c`
- `v4.3.0-domestic-realtime-scanner-integration` -> `8d18dee`
- `v4.4.0-domestic-scanner-candidate-evaluation-pipeline` -> `910e423`
- `v4.5.0-domestic-realtime-scanner-replay-evaluation-harness` -> `d089028`

v4.6 must preserve:

- v4.0 track-first routing and `DOMESTIC_KR` separation
- v4.1 report-only and non-actionable profitability safety
- v3.12 advisory-only prompt-pack safety
- v4.2 stale-data fail-closed and normalized event quality rules
- v4.3 scanner candidate state and compatibility reporting
- v4.4 evaluation state and compatibility reporting
- v4.5 event-level replay traces, window summaries, replay metrics, and
  non-actionable replay readiness semantics

## Architecture Position

v4.6 sits after v4.5 replay evaluation.

Required flow:

- `ReplayEvaluationReport`
- `PolicyCandidateConfig`
- `SingleReplayComparisonResult`
- `CalibrationPack`
- `CalibrationRunResult`
- `PolicyComparisonReport`
- `PromotionGateReport`

Interpretation:

- v4.5 remains responsible for generating event-level traces, window summaries,
  replay metrics, and replay readiness diagnostics
- v4.6 consumes those replay artifacts and applies fixture-only policy
  candidate comparisons
- v4.6 may compare scanner thresholds, evaluation thresholds, report-only
  policies, and regression outcomes
- v4.6 is calibration and reporting only; it is not trading, not broker
  routing, not execution planning, and not automatic policy activation

## Architecture Rules

The following rules are mandatory:

- `StrategyTrack` is a top-level mandatory input
- only `DOMESTIC_KR` is allowed
- `OVERSEAS_US` must fail validation
- missing or unresolved `MarketProfile` must fail closed
- v4.5 event-level traces and window summaries must be preserved
- v4.3 scanner states and compatibility fields must remain non-actionable
- v4.4 evaluation states and compatibility fields must remain non-actionable
- calibration outputs are offline diagnostics only
- calibration outputs must not create orders, `OrderIntent`, order drafts,
  execution approvals, `LIVE`, or `PROD` behavior
- policy candidates must not modify production policy
- promotion gate must never approve execution or production activation

## Hybrid Comparison Unit Model

v4.6 uses a hybrid comparison model with strict role separation.

### Single-Run Comparison

`SingleReplayComparisonResult` compares one `ReplayEvaluationReport` against a
baseline policy configuration and one or more candidate policy configurations.

It is used for:

- trace inspection
- threshold debugging
- scenario explanation
- supporting evidence

Rules:

- single-run comparison is supporting evidence only
- it must not be sufficient for promotion gate decisions
- it must explicitly include a non-approval marker such as
  `promotion_eligible=false`
- a single replay result must never be treated as final promotion evidence

### Calibration Pack

`CalibrationPack` is the primary evaluation unit.

It groups multiple `SingleReplayComparisonResult` instances across:

- replay runs
- windows
- scenario families
- replay fixtures

Rules:

- pack-level aggregation is required for final policy comparison and promotion
  gate evaluation
- the pack must preserve references to underlying single-run reports
- the pack must aggregate blocked counts, report-only counts,
  non-actionable counts, safety regression counts, stale-data regression
  counts, domestic-only regression counts, and coverage metrics
- the pack must require scenario diversity to reduce overfitting to a single
  replay fixture

### Promotion Gate

`PromotionGateReport` must consume only calibration-pack-level evidence.

Rules:

- promotion gate must fail closed if only a single replay result is provided
- promotion gate must fail closed if required scenario families are missing
- promotion gate must fail closed if coverage is insufficient
- promotion gate must fail closed if safety, domestic-only, stale-data,
  report-only, non-actionable, or unsafe-trigger invariants regress
- promotion output remains offline diagnostics only
- promotion gate does not enable `LIVE`, `PROD`, orders, `OrderIntent`, order
  drafts, or execution approval

## Core Schemas

v4.6 should define these design-level schemas:

- `PolicyCandidateConfig`
- `ScannerThresholdConfig`
- `EvaluationThresholdConfig`
- `CalibrationRunConfig`
- `CalibrationInputSet`
- `SingleReplayComparisonResult`
- `CalibrationPack`
- `CalibrationPackMetrics`
- `CalibrationPackCoverageReport`
- `CalibrationRunResult`
- `PolicyComparisonReport`
- `PolicyRegressionReport`
- `PromotionGateCriteria`
- `PromotionGateReport`
- `CalibrationSafetyBoundary`

All schemas must remain:

- local
- JSON fixture-driven
- deterministic
- track-aware
- advisory-only

## PolicyCandidateConfig

Recommended fields:

- candidate policy id
- candidate label
- strategy track
- market profile summary
- scanner threshold config
- evaluation threshold config
- report-only policy markers
- stale-data handling markers
- provenance markers

Rules:

- config requires `DOMESTIC_KR`
- candidate config is offline only
- candidate config must not carry production activation authority
- candidate config must not include execution permissions

## ScannerThresholdConfig

Recommended fields:

- volume spike threshold
- momentum threshold
- liquidity threshold
- watchlist add threshold
- watchlist remove threshold
- scanner candidate explosion guardrail
- stale-data handling strictness
- report-only handling policy

## EvaluationThresholdConfig

Recommended fields:

- minimum technical score
- minimum net-profit threshold
- maximum break-even move
- risk block threshold
- technical evidence missing policy
- profitability context missing policy
- compatibility mapping preservation policy

## CalibrationRunConfig

Recommended fields:

- calibration run id
- strategy track
- baseline policy id
- candidate policy ids
- comparison mode
- required scenario families
- minimum replay count
- minimum window count
- regression policy
- coverage policy
- promotion gate criteria reference

Rules:

- config requires `DOMESTIC_KR`
- missing track must fail
- unresolved market profile must fail
- config must not include production policy write access

## CalibrationInputSet

Recommended fields:

- input set id
- replay report references
- event-level trace references
- window summary references
- replay fixture provenance markers
- market profile summary
- scenario family labels
- advisory context markers

Rules:

- input set must consume explicit local replay outputs only
- input set must preserve replay provenance
- input set must not imply live feed access

## SingleReplayComparisonResult

Recommended fields:

- comparison result id
- replay report reference
- baseline policy reference
- candidate policy references
- event trace reference
- window summary reference
- metric deltas
- regression findings
- warnings
- block reasons
- `promotion_eligible`

Rules:

- `promotion_eligible` must default to `false`
- single-run comparison must be marked as supporting evidence only
- single-run comparison may explain a scenario but may not approve promotion

## CalibrationPack

Recommended fields:

- calibration pack id
- strategy track
- market profile summary
- included single-run comparison references
- included replay report references
- included scenario families
- included fixture families
- pack metrics
- pack coverage report
- regression summaries
- warnings
- block reasons

Rules:

- pack is the primary evaluation unit
- pack must preserve references to each underlying single-run comparison
- pack must aggregate per-run and per-window results without losing blocked,
  report-only, or non-actionable counts

## CalibrationPackMetrics

Recommended fields:

- runs evaluated
- windows evaluated
- scenario family count
- replay fixture count
- candidates generated
- candidates blocked
- report-only count
- non-actionable count
- watchlist add/remove count
- stale-data block count
- quality block count
- profitability block count
- technical evidence block count
- unsafe trigger rejection count
- safety regression count
- stale-data regression count
- domestic-only regression count
- coverage score
- safety score
- stability score
- false-positive proxy placeholder
- missed-opportunity proxy placeholder

## CalibrationPackCoverageReport

Recommended fields:

- required scenario families
- observed scenario families
- missing scenario families
- required replay count
- observed replay count
- required window count
- observed window count
- diversity warnings
- coverage pass/fail

Rules:

- pack coverage must fail closed if required scenario families are missing
- pack coverage must fail closed if run or window count is insufficient
- diversity must be explicit enough to avoid single-fixture overfitting

## CalibrationRunResult

Recommended fields:

- calibration run id
- baseline policy summary
- candidate policy summaries
- single-run comparison results
- calibration pack summary
- policy comparison report reference
- regression report reference
- warnings
- block reasons

## PolicyComparisonReport

Recommended fields:

- comparison report id
- baseline policy id
- candidate policy ids
- single-run summaries
- pack-level summaries
- metric deltas
- coverage summary
- safety summary
- stability summary
- recommendation notes

Rules:

- report may rank candidates for offline review
- report must not activate a production policy
- report must not imply order or execution authority

## PolicyRegressionReport

Recommended fields:

- regression report id
- safety boundary regression findings
- domestic-only regression findings
- stale-data policy regression findings
- report-only policy regression findings
- scanner candidate explosion regression findings
- blocked-candidate collapse regression findings
- technical evidence missing regression findings
- profitability context missing regression findings
- compatibility status mapping regression findings
- unsafe trigger rejection regression findings

## PromotionGateCriteria

Recommended fields:

- minimum calibration pack size
- minimum scenario family count
- minimum window coverage
- maximum safety regression count
- maximum stale-data regression count
- maximum domestic-only regression count
- maximum report-only invariant regression count
- maximum non-actionable invariant regression count
- maximum unsafe trigger regression count
- minimum safety score
- minimum coverage score
- minimum stability score

Rules:

- criteria must evaluate pack-level evidence only
- criteria must reject single-run-only inputs

## PromotionGateReport

Recommended fields:

- gate report id
- calibration pack reference
- gate criteria reference
- gate status
- status reasons
- coverage findings
- regression findings
- safety boundary
- warnings
- block reasons

Promotion gate statuses:

- `PROMOTION_REJECTED`
- `PROMOTION_REPORT_ONLY`
- `PROMOTION_READY_FOR_MORE_REPLAY`
- `PROMOTION_READY_FOR_PAPER_SHADOW`
- `PROMOTION_BLOCKED_SAFETY`
- `PROMOTION_BLOCKED_COVERAGE`
- `PROMOTION_BLOCKED_REGRESSION`

Rules:

- `PROMOTION_READY_FOR_PAPER_SHADOW` does not start paper trading
- it only means offline evidence may be sufficient to design a future
  paper-shadow milestone
- no promotion status may enable `LIVE`, `PROD`, orders, `OrderIntent`, order
  drafts, or execution approval

## CalibrationSafetyBoundary

Recommended fields:

- advisory only
- policy write disabled
- production policy changed false
- order creation allowed false
- order intent allowed false
- order draft allowed false
- execution approval allowed false
- live or prod allowed false
- broker access allowed false
- network access allowed false
- cloud llm allowed false
- model runtime allowed false

## Calibration Inputs

v4.6 calibration inputs should include:

- replay evaluation report reference
- event-level trace reference
- window summary reference
- candidate evaluation metrics
- scanner state distribution
- evaluation state distribution
- blocked counts
- report-only counts
- non-actionable counts
- watchlist add/remove counts
- quality failure counts
- profitability-blocked counts
- technical-evidence-blocked counts

Inputs must remain fixture-only and deterministic.

## Policy Candidate Design

Policy candidates may include fixture-only variations in:

- volume spike threshold
- momentum threshold
- liquidity threshold
- stale-data handling strictness
- report-only handling
- minimum technical score
- minimum net-profit threshold
- maximum break-even move
- risk block threshold
- watchlist add/remove threshold

Rules:

- policy candidates are offline configs only
- policy candidates must not modify production policy
- policy candidates must not enable `LIVE` or `PROD`
- policy candidates must not create orders
- policy candidates must not carry broker or account capabilities

## Comparison Metrics

Deterministic comparison metrics should include:

- candidates generated
- candidates blocked
- report-only count
- non-actionable count
- watchlist add/remove count
- stale-data block count
- quality block count
- profitability block count
- technical evidence block count
- unsafe trigger rejection count
- false-positive proxy placeholder
- missed-opportunity proxy placeholder
- coverage score
- safety score
- stability score

Interpretation:

- placeholder proxy metrics remain diagnostic placeholders only
- they must not be treated as realized trading performance
- safety and coverage scores outrank convenience metrics

## Regression Checks

Regression checks should include:

- safety boundary regression
- domestic-only regression
- stale-data policy regression
- report-only policy regression
- scanner candidate explosion regression
- blocked-candidate collapse regression
- technical evidence missing regression
- profitability context missing regression
- compatibility status mapping regression
- unsafe trigger rejection regression

Rules:

- any required safety regression must fail closed
- regressions must be explicit in both single-run evidence and pack-level
  aggregation
- pack-level regression outcomes override any favorable single-run result

## Safety and Fail-Closed Rules

The following fail-closed rules are mandatory:

- missing `StrategyTrack` fails
- non-`DOMESTIC_KR` track fails
- missing `MarketProfile` fails
- missing replay report fails
- missing event-level trace fails
- missing window summary fails
- stale/report-only/non-actionable candidates must remain non-actionable
- unsafe trigger attempts fail
- calibration output is always non-actionable
- single-run-only evidence cannot pass the promotion gate
- missing required scenario family fails the promotion gate
- no calibration state may trigger orders, `OrderIntent`, order drafts,
  execution approval, `LIVE`, or `PROD`

## Integration With Previous Milestones

v4.6 should reference:

- v4.5 replay reports, event-level traces, window summaries, replay metrics,
  and promotion-readiness outputs as upstream evidence only
- v4.4 candidate evaluation reports and state distributions for evaluation
  threshold calibration
- v4.3 scanner candidates and scanner-state distributions for scanner threshold
  calibration
- v4.2 normalized domestic realtime events and stale-data rules for replay
  quality and regression checks
- v4.1 profitability checks for net-profit threshold calibration, while
  preserving report-only and non-actionable restrictions
- v3.12 advisory context as non-runtime explanatory context only

## CLI Design Proposal

Commands should remain consistent with the existing repo style:

- `domestic-calibration-config-validate --fixture-file ...`
- `domestic-calibration-run --fixture-file ... [--output-file ...]`
- `domestic-policy-compare --fixture-file ... [--output-file ...]`
- `domestic-promotion-gate-report --fixture-file ... [--output-file ...]`

Expected behavior:

- validation returns config and coverage readiness only
- calibration run returns single-run comparisons plus pack-level summaries
- policy compare returns baseline/candidate metric deltas and regression notes
- promotion gate report returns pack-level gate status only

## Fixture Design

v4.6 should define local JSON fixture examples for:

- valid calibration config
- valid replay report input
- two policy candidate comparison
- stricter threshold candidate
- looser threshold candidate
- report-only candidate policy
- safety regression failure
- coverage regression failure
- missing track failure
- missing market profile failure
- missing replay report failure
- `OVERSEAS_US` rejection
- unsafe trigger rejection
- promotion-ready-for-more-replay case
- promotion-ready-for-paper-shadow case

Fixture expectations:

- each fixture must preserve explicit replay provenance
- each fixture must stay domestic-only
- promotion-ready fixtures must still remain non-actionable

## System Smoke Design

System smoke must use temporary local JSON fixtures only.

Smoke output must confirm:

- `domestic_calibration_fixture_run=true`
- `strategy_track_required=true`
- `domestic_kr_only=true`
- `market_profile_resolved=true`
- `replay_evaluation_report_consumed=true`
- `policy_candidate_comparison_generated=true`
- `promotion_gate_report_generated=true`
- `kiwoom_api_called=false`
- `broker_api_called=false`
- `credentials_accessed=false`
- `external_network_calls=false`
- `orders_created=false`
- `live_or_prod_used=false`
- `cloud_llm_called=false`
- `model_runtime_called=false`

## Implementation Boundary For Later

Allowed in a future v4.6 implementation:

- local JSON calibration fixture loader
- single-run replay comparison engine
- calibration pack aggregator
- policy comparison report generator
- regression checker
- promotion gate report generator
- offline deterministic system smoke

Forbidden in v4.6:

- real provider integration
- replay feed fetching
- broker or Kiwoom calls
- account or credential access
- order creation
- `OrderIntent` creation
- order drafts
- execution approval
- `LIVE` or `PROD` activation
- cloud LLM calls
- local model runtime calls
- production policy changes
