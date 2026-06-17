# v4.4 Domestic Scanner Candidate Evaluation Pipeline Design

## Scope

v4.4 designs an offline deterministic evaluation layer that consumes v4.3
domestic scanner candidates and evaluates them with technical evidence,
market-profile context, profitability context, and safety gates.

This milestone is design-only.

It does not implement runtime code, does not call Kiwoom APIs, does not call
broker APIs, does not access accounts, credentials, tokens, WebSocket feeds,
realtime feeds, FX feeds, or order paths, and does not create `OrderIntent`,
order drafts, execution approvals, `LIVE`, or `PROD` behavior.

It also does not call cloud LLMs or local model runtimes.

v4.4 remains:

- local fixture-only
- offline
- deterministic
- domestic-track only
- evaluation/reporting only
- non-executing

## Release Baseline

The completed foundations relevant to this design are:

- `v4.0.0-domestic-overseas-strategy-track-separation` -> `d6d430d`
- `v4.1.0-market-profile-fee-tax-fx-net-profit-calculator` -> `3df8289`
- `v3.12.0-offline-prompt-pack-advisory-task-suite` -> `656c7ea`
- `v4.2.0-domestic-kiwoom-realtime-data-track` -> `45b071c`
- `v4.3.0-domestic-realtime-scanner-integration` -> `8d18dee`

v4.4 must preserve:

- v4.0 track-first routing
- v4.1 report-only and non-actionable profitability safety
- v3.12 advisory-only prompt-pack safety
- v4.2 realtime quality and stale-data fail-closed policy
- v4.3 scanner candidate safety and watchlist-only semantics

## Architecture Position

v4.4 sits after v4.3 scanner candidate generation.

Required flow:

- `StrategyTrack`
- `MarketProfile`
- `ScannerCandidate`
- `TechnicalEvidenceContext`
- `TrackAwareProfitabilityCheck`
- `CandidateEvaluationReport`

Interpretation:

- v4.3 remains responsible for normalized domestic realtime event conversion,
  scanner candidate generation, and watchlist plan proposals
- v4.4 consumes the produced scanner candidate report as its primary input
- v4.4 may reference v3.2-style technical evidence only as fixture context
- v4.4 must respect v4.1 profitability constraints and report-only modes
- v4.4 may expose non-runtime advisory context markers for later v3.12 prompt
  pack consumption

v4.4 is evaluation and reporting only. It is not trading, not broker routing,
not execution planning, and not order creation.

## Architecture Rules

The following rules are mandatory:

- `StrategyTrack` is a top-level mandatory input
- only `DOMESTIC_KR` is allowed
- `OVERSEAS_US` must fail validation
- missing or unresolved `MarketProfile` must fail closed
- v4.3 scanner candidate quality, staleness, and non-actionable flags must be
  preserved
- v4.1 profitability context must be respected
- v3.2 technical evidence may be referenced only as fixture context
- v3.12 advisory prompt-pack context may be referenced only as non-runtime
  context
- no candidate evaluation result may create orders, `OrderIntent`, order
  drafts, execution approvals, `LIVE`, or `PROD` behavior

## Core Schemas

v4.4 should define these design-level schemas:

- `CandidateEvaluationConfig`
- `CandidateEvaluationInput`
- `TechnicalEvidenceContext`
- `CandidateTechnicalScore`
- `CandidateProfitabilityScore`
- `CandidateRiskSignal`
- `CandidateEvaluationDecision`
- `CandidateEvaluationReport`
- `CandidateEvaluationSafetyBoundary`
- `CandidateEvaluationGapReport`

All schemas must remain:

- local
- JSON fixture-driven
- deterministic
- track-aware
- advisory-only

## CandidateEvaluationConfig

Recommended fields:

- config id
- strategy track
- report-only mode flag
- minimum technical score threshold
- minimum profitability score threshold
- minimum risk acceptance threshold
- stale evaluation policy
- missing evidence policy
- scanner compatibility carry-forward policy
- evaluation compatibility mapping policy

Rules:

- config requires `DOMESTIC_KR`
- missing track must fail
- unresolved market profile must fail
- config must not include execution permissions

## CandidateEvaluationInput

Recommended fields:

- input id
- strategy track
- resolved market profile
- scanner candidate report reference or embedded scanner report
- selected scanner candidate ids
- technical evidence context
- profitability context
- advisory context markers
- fixture source markers

