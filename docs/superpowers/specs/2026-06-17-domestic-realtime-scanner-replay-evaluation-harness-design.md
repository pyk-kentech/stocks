# v4.5 Domestic Realtime Scanner Replay Evaluation Harness Design

## Scope

v4.5 designs an offline deterministic replay harness that replays domestic
normalized realtime event fixtures through the v4.2, v4.3, and v4.4 pipeline
and produces deterministic replay evaluation reports.

This milestone is design-only.

It does not implement runtime code, does not call Kiwoom APIs, does not call
broker APIs, does not access accounts, credentials, tokens, WebSocket feeds,
realtime feeds, FX feeds, or order paths, and does not create `OrderIntent`,
order drafts, execution approvals, `LIVE`, or `PROD` behavior.

It also does not call cloud LLMs or local model runtimes.

v4.5 remains:

- local fixture-only
- offline
- deterministic
- domestic-track only
- replay/diagnostics only
- non-executing

## Release Baseline

The completed foundations relevant to this design are:

- `v4.0.0-domestic-overseas-strategy-track-separation` -> `d6d430d`
- `v4.1.0-market-profile-fee-tax-fx-net-profit-calculator` -> `3df8289`
- `v3.12.0-offline-prompt-pack-advisory-task-suite` -> `656c7ea`
- `v4.2.0-domestic-kiwoom-realtime-data-track` -> `45b071c`
- `v4.3.0-domestic-realtime-scanner-integration` -> `8d18dee`
- `v4.4.0-domestic-scanner-candidate-evaluation-pipeline` -> `910e423`

v4.5 must preserve:

- v4.0 track-first routing
- v4.1 report-only and non-actionable profitability safety
- v3.12 advisory-only prompt-pack safety
- v4.2 normalized realtime quality and stale-data fail-closed policy
- v4.3 scanner candidate state and compatibility reporting
- v4.4 evaluation state and compatibility reporting

## Architecture Position

v4.5 sits after the v4.2/v4.3/v4.4 domestic pipeline layers.

Required flow:

- `ReplayFixture`
- `StrategyTrack`
- `MarketProfile`
- `NormalizedRealtimeEventSequence`
- `ScannerInputSnapshot`
- `ScannerCandidate`
- `CandidateEvaluationReport`
- `ReplayEvaluationReport`

Interpretation:

- v4.2 remains responsible for normalized domestic realtime event quality,
  staleness, and event normalization rules
- v4.3 remains responsible for scanner candidate generation
- v4.4 remains responsible for candidate evaluation
- v4.5 replays explicit local event sequences through those layers and records
  traces, summaries, and readiness diagnostics

v4.5 is replay and reporting only. It is not trading, not broker routing, not
execution planning, and not order creation.

## Architecture Rules

The following rules are mandatory:

- `StrategyTrack` is a top-level mandatory input
- only `DOMESTIC_KR` is allowed
- `OVERSEAS_US` must fail validation
- missing or unresolved `MarketProfile` must fail closed
- v4.2 normalized event quality and stale-data rules must be preserved
- v4.3 scanner state and discovery compatibility fields must be preserved
- v4.4 evaluation state and compatibility fields must be preserved
- replay results are offline diagnostics only
- replay results must not create orders, `OrderIntent`, order drafts,
  execution approvals, `LIVE`, or `PROD` behavior

## Core Schemas

v4.5 should define these design-level schemas:

- `DomesticReplayConfig`
- `DomesticReplayFixture`
- `ReplayEventSequence`
- `ReplayClockPolicy`
- `ReplayWindow`
- `ReplayStepResult`
- `ReplayCandidateTrace`
- `ReplayEvaluationMetrics`
- `ReplayEvaluationReport`
- `ReplayQualityGate`
- `ReplayPromotionReadinessReport`
- `ReplaySafetyBoundary`

All schemas must remain:

- local
- JSON fixture-driven
- deterministic
- track-aware
- advisory-only

## DomesticReplayConfig

Recommended fields:

- config id
- strategy track
- report-only mode flag
- replay ordering mode
- replay tie-breaker mode
- duplicate event policy
- missing timestamp policy
- stale event policy
- report-only downgrade policy
- replay window size
- replay metrics policy
- promotion readiness policy

Rules:

- config requires `DOMESTIC_KR`
- missing track must fail
- unresolved market profile must fail
- config must not include execution permissions

## DomesticReplayFixture

Recommended fields:

- fixture id
- strategy track
- resolved market profile
- replay config
- normalized domestic realtime event sequence
- symbol universe snapshot
- technical evidence context references
- profitability context references
- advisory context markers
- fixture provenance

Rules:

- fixture must consume explicit local normalized domestic event sequences
- fixture must not imply live feed access
- fixture provenance must remain explicit

## ReplayEventSequence

Recommended fields:

- sequence id
- ordered events
- sequence start timestamp
- sequence end timestamp
- symbol universe snapshot
- source fixture markers

Each event should preserve:

- source event id
- provider timestamp
- received timestamp
- normalized event state
- data quality flags

## ReplayClockPolicy

