# v4.12 Domestic Regime-Aware Offline Pipeline Integration Design

## Scope

v4.12 designs an offline deterministic regime-aware integration layer for the
domestic Korean offline pipeline.

This milestone is design-only.

It does not implement runtime code, does not fetch real market data, does not
call Kiwoom APIs or broker APIs, does not access accounts, credentials,
tokens, WebSocket feeds, realtime feeds, FX feeds, or order paths, does not
create `OrderIntent`, order drafts, or execution approvals, does not use
`LIVE` or `PROD`, does not train ML models, does not call cloud LLMs or local
model runtimes, and does not execute prompt packs or prompt stubs.

v4.12 remains:

- local fixture-only
- offline
- deterministic
- domestic-track only
- integration and context-attachment only
- non-executable

## Release Baseline

The completed foundations relevant to this design are:

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
- `v3.12.0-offline-prompt-pack-advisory-task-suite` -> `656c7ea`

v4.12 must preserve:

- v4.0 track-first routing and `DOMESTIC_KR` separation
- v4.1 report-only and non-actionable profitability safety
- v4.2 stale-data fail-closed posture
- v4.3 non-executable scanner semantics
- v4.4 candidate-evaluation blocked/report-only/non-actionable semantics
- v4.5 replay provenance and replay-window traceability
- v4.6 pack-level calibration and promotion-gate safety
- v4.7 paper-shadow candidate-level non-executable journaling
- v4.8 observation outcomes, not execution results
- v4.9 advisory-context bundle safety boundaries
- v4.10 training-only distillation dataset safety boundaries
- v4.11 market regime evidence as standalone non-executable context
- v3.12 advisory-only prompt-pack safety boundaries

## Design Goal

v4.12 should define a local fixture-only integration layer that attaches v4.11
`MarketRegimeReport` evidence to the existing v4 domestic offline pipeline.

This milestone should make regime context available to:

- candidate evaluation
- replay
- calibration
- paper-shadow journal
- outcome review
- advisory context bundles
- distillation dataset records

This milestone must remain context-only. It must not convert regime labels into
trade approval, order intent, or execution behavior.

## Architecture Position

v4.12 sits after v4.11.

Interpretation:

- v4.11 produced standalone market regime evidence and classification
- v4.12 wires that evidence into existing v4 offline artifacts
- v4.12 is still fixture-only integration, not live operation
- v4.12 is not a trading layer
- v4.12 does not introduce new execution authority

Required flow:

- `MarketRegimeReport`
- `RegimeAwareContextReference`
- `CandidateEvaluationReport`
- `ReplayEvaluationReport`
- `CalibrationPack`
- `PaperShadowDecisionJournal`
- `PaperShadowOutcomeReviewReport`
- `ShadowReviewAdvisoryContextBundle`
- `DistillationDatasetPack`

## Architecture Rules

The following rules are mandatory:

- `StrategyTrack` is a top-level mandatory input
- only `DOMESTIC_KR` is allowed
- `OVERSEAS_US` must fail validation
- missing or unresolved `MarketProfile` must fail closed
- missing required `MarketRegimeReport` must fail closed unless explicitly
  configured as report-only integration mode
- regime context must remain evidence and context only
- regime labels must not become buy, sell, entry, exit, or order signals
- regime-aware outputs must not create orders, `OrderIntent`, order drafts,
  execution approval, `LIVE`, or `PROD` behavior
- regime-aware outputs must not call cloud LLMs or local model runtimes
- regime-aware outputs must not train ML models

## Fixed Hybrid Integration Unit Model

v4.12 uses a fixed hybrid integration-unit model.

### Top-Level Unit

The top-level unit is `one integration fixture -> one RegimeAwareIntegrationReport`.

This keeps CLI behavior, validation, audit references, and fixture loading
simple at the top level.

Rules:

- one integration fixture yields one primary integration report
- the top-level report must remain non-executable
- the top-level report must preserve source ids and traceability

### Mandatory Sub-Context Sections

The primary report must include mandatory downstream sub-context sections for:

