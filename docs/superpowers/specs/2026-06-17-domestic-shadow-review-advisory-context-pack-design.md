# v4.9 Domestic Shadow Review Advisory Context Pack Design

## Scope

v4.9 designs an offline deterministic advisory-context packaging layer for
domestic paper-shadow review evidence.

This milestone is design-only.

It does not implement runtime code, does not execute prompt packs, does not
call cloud LLMs, does not call local model runtimes, does not start paper
trading, does not call Kiwoom APIs or broker APIs, does not access accounts,
credentials, tokens, WebSocket feeds, realtime feeds, FX feeds, or order
paths, and does not create `OrderIntent`, order drafts, execution approvals,
`LIVE`, or `PROD` behavior.

v4.9 remains:

- local fixture-only
- offline
- deterministic
- domestic-track only
- advisory-context packaging only
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
- `v3.12.0-offline-prompt-pack-advisory-task-suite` -> `656c7ea`

v4.9 must preserve:

- v4.0 track-first routing and `DOMESTIC_KR` separation
- v4.1 report-only and non-actionable profitability safety
- v4.2 domestic realtime quality and stale-data fail-closed behavior
- v4.3 scanner-state non-executable semantics
- v4.4 candidate-evaluation blocked/report-only/non-actionable semantics
- v4.5 replay provenance and scenario/window traceability
- v4.6 promotion-gate evidence as supporting context only
- v4.7 candidate-level paper-shadow journaling
- v4.8 outcome labels as observation labels, not trade results
- v3.12 advisory-only prompt-pack safety boundaries

## Design Goal

v4.9 should define a local fixture-only advisory context pack layer that
converts v4.7 paper-shadow journals and v4.8 outcome review reports into safe,
non-executable advisory context bundles for future v3.12 prompt-pack
consumption.

This milestone must not call any LLM or model runtime. It only defines how
shadow review evidence can be packaged, summarized, validated, and marked as
non-actionable context.

## Architecture Position

v4.9 sits after v4.7 paper-shadow journaling and v4.8 outcome review
generation.

Required flow:

- `PaperShadowDecisionJournal`
- `PaperShadowOutcomeReviewReport`
- `AdvisoryContextPolicy`
- `ShadowReviewAdvisoryContextBundle`
- `AdvisoryContextValidationReport`
- `AdvisoryContextGapReport`

Interpretation:

- v4.7 remains responsible for candidate-level non-executable journal entries
- v4.8 remains responsible for candidate-level observation labels and
  review-level aggregations
- v4.9 consumes paper-shadow and outcome-review evidence as source material
- v4.9 packages that evidence into advisory context bundles only
- v4.9 does not produce trade decisions
- v4.9 does not execute prompt packs or LLM/model runtime calls

## Architecture Rules

The following rules are mandatory:

- `StrategyTrack` is a top-level mandatory input
- only `DOMESTIC_KR` is allowed
- `OVERSEAS_US` must fail validation
- missing or unresolved `MarketProfile` must fail closed
- v4.7 paper-shadow journal entries must remain non-executable
- v4.8 outcome labels must remain observation labels, not trade results
- advisory context bundles must not contain executable trade instructions
- advisory context bundles must not create orders, `OrderIntent`, order drafts,
  execution approval, `LIVE`, or `PROD` behavior
- advisory context bundles must not call cloud LLMs or local model runtimes

## Fixed Hybrid Bundle Unit Model

v4.9 uses a fixed hybrid bundle-unit model.

### Primary Bundle Unit

The primary `ShadowReviewAdvisoryContextBundle` unit is review-report level.

One v4.8 `PaperShadowOutcomeReviewReport` produces one primary v4.9 advisory
context bundle.

This keeps CLI behavior, validation, fixture loading, and audit references
simple at the top level.

Rules:

- one outcome review report yields one primary bundle
- the primary bundle must preserve source report ids and trace references
- the primary bundle must remain non-executable

### Mandatory Sub-Summary Sections

Scenario family, replay window, and observation horizon summaries are mandatory
sub-summary sections inside the same bundle.