Rules:

- input requires v4.3 scanner candidates
- scanner candidate source must preserve v4.3 state and compatibility fields
- fixture provenance must remain explicit

## TechnicalEvidenceContext

Recommended fields:

- evidence id
- ticker
- MACD evidence summary
- RSI evidence summary
- moving-average evidence summary
- HMA evidence summary
- ATR or stop-distance evidence summary
- volume evidence summary
- divergence evidence summary
- setup grade
- evidence freshness
- missing evidence flags

Rules:

- v4.4 may consume technical evidence only as provided local fixture context
- v4.4 must not fetch or recalculate real technical data
- missing evidence policy must be explicit

## CandidateTechnicalScore

Recommended fields:

- ticker
- score
- contributing indicators
- missing indicators
- setup grade
- evidence freshness
- evaluation warnings

This score must remain an offline deterministic evaluation artifact only.

## CandidateProfitabilityScore

Recommended fields:

- ticker
- profitability context status
- expected net profit
- expected net return percentage
- break-even move
- cost-aware minimum target move
- score
- blocked reason if non-actionable

Rules:

- placeholder or needs-evidence profiles must remain non-actionable by default
- report-only profitability context must remain non-approving

## CandidateRiskSignal

Recommended fields:

- ticker
- stale risk
- scanner quality risk
- profitability risk
- technical evidence risk
- unsafe trigger risk
- overall risk classification

This signal is evaluation-only and must not be interpreted as an execution
decision.

## CandidateEvaluationDecision

Recommended fields:

- candidate id
- internal evaluation state
- scanner compatibility status
- evaluation compatibility status
- technical score
- profitability score
- risk signal
- warnings
- block reasons
- actionable approval flag, always false in v4.4

## CandidateEvaluationReport

Recommended fields:

- report id
- strategy track
- market profile summary
- candidate count
- evaluation-ready count
- watch-only count
- report-only count
- blocked count
- rejected count
- gap count
- decisions
- warnings
- block reasons
- metadata flags

Metadata should include:

- `domestic_candidate_evaluation_fixture_run=true`
- `strategy_track_required=true`
- `domestic_kr_only=true`
- `market_profile_resolved=true`
- `scanner_candidate_consumed=true`
- `technical_evidence_context_checked=true`
- `profitability_context_checked=true`
- `candidate_evaluation_report_generated=true`
- `kiwoom_api_called=false`
- `broker_api_called=false`
- `credentials_accessed=false`
- `external_network_calls=false`
- `orders_created=false`
- `live_or_prod_used=false`
- `cloud_llm_called=false`
- `model_runtime_called=false`

## CandidateEvaluationSafetyBoundary

Recommended fields:

- advisory only
- trade approval allowed, false
- order creation allowed, false
- order intent allowed, false
- order draft allowed, false
- execution approval allowed, false
- live or prod allowed, false
- broker access allowed, false
- network access allowed, false
- model runtime allowed, false

Rules:

- evaluation output is reporting-only
- evaluation output must not bypass any later risk or execution gate

## CandidateEvaluationGapReport

Recommended fields:

- report id
- missing technical evidence count
- missing profitability context count
- stale candidate count
- blocked candidate count
- unsupported track count
- unsafe trigger count
- unresolved market profile count
- gap reasons

This report is for diagnostics only.

## Candidate Evaluation States

Internal v4.4 evaluation states:

- `EVALUATION_READY`
- `WATCH_ONLY`
- `REPORT_ONLY`
- `BLOCKED_SCANNER_QUALITY`
- `BLOCKED_STALE_DATA`
- `BLOCKED_PROFITABILITY`
- `BLOCKED_TECHNICAL_EVIDENCE`
- `BLOCKED_RISK`
- `REJECTED_NON_DOMESTIC`
- `REJECTED_UNSAFE_TRIGGER`
- `INSUFFICIENT_CONTEXT`

State rules:

- `EVALUATION_READY` means ready for offline evaluation and reporting only
- `EVALUATION_READY` does not mean trade-ready
- `WATCH_ONLY` means the candidate may remain under observation
- `REPORT_ONLY` means non-actionable report output only
- blocked and rejected states must never be converted into trade approval
- no state may trigger orders, `OrderIntent`, order drafts, execution approval,
  `LIVE`, or `PROD`