- candidate evaluation
- replay
- calibration
- paper-shadow
- outcome review
- advisory context
- distillation context

These are not separate top-level reports by default.

Rules:

- sub-context sections preserve downstream traceability
- sub-context sections must not replace source artifacts
- sub-context sections remain non-executable

## Missing Regime Report Policy

v4.12 uses a fixed default rule for missing required regime context.

Default behavior:

- missing required `MarketRegimeReport` is `FAIL_CLOSED`

Exception:

- only an explicit `report-only integration mode` may allow a non-actionable,
  non-executable fallback summary for missing regime context

Rules:

- report-only integration is opt-in only
- report-only integration must not silently pass as normal integration
- report-only integration must not remove warnings or missing-context markers

## Hybrid Coverage Rule

v4.12 uses a fixed hybrid coverage rule for
`INSUFFICIENT_REGIME_COVERAGE`.

Coverage is not satisfied by artifact presence alone and not satisfied by
regime-label diversity alone.

Coverage must include:

- required artifact presence
- required sub-context section presence
- minimum regime attachment coverage per downstream section

Interpretation:

- a single attached regime label does not imply complete coverage
- missing regime attachment for required downstream sections must remain visible
- partial integration is not treated as complete integration

## Core Schemas

v4.12 should define these design-level schemas:

- `RegimeAwareIntegrationConfig`
- `RegimeAwareInputSet`
- `RegimeAwareContextReference`
- `RegimeAwareCandidateEvaluationContext`
- `RegimeAwareReplayContext`
- `RegimeAwareCalibrationContext`
- `RegimeAwarePaperShadowContext`
- `RegimeAwareOutcomeReviewContext`
- `RegimeAwareAdvisoryContext`
- `RegimeAwareDistillationContext`
- `RegimeAwareIntegrationReport`
- `RegimeAwareGapReport`
- `RegimeAwareSafetyBoundary`

All schemas must remain:

- local
- JSON fixture-driven
- deterministic
- track-aware
- non-executable

## RegimeAwareIntegrationConfig

Recommended fields:

- config id
- strategy track
- market profile id
- explicit regime-aware integration opt-in flag
- report-only integration mode
- stale regime context policy
- missing regime report policy
- coverage sufficiency mode
- wording validation mode
- non-executable enforcement mode

Rules:

- config requires `DOMESTIC_KR`
- config must not imply execution authority
- config must not grant order or approval permissions

## RegimeAwareInputSet

Recommended fields:

- input set id
- strategy track
- market profile summary
- source market regime report
- source market regime classification
- primary regime label
- secondary regime labels
- evidence strength bucket
- data quality flags
- missing evidence summary
- stale evidence summary
- report-only marker
- source candidate evaluation report ids
- source replay report ids
- source calibration pack ids
- source paper-shadow journal ids
- source outcome review report ids
- source advisory context bundle ids
- source distillation dataset pack ids

Rules:

- inputs are fixture-only
- missing regime report fails closed unless explicitly report-only
- missing market profile fails closed
- non-domestic track fails closed
- stale regime context fails closed unless explicitly report-only
- executable wording fails validation

## RegimeAwareContextReference

v4.12 reuses the v4.11 context-reference idea but adapts it for integration.

Recommended fields:

- context reference id
- source market regime report id
- source market regime classification id
- primary regime label
- secondary regime labels
- evidence strength bucket
- data quality flags
- stale summary
- missing evidence summary
- report-only marker
- non-executable marker
- strategy track
- market profile id
- source trace references

Rules:

- reference remains evidence-only
- reference must not become a trade or order signal
- reference must preserve report-only and stale markers

## RegimeAwareCandidateEvaluationContext

This context attaches regime evidence to v4.4 candidate evaluation reports.

Recommended fields:

- candidate evaluation report id
- source regime report id
- primary regime label
- secondary regime labels
- evidence strength bucket
- data quality flags
- report-only marker
- non-actionable marker

Rules:

- regime context may explain why a candidate is watch-only, report-only, or
  blocked
- regime context must not turn a blocked candidate into an approved candidate
- regime context must not weaken v4.4 safety gates