These sub-summaries are not separate top-level bundles by default.

They preserve enough granularity for future prompt-pack selection while
avoiding over-fragmented advisory artifacts.

Required sub-summary sections:

- scenario family sub-summaries
- replay window sub-summaries
- observation horizon sub-summaries

Rules:

- sub-summaries must be derived from the source review report and candidate-level
  outcome labels
- sub-summaries must not replace source candidate-level evidence
- future prompt packs may select sub-summaries as context, but v4.9 itself must
  not execute prompt packs

### Summary Expression Level

v4.9 uses `structured counts + short deterministic summaries`.

Structured fields must include counts, coverage metrics, flags, source ids,
trace references, gap categories, and explicit `non_executable=true`.

Short deterministic summaries are allowed only when derived directly from
fixture data.

Rules:

- do not allow inference
- do not allow recommendations
- do not allow trade advice
- do not allow execution wording
- do not allow long prompt-ready narrative blocks

## Core Schemas

v4.9 should define these design-level schemas:

- `ShadowReviewAdvisoryContextConfig`
- `ShadowReviewAdvisoryInputSet`
- `AdvisoryContextPolicy`
- `ShadowReviewAdvisoryContextBundle`
- `AdvisoryContextEvidenceItem`
- `AdvisoryContextRiskSummary`
- `AdvisoryContextOutcomeSummary`
- `AdvisoryContextValidationReport`
- `AdvisoryContextGapReport`
- `AdvisoryContextSafetyBoundary`

All schemas must remain:

- local
- JSON fixture-driven
- deterministic
- track-aware
- non-executable

## ShadowReviewAdvisoryContextConfig

Recommended fields:

- config id
- strategy track
- market profile id
- explicit advisory-context opt-in flag
- supported advisory task names
- supported tracks
- report-level bundle mode
- sub-summary inclusion mode
- wording validation mode
- coverage sufficiency mode

Rules:

- config requires `DOMESTIC_KR`
- config must not imply prompt execution
- config must not include execution permissions

## ShadowReviewAdvisoryInputSet

Recommended fields:

- input set id
- strategy track
- market profile summary
- source paper-shadow journal id
- source paper-shadow review report id
- source outcome review report id
- source promotion gate id
- calibration pack reference
- scenario family coverage
- symbol coverage
- observation window coverage
- supported advisory task names
- data quality flags
- non-actionable marker

Rules:

- inputs are fixture-only
- missing paper-shadow journal fails closed
- missing outcome review report fails closed
- missing promotion gate reference fails closed
- missing market profile fails closed
- non-domestic track fails closed

## AdvisoryContextPolicy

Recommended fields:

- policy id
- allowed evidence item types
- forbidden wording patterns
- deterministic summary length cap
- supported advisory task compatibility mode
- non-executable enforcement mode
- gap-preservation mode
- coverage sufficiency thresholds

Rules:

- policy must be deterministic
- policy must reject executable wording
- policy must preserve blocked/report-only/non-actionable semantics
- policy must not permit prompt execution or runtime calls

## ShadowReviewAdvisoryContextBundle

Each bundle should preserve:

- `bundle_id`
- `source_outcome_review_report_id`
- `source_paper_shadow_journal_id`
- `source_promotion_gate_id`
- `strategy_track`
- `market_profile_id`
- `review_level_summary`
- `scenario_family_sub_summaries`
- `replay_window_sub_summaries`
- `observation_horizon_sub_summaries`
- `symbol_coverage_summary`
- `outcome_label_summary`
- `blocked_report_only_non_actionable_summary`
- `data_quality_summary`
- `gap_summary`
- `non_executable=true`

Additional recommended fields:

- fixture id
- supported advisory task names
- supported tracks
- evidence summaries
- risk summaries
- trace references
- source review report ids

Rules:

- bundle is review-report level primary output
- bundle sub-summaries are mandatory internal sections
- bundle and all sub-summaries remain non-executable

## AdvisoryContextEvidenceItem