## Dual Compatibility Model

v4.4 uses a mixed compatibility model.

Each evaluation decision should expose:

- `scanner_compatibility_status`
  the carried-forward v4.3 `DISCOVER / WATCH / EXCLUDE`
- `evaluation_compatibility_status`
  a v4.4 report-level `DISCOVER / WATCH / EXCLUDE`

Core rules:

- `scanner_compatibility_status` is traceability only
- `scanner_compatibility_status` must not be reinterpreted as approval
- `evaluation_compatibility_status` is a reporting compatibility field only
- `evaluation_compatibility_status` must not weaken blocked or report-only
  safety states
- if `evaluation_compatibility_status` is `DISCOVER` or `WATCH`, but the
  internal state is `REPORT_ONLY` or any blocked state, the result remains
  non-actionable

Recommended mapping:

- `EVALUATION_READY` -> `DISCOVER` or `WATCH`
- `WATCH_ONLY` -> `WATCH`
- `REPORT_ONLY` -> `WATCH` or `EXCLUDE`
- `BLOCKED_SCANNER_QUALITY` -> `EXCLUDE`
- `BLOCKED_STALE_DATA` -> `EXCLUDE`
- `BLOCKED_PROFITABILITY` -> `EXCLUDE`
- `BLOCKED_TECHNICAL_EVIDENCE` -> `WATCH` or `EXCLUDE`
- `BLOCKED_RISK` -> `EXCLUDE`
- `REJECTED_NON_DOMESTIC` -> `EXCLUDE`
- `REJECTED_UNSAFE_TRIGGER` -> `EXCLUDE`
- `INSUFFICIENT_CONTEXT` -> `WATCH` or `EXCLUDE`

## Technical Evidence Integration

v4.4 may consume or reference:

- MACD evidence
- RSI evidence
- moving-average evidence
- HMA evidence
- ATR or risk evidence
- volume evidence
- divergence evidence
- setup grade
- evidence freshness
- missing evidence policy

Rules:

- v4.4 must not recalculate or fetch real technical data
- technical evidence is fixture-provided context only
- stale technical evidence must not silently pass as fresh
- missing technical evidence must map to `BLOCKED_TECHNICAL_EVIDENCE`,
  `WATCH_ONLY`, or `INSUFFICIENT_CONTEXT` according to explicit policy

## Profitability Integration

v4.4 must respect v4.1 profitability concepts:

- `TrackAwareProfitabilityCheck`
- expected net profit
- expected net return percentage
- break-even move
- report-only profitability context
- non-actionable profitability context
- placeholder or needs-evidence profiles

Rules:

- non-actionable profitability context must block trade-actionable
  interpretation
- negative or insufficient expected net profit must produce blocked or
  report-only states
- report-only profitability context must not approve candidate evaluation
- placeholder or needs-evidence profiles default to `REPORT_ONLY`

## Scanner State Integration

v4.4 must preserve and interpret v4.3 scanner states:

- `SCANNER_READY`
- `REPORT_ONLY_STALE`
- `BLOCKED_QUALITY`
- `WATCHLIST_ADD`
- `WATCHLIST_REMOVE`
- `INSUFFICIENT_DATA`
- `REJECTED_NON_DOMESTIC`
- `REJECTED_UNSAFE_TRIGGER`

Rules:

- `SCANNER_READY` may proceed to offline evaluation only
- `REPORT_ONLY_STALE` may only produce report-only evaluation
- `BLOCKED_QUALITY`, `INSUFFICIENT_DATA`, `REJECTED_NON_DOMESTIC`, and
  `REJECTED_UNSAFE_TRIGGER` must fail closed or remain blocked
- `WATCHLIST_ADD` and `WATCHLIST_REMOVE` are watchlist proposals only, not
  trade signals

Recommended v4.4 interpretation:

- `SCANNER_READY` -> eligible for `EVALUATION_READY` or `WATCH_ONLY`
- `REPORT_ONLY_STALE` -> `REPORT_ONLY` or `BLOCKED_STALE_DATA`
- `BLOCKED_QUALITY` -> `BLOCKED_SCANNER_QUALITY`
- `WATCHLIST_ADD` -> `WATCH_ONLY` or `EVALUATION_READY`
- `WATCHLIST_REMOVE` -> `WATCH_ONLY` or `BLOCKED_RISK`
- `INSUFFICIENT_DATA` -> `INSUFFICIENT_CONTEXT`
- `REJECTED_NON_DOMESTIC` -> `REJECTED_NON_DOMESTIC`
- `REJECTED_UNSAFE_TRIGGER` -> `REJECTED_UNSAFE_TRIGGER`