## RegimeAwareReplayContext

This context attaches regime evidence to v4.5 replay windows.

Recommended fields:

- replay window id
- source regime report id
- primary regime label
- secondary regime labels
- evidence strength bucket
- stale regime marker
- report-only regime marker

Rules:

- replay summaries may group metrics by regime label
- grouping must be derived from fixture reports only
- replay output remains non-actionable

## RegimeAwareCalibrationContext

This context attaches regime evidence to v4.6 calibration packs.

Recommended fields:

- calibration pack id
- candidates generated by regime
- blocked candidates by regime
- report-only candidates by regime
- favorable or adverse proxy by regime when prior outcome fixtures allow it
- safety regression by regime
- coverage by regime

Rules:

- calibration gate remains pack-level
- regime-aware calibration must not enable promotion from a single regime slice
- promotion gate remains non-executable

## RegimeAwarePaperShadowContext

This context attaches regime evidence to v4.7 paper-shadow journal entries.

Recommended fields:

- journal entry id
- candidate id
- source regime report id
- primary regime label
- secondary regime labels
- regime context marker
- non-executable marker

Rules:

- paper-shadow decisions remain candidate-level, non-executable entries
- regime labels must not become shadow buy, sell, or entry labels

## RegimeAwareOutcomeReviewContext

This context attaches regime evidence to v4.8 outcome review.

Recommended fields:

- favorable count by regime
- adverse count by regime
- neutral count by regime
- inconclusive count by regime
- report-only count by regime
- blocked-confirmed count by regime
- insufficient-data count by regime

Rules:

- regime-aware outcome review describes observation outcomes only
- it is not realized P/L
- it is not account return
- it is not execution result

## RegimeAwareAdvisoryContext

This context attaches regime evidence to v4.9 advisory bundles.

Recommended fields:

- regime distribution summary
- outcome label summary by regime
- blocked, report-only, non-actionable summary by regime
- data quality summary by regime
- short deterministic regime summary

Rules:

- summaries must be fixture-derived
- summaries must not recommend trades
- summaries must remain non-executable
- prompt packs are not executed

## RegimeAwareDistillationContext

This context attaches regime evidence to v4.10 distillation dataset records.

Recommended fields:

- primary regime label feature
- secondary regime label features
- regime evidence strength feature
- regime data quality feature
- regime report-only marker
- regime stale marker
- regime-conditioned label distribution metadata

Rules:

- dataset records remain training-only
- dataset records are not runtime decisions
- no LLM training or inference
- no ML training

## RegimeAwareIntegrationReport

The primary integration report should include:

- report id
- fixture id
- strategy track
- market profile id
- source regime report id
- top-level regime-aware context reference
- candidate evaluation sub-context
- replay sub-context
- calibration sub-context
- paper-shadow sub-context
- outcome review sub-context
- advisory sub-context
- distillation sub-context
- coverage summary
- report-only marker
- non-executable marker
- source trace references

Rules:

- one integration fixture yields one primary report
- the report remains non-executable
- the report describes attachment state, not trade approval

## RegimeAwareGapReport

Recommended gap categories:

- `MISSING_MARKET_REGIME_REPORT`
- `MISSING_REGIME_CLASSIFICATION`
- `MISSING_PRIMARY_REGIME_LABEL`
- `STALE_REGIME_CONTEXT`
- `REPORT_ONLY_REGIME_CONTEXT`
- `INSUFFICIENT_REGIME_COVERAGE`
- `REGIME_CONTEXT_TRACK_MISMATCH`
- `REGIME_CONTEXT_MARKET_PROFILE_MISMATCH`
- `UNSUPPORTED_TRACK`
- `EXECUTABLE_WORDING_DETECTED`
- `UNSAFE_TRIGGER_DETECTED`

Recommended report fields:

- report id
- fixture id
- strategy track
- market profile id
- gap categories
- missing regime context count
- stale regime context count
- coverage failure count
- wording violation count
- unsupported-track count

## RegimeAwareSafetyBoundary

Recommended fields:

