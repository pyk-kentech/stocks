# v4.7 Domestic Paper-Shadow Decision Journal Design

## Scope

v4.7 designs an offline deterministic paper-shadow decision journal that
records hypothetical non-executable decisions derived from domestic replay,
calibration, promotion-gate, and candidate-evaluation outputs.

This milestone is design-only.

It does not implement runtime code, does not start paper trading, does not call
Kiwoom APIs, broker APIs, or external providers, does not access accounts,
credentials, tokens, WebSocket feeds, realtime feeds, FX feeds, or order
paths, and does not create `OrderIntent`, order drafts, execution approvals,
`LIVE`, or `PROD` behavior.

It also does not call cloud LLMs or local model runtimes.

v4.7 remains:

- local fixture-only
- offline
- deterministic
- domestic-track only
- journaling/review only
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
- `v4.6.0-domestic-replay-policy-calibration-promotion-gate` -> `f46e878`

v4.7 must preserve:

- v4.0 track-first routing and `DOMESTIC_KR` separation
- v4.1 report-only and non-actionable profitability safety
- v3.12 advisory-only prompt-pack safety
- v4.2 stale-data fail-closed and normalized event quality rules
- v4.3 scanner candidate safety and non-executable scanner semantics
- v4.4 candidate evaluation states and blocked/report-only semantics
- v4.5 replay trace provenance and non-actionable replay reporting
- v4.6 calibration-pack-only promotion gate semantics

## Architecture Position

v4.7 sits after v4.6 promotion-gate reporting.

Required flow:

- `PromotionGateReport`
- `PaperShadowConfig`
- `CandidateEvaluationReport`
- `PaperShadowDecision`
- `PaperShadowDecisionJournal`
- `PaperShadowReviewReport`

Interpretation:

- v4.6 remains responsible for replay-driven calibration and pack-level
  promotion-gate evidence
- v4.7 consumes promotion-gate evidence plus candidate-evaluation outputs
- v4.7 journals hypothetical decisions only
- v4.7 is not paper-trading execution, not broker simulation, not account
  simulation, and not order planning

## Architecture Rules

The following rules are mandatory:

- `StrategyTrack` is a top-level mandatory input
- only `DOMESTIC_KR` is allowed
- `OVERSEAS_US` must fail validation
- missing or unresolved `MarketProfile` must fail closed
- v4.6 promotion gate must be consumed as evidence, but it must not
  automatically enable paper-shadow
- paper-shadow mode must require an explicit local fixture opt-in
- paper-shadow decisions are non-executable journal entries only
- paper-shadow decisions must not create orders, `OrderIntent`, order drafts,
  execution approval, `LIVE`, or `PROD` behavior
- journal and review outputs are offline diagnostics only

## Fixed Hybrid Journal-Entry Model

v4.7 uses a fixed hybrid journal model with candidate-level source entries and
derived reporting summaries.

### Candidate-Level Primary Journal Entry

The primary `PaperShadowDecision` journal entry unit must be candidate-level.

Each journal entry represents one non-executable decision for one evaluated
candidate.

It must preserve direct traceability to:

- source scanner candidate
- source candidate evaluation report
- v4.4 `evaluation_state`
- v4.4 `evaluation_compatibility_status`
- v4.6 promotion gate evidence
- blocked reasons
- report-only reasons
- non-actionable reasons
- technical evidence context
- profitability context
- risk/safety context

Rules:

- one `PaperShadowDecision` equals one evaluated candidate
- it must preserve source ids and reason fields
- it must never represent a grouped scenario/window as if it were an actionable
  decision

### Scenario/Window-Level Derived Summaries

Scenario/window-level summaries belong only in `PaperShadowReviewReport`.

They must be derived from candidate-level journal entries and may aggregate by:

- replay window
- scenario family
- symbol
- decision type
- blocked reason
- report-only reason
- non-actionable reason
- promotion gate status

Rules:

- summaries are reporting-only
- summaries must not replace candidate-level entries
- summaries must not imply trade approval

### Safety Interpretation

- no candidate-level journal entry may use executable intent labels such as
  `BUY`, `SELL`, `ORDER`, `EXECUTE`, or `ENTRY_APPROVED`
- no scenario/window summary may imply trade approval
- journal entries and review summaries remain offline diagnostics only
- no paper-shadow state may trigger orders, `OrderIntent`, order drafts,
  execution approval, `LIVE`, or `PROD`

## Core Schemas

v4.7 should define these design-level schemas:

- `PaperShadowConfig`
- `PaperShadowInputSet`
- `PaperShadowDecision`
- `PaperShadowDecisionType`
- `PaperShadowDecisionReason`
- `PaperShadowDecisionJournal`
- `PaperShadowReviewReport`
- `PaperShadowSafetyBoundary`
- `PaperShadowGapReport`