## Advisory Context Integration

v3.12 prompt packs may later consume evaluation reports.

Rules:

- prompt packs must declare supported tracks
- prompt packs must respect report-only and non-actionable evaluation states
- prompt packs must not turn evaluation reports into actionable trade
  instructions
- no LLM or model runtime execution belongs in v4.4

v4.4 may expose:

- advisory summary markers
- supported tracks
- report-only markers
- non-actionable explanation fields

## Domestic-Only Enforcement

v4.4 must explicitly enforce domestic-only routing.

Required failures:

- missing `StrategyTrack`
- non-`DOMESTIC_KR` track
- missing `MarketProfile`
- unresolved `MarketProfile`
- missing v4.3 scanner candidate input
- missing profitability context
- `OVERSEAS_US`
- provider or scanner data attempting non-domestic extension

Kiwoom rules:

- Kiwoom remains domestic Korean stock only
- Kiwoom may be represented only through existing local fixture metadata
- no direct Kiwoom runtime path is allowed

## CLI Design Proposal

Recommended CLI commands:

- `domestic-candidate-evaluation-config-validate --fixture-file ...`
- `domestic-candidate-evaluate --fixture-file ... [--output-file ...]`
- `domestic-candidate-evaluation-gap-report --fixture-file ... [--output-file ...]`
- `domestic-candidate-evaluation-safety-report --fixture-file ... [--output-file ...]`

Command purposes:

- config validate checks schema, track, market-profile, and safety boundary
- evaluate produces deterministic candidate evaluation reports
- gap report summarizes missing evidence and blocked reasons
- safety report summarizes non-actionable, blocked, stale, and rejected states

## Fixture Design

v4.4 fixture set should include local JSON examples for:

- valid domestic candidate evaluation
- scanner-ready candidate with technical evidence
- watch-only candidate
- report-only stale candidate
- blocked scanner-quality case
- blocked profitability case
- blocked technical evidence case
- missing track failure
- missing market profile failure
- `OVERSEAS_US` rejection
- unsafe order-trigger attempt failure

Fixture requirements:

- explicit local JSON only
- deterministic candidate values
- explicit fixture provenance
- preserved scanner state and compatibility fields
- no hidden runtime dependencies

## System Smoke Design

System smoke must use temporary local JSON fixtures only.

Smoke must confirm:

- `domestic_candidate_evaluation_fixture_run=true`
- `strategy_track_required=true`
- `domestic_kr_only=true`
- `market_profile_resolved=true`
- `scanner_candidate_consumed=true`
- `technical_evidence_context_checked=true`
- `profitability_context_checked=true`
- `candidate_evaluation_report_generated=true`
- `kiwoom_api_called=false`
- `broker_api_called=false`
- `credentials_accessed=false`
- `external_network_calls=false`
- `orders_created=false`
- `live_or_prod_used=false`
- `cloud_llm_called=false`
- `model_runtime_called=false`

The smoke run remains offline and deterministic.

## Hard Restrictions

v4.4 design must preserve all of the following:

- no Kiwoom API calls
- no broker API calls
- no credentials access
- no account access
- no WebSocket connections
- no realtime market-data fetch
- no realtime FX fetch
- no external technical-indicator fetch
- no order submission
- no `OrderIntent`
- no order drafts
- no execution approval
- no `LIVE`
- no `PROD`
- no real provider integration
- no account-read
- no token handling
- no cloud LLMs
- no local model runtimes
- no modification to v4.0, v4.1, v4.2, v4.3, or v3.12 implementation

## Recommended v4.4 Implementation Boundary

When implementation begins later, the allowed boundary should be:

- strict local JSON fixture loader
- candidate evaluation config validation
- deterministic scanner-candidate consumption
- deterministic technical and profitability scoring
- dual compatibility reporting
- gap report generation
- safety report generation
- offline system smoke

Forbidden boundary:

- live data access
- Kiwoom runtime connection
- broker integration
- account integration
- order path creation
- execution path activation
- non-domestic track support
- cloud or local model execution