v4.9 should define evidence item types such as:

- `SHADOW_DECISION_SUMMARY`
- `OUTCOME_LABEL_SUMMARY`
- `BLOCKED_REASON_SUMMARY`
- `REPORT_ONLY_REASON_SUMMARY`
- `NON_ACTIONABLE_SUMMARY`
- `SCENARIO_COVERAGE_SUMMARY`
- `SYMBOL_COVERAGE_SUMMARY`
- `RISK_OBSERVATION_SUMMARY`
- `DATA_QUALITY_SUMMARY`
- `GAP_SUMMARY`

Important rules:

- do not use evidence item types like `BUY_SIGNAL`, `SELL_SIGNAL`,
  `ENTRY_SIGNAL`, `ORDER_RECOMMENDATION`, or `EXECUTION_ADVICE`
- evidence items must remain explanatory only
- evidence items must not imply trade approval

## AdvisoryContextRiskSummary

Recommended fields:

- safety rejection counts
- blocked-safety counts
- unsafe trigger markers
- stale or low-quality data markers
- report-only persistence markers
- non-actionable persistence markers

Rules:

- risk summary is review context only
- risk summary must not imply execution readiness

## AdvisoryContextOutcomeSummary

Recommended fields:

- favorable/adverse/neutral/inconclusive counts
- blocked-confirmed count
- report-only count
- insufficient-data count
- scenario coverage count
- observation horizon coverage count
- short deterministic outcome summary text

Rules:

- summaries must be derived directly from fixture data
- summaries must not infer beyond source review evidence

## Input Design

The input layer should include:

- source paper-shadow journal id
- source paper-shadow review report id
- source outcome review report id
- promotion gate reference
- calibration pack reference
- scenario family coverage
- symbol coverage
- observation window coverage
- strategy track
- market profile id
- data quality flags
- non-actionable marker

Rules:

- inputs are fixture-only
- missing paper-shadow journal fails closed
- missing outcome review report fails closed
- missing promotion gate reference fails closed
- missing market profile fails closed
- non-domestic track fails closed

## Advisory Task Compatibility

v3.12 prompt packs may later consume this bundle only as non-executable
advisory context.

Required rules:

- prompt pack must declare supported tracks
- prompt pack must declare whether it accepts shadow review context
- prompt pack must treat advisory context as non-executable evidence
- prompt pack must not convert context bundles into trade instructions
- prompt pack execution is not part of v4.9
- no LLM or local model runtime is called in v4.9

## Context Summarization Policy

v4.9 should define deterministic fixture-only summarization rules:

- summarize favorable/adverse/neutral/inconclusive outcome counts
- summarize blocked/report-only/non-actionable counts
- summarize scenario family coverage
- summarize symbol coverage
- summarize observation horizon coverage
- summarize safety rejections
- summarize missing-data gaps
- preserve links to source candidate-level entries
- do not infer beyond fixture data
- do not create trade recommendations

The short deterministic summaries should remain brief and factual, for example:

- concentration by scenario family
- concentration by observation horizon
- recurring blocked or report-only reasons
- coverage gaps explicitly observed in the source review report

They must not include:

- directional trade suggestions
- buy/sell wording
- profitability approval
- execution language

## Safety and Fail-Closed Rules

The design must enforce:

- missing `StrategyTrack` fails
- non-`DOMESTIC_KR` track fails
- missing `MarketProfile` fails
- missing paper-shadow journal fails
- missing outcome review report fails
- missing promotion gate reference fails
- executable wording in context fails validation
- unsafe trigger attempt fails
- context bundle is always non-executable
- no advisory context state may trigger orders, `OrderIntent`, order drafts,
  execution approval, `LIVE`, or `PROD`
- no advisory context state may call cloud LLMs or local model runtimes

## Validation Report Design

v4.9 should define validation checks such as:

- track compatibility check
- market profile check
- source journal presence check
- outcome review presence check
- promotion gate reference check
- supported advisory task check
- non-executable wording check
- no order-like artifact check
- no LLM runtime check
- coverage sufficiency check
- gap report check