All schemas must remain:

- local
- JSON fixture-driven
- deterministic
- track-aware
- non-executable

## PaperShadowConfig

Recommended fields:

- config id
- strategy track
- explicit paper-shadow opt-in flag
- allowed promotion gate statuses
- blocked promotion gate statuses
- journal generation mode
- review aggregation mode
- report-only preservation mode
- non-actionable preservation mode

Rules:

- config requires `DOMESTIC_KR`
- paper-shadow opt-in must be explicit
- config must not include execution permissions
- config must not imply account or broker connectivity

## PaperShadowInputSet

Recommended fields:

- input set id
- strategy track
- market profile summary
- promotion gate report reference
- promotion gate criteria reference
- calibration pack reference
- coverage report reference
- regression report reference
- candidate evaluation report references
- replay provenance markers
- scenario family markers
- advisory context markers

Rules:

- missing promotion gate report fails closed
- missing candidate evaluation report fails closed
- single replay report evidence must not be accepted as sufficient
- all references must remain explicit and local

## PaperShadowDecisionType

v4.7 should define non-executable decision types such as:

- `SHADOW_WATCH`
- `SHADOW_REJECT`
- `SHADOW_REPORT_ONLY`
- `SHADOW_BLOCKED_QUALITY`
- `SHADOW_BLOCKED_PROFITABILITY`
- `SHADOW_BLOCKED_TECHNICAL_EVIDENCE`
- `SHADOW_BLOCKED_RISK`
- `SHADOW_BLOCKED_SAFETY`
- `SHADOW_INSUFFICIENT_CONTEXT`

Rules:

- do not use names like `BUY`, `SELL`, `ORDER`, `EXECUTE`, or
  `ENTRY_APPROVED`
- the journal must not contain executable intent language

## PaperShadowDecisionReason

Recommended fields:

- reason code
- reason category
- source layer
- explanatory summary

Reason categories may include:

- promotion gate
- candidate evaluation
- scanner quality
- technical evidence
- profitability
- risk
- safety
- report-only
- missing context

## PaperShadowDecision

Recommended fields:

- journal entry id
- fixture id
- strategy track
- market profile id
- candidate id
- source scanner candidate id
- source evaluation report id
- source promotion gate id
- non-executable decision type
- decision reasons
- blocked reasons
- report-only reasons
- non-actionable reasons
- non-actionable marker
- data quality flags
- timestamp from fixture or replay context
- technical evidence context summary
- profitability context summary
- risk/safety context summary

Rules:

- one decision entry per evaluated candidate
- no order id
- no account id
- no credential-bearing broker id
- no execution id
- no grouped scenario/window entry may be emitted as a decision

## PaperShadowDecisionJournal

Recommended fields:

- journal id
- strategy track
- market profile summary
- promotion gate status
- source candidate evaluation report ids
- source replay/calibration provenance markers
- journal entries
- warnings
- block reasons
- safety boundary

Rules:

- journal is candidate-entry-first
- journal must preserve source ids and provenance references
- journal must remain non-executable even when entries are positive within
  paper-shadow semantics

## PaperShadowReviewReport

Recommended fields:

- review report id
- journal reference
- total journal entries
- shadow watch count
- rejected count
- report-only count
- blocked quality count
- blocked profitability count
- blocked technical evidence count
- blocked risk count
- blocked safety count
- insufficient context count
- non-actionable count
- candidate coverage count
- scenario family coverage count
- aggregations by replay window
- aggregations by scenario family
- aggregations by symbol
- aggregations by decision type
- aggregations by blocked reason
- aggregations by report-only reason
- aggregations by non-actionable reason
- aggregations by promotion gate status

Rules:

- review summaries must be derived from candidate-level journal entries
- review summaries must not replace journal entries
- review summaries must remain non-executable

## PaperShadowSafetyBoundary

Recommended fields:

- advisory only
- non-executable only
- order creation allowed false
- order intent allowed false
- order draft allowed false
- execution approval allowed false
- account access allowed false
- broker access allowed false
- live or prod allowed false
- cloud llm allowed false
- model runtime allowed false

## PaperShadowGapReport

Recommended fields:

- gap report id
- missing promotion gate evidence count
- missing candidate evaluation count
- blocked promotion gate count
- single-run-only evidence count
- missing market profile count
- missing strategy track count
- unsafe trigger attempt count
- gap reasons

## Promotion Gate Dependency

v4.7 should consume the following v4.6 artifacts:

- `PromotionGateReport`
- `PromotionGateCriteria`
- calibration pack reference
- coverage report reference
- regression report reference
- promotion gate status

Rules:

- `PROMOTION_READY_FOR_PAPER_SHADOW` only allows the paper-shadow journal
  design or runtime to be considered