Recommended fields:

- primary ordering field
- secondary ordering field
- deterministic tie-breaker
- out-of-order handling policy
- impossible timestamp handling policy
- gap handling policy
- replay clock advancement mode

Rules:

- ordering must be deterministic
- replay clock behavior must be reproducible from fixture contents alone
- tie-breakers must not depend on runtime state

## ReplayWindow

Recommended fields:

- window id
- window start
- window end
- included event ids
- aggregated summary metrics
- warnings
- block reasons

Rules:

- window summaries are derived from event-level traces
- window summaries must not replace event-level traces

## Hybrid Replay Model

v4.5 uses a two-layer replay model.

### Event-Level Internal Replay

Replay processes events one by one.

Each event should produce deterministic trace data when applicable:

- replay step id
- source event id
- normalized event state
- scanner input snapshot
- scanner candidate trace
- candidate evaluation trace
- blocked reasons
- report-only reasons
- non-actionable reasons
- data quality flags

### Window-Level Report Summary

Window summaries are second-order outputs derived from event-level traces.

Window summaries must not replace event-level traces.

Window summary metrics should include at least:

- events processed
- valid events
- stale events
- invalid events
- candidates generated
- candidates by scanner state
- candidates by evaluation state
- blocked candidates
- report-only candidates
- watchlist add/remove counts
- unsafe trigger rejections
- profitability-blocked count
- technical-evidence-blocked count
- non-actionable candidate count

Core rules:

- window summaries must be derived from event-level traces
- window summaries must not replace event-level traces
- replay output is offline diagnostics only
- event-level replay and window-level summaries must both remain
  non-actionable
- a window summary may indicate replay quality, coverage, warnings, or
  blocking reasons, but it must not imply trade approval
- no replay result may trigger orders, `OrderIntent`, order drafts, execution
  approval, `LIVE`, or `PROD` behavior

## Replay Input Design

Replay input must include:

- normalized realtime event sequence
- fixture id
- replay window start and end
- event ordering policy
- duplicate event policy
- missing timestamp policy
- stale event policy
- report-only event policy
- symbol universe snapshot
- market profile reference

Rules:

- event sequence input must remain explicit and local
- missing timestamps must fail or downgrade according to declared policy
- replay input must not depend on network or provider runtime state

## Replay Clock And Ordering

v4.5 should design deterministic handling for:

- provider timestamp ordering
- received timestamp ordering
- deterministic tie-breaker policy
- out-of-order event handling
- impossible timestamp handling
- event gap handling
- replay clock advancement

Recommended policy:

- provider timestamp first
- received timestamp second
- fixture-order index as deterministic tie-breaker
- impossible timestamps fail closed or downgrade only under explicit policy
- out-of-order events are recorded, not hidden
- replay clock advances only through deterministic policy transitions

## ReplayStepResult

Recommended fields:

- replay step id
- source event id
- replay clock timestamp
- normalized event state
- scanner input snapshot id
- scanner candidate id if produced
- candidate evaluation decision id if produced
- blocked reasons
- report-only reasons
- non-actionable reasons
- data quality flags
- warnings

Rules:

- step results are the primary replay trace unit
- step results must preserve enough context to reproduce blocked and
  non-actionable transitions

## ReplayCandidateTrace

Each replayed candidate should preserve:

- source event ids
- scanner input snapshot id
- scanner candidate id
- v4.3 `scanner_state`
- v4.3 `scanner_compatibility_status`
- v4.4 `evaluation_state`
- v4.4 `evaluation_compatibility_status`
- blocked reasons
- report-only reasons
- data quality flags
- non-actionable marker

Rules:

- v4.5 must not reinterpret v4.3 or v4.4 states as approval
- trace fields are for diagnostics and replay auditability only

## ReplayEvaluationMetrics

Recommended metrics include:

- total events processed
- valid events
- stale events
- invalid events
- generated scanner candidates
- candidates by scanner state
- candidates by evaluation state
- blocked candidate count
- report-only candidate count
- watchlist add count
- watchlist remove count
- domestic-only rejection count
- unsafe trigger rejection count
- quality failure count
- profitability-blocked count
- technical-evidence-blocked count
- non-actionable candidate count

Rules:

- all metrics must be derived from event-level traces
- metrics must remain deterministic under replay re-run

## ReplayEvaluationReport

Recommended fields:

- report id
- strategy track
- market profile summary
- replay config summary
- event-level step results
- replay candidate traces
- window summaries
- aggregate metrics
- warnings
- block reasons
- metadata flags

Metadata should include:

- `domestic_replay_fixture_run=true`
- `strategy_track_required=true`
- `domestic_kr_only=true`
- `market_profile_resolved=true`
- `normalized_realtime_event_sequence_consumed=true`
- `scanner_candidate_trace_generated=true`
- `candidate_evaluation_trace_generated=true`
- `replay_metrics_report_generated=true`
- `promotion_readiness_report_generated=true`
- `kiwoom_api_called=false`
- `broker_api_called=false`
- `credentials_accessed=false`
- `external_network_calls=false`
- `orders_created=false`
- `live_or_prod_used=false`
- `cloud_llm_called=false`
- `model_runtime_called=false`