Recommended validation report fields:

- validation report id
- config id
- strategy track
- market profile id
- source references present marker
- supported advisory task compatibility marker
- wording validation result
- coverage sufficiency result
- non-executable result
- warnings
- block reasons

## Gap Report Design

v4.9 should define gap categories:

- `MISSING_JOURNAL`
- `MISSING_OUTCOME_REVIEW`
- `MISSING_PROMOTION_GATE`
- `MISSING_MARKET_PROFILE`
- `INSUFFICIENT_SCENARIO_COVERAGE`
- `INSUFFICIENT_SYMBOL_COVERAGE`
- `INSUFFICIENT_OBSERVATION_WINDOW_COVERAGE`
- `EXECUTABLE_WORDING_DETECTED`
- `UNSAFE_TRIGGER_DETECTED`
- `UNSUPPORTED_TRACK`
- `ADVISORY_TASK_UNSUPPORTED`

Recommended gap report fields:

- gap report id
- bundle id reference
- gap categories
- missing source counts
- insufficient coverage counts
- wording violation counts
- unsupported advisory task counts
- non-domestic rejection markers

Rules:

- gap reporting is diagnostic only
- gap reporting must not imply prompt-pack execution

## AdvisoryContextSafetyBoundary

Recommended fields:

- advisory only marker
- non-executable only marker
- order creation allowed marker
- order intent allowed marker
- order draft allowed marker
- execution approval allowed marker
- live/prod allowed marker
- cloud LLM allowed marker
- local model runtime allowed marker

Rules:

- all safety markers should remain explicit
- any violation should fail closed

## CLI Design Proposal

CLI commands should remain consistent with existing repo style:

- `domestic-shadow-advisory-context-config-validate --fixture-file ...`
- `domestic-shadow-advisory-context-build --fixture-file ... [--output-file ...]`
- `domestic-shadow-advisory-context-validate --fixture-file ... [--output-file ...]`
- `domestic-shadow-advisory-context-gap-report --fixture-file ... [--output-file ...]`
- `domestic-shadow-advisory-context-safety-report --fixture-file ... [--output-file ...]`

CLI behavior:

- `build` creates one review-report-level bundle
- `validate` checks track, market profile, source presence, non-executable
  wording, supported advisory task compatibility, and coverage sufficiency
- `gap-report` summarizes missing sources, insufficient coverage, unsupported
  tasks, unsafe wording, and non-domestic rejection
- `safety-report` confirms the bundle remains non-executable and does not
  create order-like artifacts or LLM/model runtime calls

## Fixture Design

v4.9 should design local JSON fixture examples for:

- valid advisory context config
- valid paper-shadow and outcome-review input
- valid context bundle
- insufficient scenario coverage
- insufficient symbol coverage
- insufficient observation window coverage
- missing paper-shadow journal failure
- missing outcome review report failure
- missing promotion gate failure
- missing market profile failure
- `OVERSEAS_US` rejection
- executable wording detection failure
- unsupported advisory task failure
- unsafe trigger attempt failure

## System Smoke Design

System smoke must use temporary local JSON fixtures only.

Smoke output should confirm:

- `domestic_shadow_advisory_context_fixture_run=true`
- `strategy_track_required=true`
- `domestic_kr_only=true`
- `market_profile_resolved=true`
- `paper_shadow_journal_consumed=true`
- `outcome_review_report_consumed=true`
- `advisory_context_bundle_generated=true`
- `advisory_context_validation_report_generated=true`
- `advisory_context_non_executable=true`
- `prompt_pack_executed=false`
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

## Implementation Boundary For Later

If implemented later, v4.9 may add:

- strict local fixture loaders
- deterministic bundle generation
- deterministic validation reporting
- deterministic gap reporting
- bundle-level safety reporting

v4.9 must still not add:

- prompt execution
- cloud LLM calls
- local model runtime calls
- trade recommendation generation
- order artifacts
- Kiwoom or broker connectivity
- realtime or FX network access