- it does not automatically enable paper-shadow journaling
- missing promotion gate report fails closed
- `PROMOTION_BLOCKED_*`, `PROMOTION_REJECTED`, or insufficient coverage must
  block paper-shadow journaling
- a single replay report must never enable paper-shadow journaling

## Candidate Evaluation Dependency

v4.7 should consume the following v4.4 artifacts:

- `CandidateEvaluationReport`
- `evaluation_state`
- `evaluation_compatibility_status`
- scanner state references
- technical evidence context
- profitability context
- risk/safety context

Rules:

- `EVALUATION_READY` may become `SHADOW_WATCH` only, not trade-ready
- `WATCH_ONLY` may become `SHADOW_WATCH`
- `REPORT_ONLY` must become `SHADOW_REPORT_ONLY`
- any `BLOCKED_*`, `REJECTED_*`, or `INSUFFICIENT_CONTEXT` state must remain
  blocked or rejected in the journal
- non-actionable profitability context must prevent any positive decision label

## Journal Content Design

Each journal entry should preserve:

- journal entry id
- fixture id
- strategy track
- market profile id
- candidate id
- source scanner candidate id
- source evaluation report id
- source promotion gate id
- non-executable decision type
- reasons
- blocked reasons
- report-only reasons
- non-actionable marker
- non-actionable reasons
- data quality flags
- timestamp from fixture or replay context
- no order id
- no account id
- no broker id requiring credentials
- no execution id

## Review Report Design

Review report metrics should include:

- total journal entries
- shadow watch count
- rejected count
- report-only count
- blocked quality count
- blocked profitability count
- blocked technical evidence count
- blocked risk count
- blocked safety count
- insufficient context count
- non-actionable count
- candidate coverage count
- scenario family coverage count

These metrics must remain review-only and non-executable.

## Advisory Context Integration

v3.12 prompt packs may later consume paper-shadow review reports under these
rules:

- prompt packs must declare supported tracks
- prompt packs must treat paper-shadow entries as non-executable context
- prompt packs must not convert journal entries into trade instructions
- no LLM or model runtime execution is allowed in this milestone

## Safety and Fail-Closed Rules

The following fail-closed rules are mandatory:

- missing `StrategyTrack` fails
- non-`DOMESTIC_KR` track fails
- missing `MarketProfile` fails
- missing promotion gate report fails
- blocked promotion gate fails
- single-run-only evidence fails
- missing candidate evaluation report fails
- non-actionable evaluation remains non-actionable
- unsafe trigger attempt fails
- journal output is always non-executable
- no paper-shadow state may trigger orders, `OrderIntent`, order drafts,
  execution approval, `LIVE`, or `PROD`

## CLI Design Proposal

Commands should remain consistent with the existing repo style:

- `domestic-paper-shadow-config-validate --fixture-file ...`
- `domestic-paper-shadow-journal-build --fixture-file ... [--output-file ...]`
- `domestic-paper-shadow-review-report --fixture-file ... [--output-file ...]`
- `domestic-paper-shadow-safety-report --fixture-file ... [--output-file ...]`

Expected behavior:

- validation returns fixture readiness only
- journal build returns candidate-level journal entries only
- review report returns only derived reporting summaries
- safety report returns non-executable boundary confirmation and fail-closed
  findings

## Fixture Design

v4.7 should define local JSON fixture examples for:

- valid paper-shadow config
- valid promotion-ready-for-paper-shadow input
- blocked promotion gate input
- single-run-only evidence failure
- valid shadow watch journal
- report-only journal
- blocked profitability journal
- blocked technical evidence journal
- blocked safety journal
- missing track failure
- missing market profile failure
- missing promotion gate failure
- missing candidate evaluation failure
- `OVERSEAS_US` rejection
- unsafe order-trigger attempt failure

Fixture expectations:

- each fixture must preserve explicit replay/calibration/evaluation provenance
- each fixture must stay domestic-only
- positive paper-shadow fixtures must still remain non-executable

## System Smoke Design

System smoke must use temporary local JSON fixtures only.

Smoke output must confirm:

- `domestic_paper_shadow_fixture_run=true`
- `strategy_track_required=true`
- `domestic_kr_only=true`
- `market_profile_resolved=true`
- `promotion_gate_report_consumed=true`
- `candidate_evaluation_report_consumed=true`
- `paper_shadow_journal_generated=true`
- `paper_shadow_review_report_generated=true`
- `paper_shadow_non_executable=true`
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

Allowed in a future v4.7 implementation:

- local JSON paper-shadow fixture loader
- candidate-level journal builder
- derived review report generator
- safety report generator
- offline deterministic system smoke

Forbidden in v4.7:

- paper trading execution
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