## ReplayQualityGate

Recommended fields:

- stale-event gate
- timestamp-validity gate
- duplicate-event gate
- out-of-order gate
- report-only downgrade gate
- scanner quality gate
- evaluation quality gate
- gate outcome

Rules:

- stale data fails closed by default
- duplicate and out-of-order handling must be explicit
- quality gates run before promotion-readiness interpretation

## ReplayPromotionReadinessReport

This is not production approval.

Recommended statuses:

- `REPLAY_PASS`
- `REPLAY_PASS_WITH_WARNINGS`
- `REPLAY_REPORT_ONLY`
- `REPLAY_BLOCKED_QUALITY`
- `REPLAY_BLOCKED_SAFETY`
- `REPLAY_INSUFFICIENT_COVERAGE`

Rules:

- promotion readiness does not enable `LIVE` or `PROD`
- promotion readiness does not enable orders
- promotion readiness does not approve execution
- it only indicates whether offline fixture coverage is sufficient for the next
  development milestone

Recommended interpretation:

- `REPLAY_PASS`
  replay coverage and quality gates are sufficient for the next offline
  milestone
- `REPLAY_PASS_WITH_WARNINGS`
  replay is usable, but diagnostics indicate follow-up work
- `REPLAY_REPORT_ONLY`
  replay completed only in report-only mode
- `REPLAY_BLOCKED_QUALITY`
  replay was blocked by stale or invalid event quality
- `REPLAY_BLOCKED_SAFETY`
  replay exposed unsafe trigger or non-domestic rejection issues
- `REPLAY_INSUFFICIENT_COVERAGE`
  fixture coverage was too weak to support useful offline progression

## ReplaySafetyBoundary

Recommended fields:

- advisory only
- order creation allowed, false
- order intent allowed, false
- order draft allowed, false
- execution approval allowed, false
- live or prod allowed, false
- broker access allowed, false
- network access allowed, false
- model runtime allowed, false

Rules:

- replay output is always non-actionable
- replay output must not bypass later risk or execution gates

## Safety And Fail-Closed Rules

The following rules are mandatory:

- missing `StrategyTrack` fails
- non-`DOMESTIC_KR` track fails
- missing `MarketProfile` fails
- stale data fails closed by default
- report-only downgrade only when explicitly declared
- unsafe trigger attempt fails
- replay output is always non-actionable
- no replay state may trigger orders, `OrderIntent`, order drafts, execution
  approval, `LIVE`, or `PROD`

## Integration With Previous Milestones

v4.5 should reference:

- v4.2 normalized domestic realtime events
- v4.3 scanner candidates
- v4.4 candidate evaluation reports
- v4.1 profitability checks
- v3.12 advisory context as non-runtime context only

Rules:

- v4.5 may reuse schema shapes and report fields from prior milestones
- v4.5 must not weaken any earlier non-actionable boundary
- v4.5 must not introduce direct provider, broker, or model runtime execution

## CLI Design Proposal

Recommended CLI commands:

- `domestic-replay-config-validate --fixture-file ...`
- `domestic-replay-run --fixture-file ... [--output-file ...]`
- `domestic-replay-metrics-report --fixture-file ... [--output-file ...]`
- `domestic-replay-promotion-readiness --fixture-file ... [--output-file ...]`

Command purposes:

- config validate checks schema, track, market-profile, and replay safety
- replay run produces event-level traces and window summaries
- metrics report summarizes aggregate replay metrics
- promotion readiness reports offline development-readiness only

## Fixture Design

v4.5 fixture set should include local JSON examples for:

- valid domestic replay sequence
- ordered normalized event replay
- out-of-order event replay
- stale event fail-closed replay
- explicit report-only stale replay
- volume spike replay
- scanner blocked replay
- profitability blocked replay
- technical evidence blocked replay
- unsafe trigger rejection replay
- missing track failure
- missing market profile failure
- `OVERSEAS_US` rejection

Fixture requirements:

- explicit local JSON only
- deterministic event ordering
- explicit replay policies
- preserved scanner and evaluation trace fields
- no hidden runtime dependencies

## System Smoke Design

System smoke must use temporary local JSON fixtures only.

Smoke must confirm:

- `domestic_replay_fixture_run=true`
- `strategy_track_required=true`
- `domestic_kr_only=true`
- `market_profile_resolved=true`
- `normalized_realtime_event_sequence_consumed=true`
- `scanner_candidate_trace_generated=true`
- `candidate_evaluation_trace_generated=true`
- `replay_metrics_report_generated=true`
- `promotion_readiness_report_generated=true`
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

v4.5 design must preserve all of the following:

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
- no modification to v4.0, v4.1, v4.2, v4.3, v4.4, or v3.12 implementation

## Recommended v4.5 Implementation Boundary

When implementation begins later, the allowed boundary should be:

- strict local JSON replay fixture loader
- deterministic event-by-event replay
- deterministic window summary derivation
- replay metrics report generation
- replay promotion-readiness report generation
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