- context-only
- non-executable-only
- order creation allowed
- order-intent creation allowed
- order-draft creation allowed
- execution approval allowed
- cloud-llm allowed
- model-runtime allowed
- ml-training allowed
- live-or-prod allowed

Required values:

- context-only = true
- non-executable-only = true
- order creation allowed = false
- order-intent creation allowed = false
- order-draft creation allowed = false
- execution approval allowed = false
- cloud-llm allowed = false
- model-runtime allowed = false
- ml-training allowed = false
- live-or-prod allowed = false

## Safety and Fail-Closed Rules

The following rules are mandatory:

- missing `StrategyTrack` fails
- non-`DOMESTIC_KR` track fails
- missing `MarketProfile` fails
- missing regime report fails closed unless report-only integration is
  explicitly configured
- stale regime context fails closed unless report-only integration is explicitly
  configured
- regime track mismatch fails
- regime market profile mismatch fails
- executable wording fails
- unsafe trigger attempt fails
- regime context is always non-executable
- no regime-aware state may trigger orders, `OrderIntent`, order drafts,
  execution approval, `LIVE`, or `PROD`
- no regime-aware state may call cloud LLMs or local model runtimes
- no regime-aware state may train ML models

## CLI Design Proposal

Recommended CLI commands:

- `domestic-regime-aware-integration-config-validate --fixture-file ...`
- `domestic-regime-aware-integration-build --fixture-file ... [--output-file ...]`
- `domestic-regime-aware-integration-report --fixture-file ... [--output-file ...]`
- `domestic-regime-aware-gap-report --fixture-file ... [--output-file ...]`
- `domestic-regime-aware-safety-report --fixture-file ... [--output-file ...]`

Expected behavior:

- `config-validate` validates fixture structure and fail-closed preconditions
- `build` produces the integrated report-level artifact
- `report` produces the final integration report view
- `gap-report` produces integration gap diagnostics
- `safety-report` confirms the integration remains non-executable

## Fixture Design

v4.12 should define local JSON fixture examples for:

- valid regime-aware integration config
- valid regime-aware candidate evaluation context
- valid regime-aware replay context
- valid regime-aware calibration context
- valid regime-aware paper-shadow context
- valid regime-aware outcome review context
- valid regime-aware advisory context
- valid regime-aware distillation context
- missing regime report failure
- stale regime context failure
- report-only regime context
- regime track mismatch failure
- regime market profile mismatch failure
- missing primary regime label failure
- insufficient regime coverage
- missing track failure
- missing market profile failure
- `OVERSEAS_US` rejection
- executable wording detection failure
- unsafe trigger attempt failure

## System Smoke Design

System smoke must use temporary local JSON fixtures only.

Smoke output should confirm:

- `domestic_regime_aware_integration_fixture_run=true`
- `strategy_track_required=true`
- `domestic_kr_only=true`
- `market_profile_resolved=true`
- `market_regime_report_consumed=true`
- `regime_aware_context_reference_generated=true`
- `regime_aware_integration_report_generated=true`
- `regime_aware_gap_report_generated=true`
- `regime_context_non_executable=true`
- `kiwoom_api_called=false`
- `broker_api_called=false`
- `credentials_accessed=false`
- `external_network_calls=false`
- `orders_created=false`
- `order_intent_created=false`
- `order_drafts_created=false`
- `execution_approval_enabled=false`
- `live_or_prod_used=false`
- `cloud_llm_called=false`
- `model_runtime_called=false`
- `ml_training_run=false`
- `real_market_data_fetched=false`

## Implementation Boundary for Later

Allowed for a later implementation milestone:

- local JSON fixture loader
- deterministic regime-context attachment
- deterministic coverage validation
- integration report generator
- gap report generator
- safety report generator
- offline system smoke

Forbidden for a later implementation milestone:

- real market data fetch
- Kiwoom or broker API calls
- account or credential access
- WebSocket connection
- realtime FX fetch
- news fetch
- order submission
- `OrderIntent`
- order draft creation
- execution approval
- `LIVE` or `PROD`
- cloud LLM calls
- local model runtime calls
- prompt pack or prompt stub execution
- ML training

