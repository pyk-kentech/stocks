# v4.8 Domestic Paper-Shadow Outcome Labeling and Review Design

## Scope

v4.8 designs an offline deterministic outcome-labeling and review layer for
domestic paper-shadow journal entries.

This milestone is design-only.

It does not implement runtime code, does not start paper trading, does not
perform broker simulation, does not access accounts, credentials, tokens,
WebSocket feeds, realtime feeds, FX feeds, or order paths, and does not create
`OrderIntent`, order drafts, execution approvals, `LIVE`, or `PROD` behavior.

It also does not call Kiwoom APIs, broker APIs, cloud LLMs, or local model
runtimes.

v4.8 remains:

- local fixture-only
- offline
- deterministic
- domestic-track only
- review-only
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
- `v3.12.0-offline-prompt-pack-advisory-task-suite` -> `656c7ea`

v4.8 must preserve:

- v4.0 track-first routing and `DOMESTIC_KR` separation
- v4.1 report-only and non-actionable profitability safety
- v4.2 stale-data fail-closed and domestic realtime quality rules
- v4.3 scanner-state non-executable semantics
- v4.4 candidate-evaluation blocked/report-only/non-actionable semantics
- v4.5 replay trace provenance and scenario/window references
- v4.6 promotion-gate evidence as supporting context only
- v4.7 candidate-level paper-shadow journaling
- v3.12 advisory-only prompt-pack safety

## Architecture Position

v4.8 sits after v4.7 paper-shadow journaling.

Required flow:

- `PaperShadowDecisionJournal`
- `ShadowOutcomeFixture`
- `OutcomeLabelPolicy`
- `PaperShadowOutcomeLabel`
- `PaperShadowOutcomeReviewReport`

Interpretation:

- v4.7 remains responsible for generating candidate-level non-executable
  journal entries
- v4.8 consumes those journal entries plus local future-outcome fixtures
- v4.8 evaluates observed future movement only within fixture-defined
  observation windows
- v4.8 does not perform paper trading, broker simulation, position tracking,
  account P/L, or execution replay
- v4.8 produces offline outcome labels and review reports only

## Architecture Rules

The following rules are mandatory:

- `StrategyTrack` is a top-level mandatory input
- only `DOMESTIC_KR` is allowed
- `OVERSEAS_US` must fail validation
- missing or unresolved `MarketProfile` must fail closed
- v4.7 paper-shadow journal entries must be consumed as non-executable inputs
  only
- outcome fixtures must be explicit local JSON fixtures only
- outcome labels are offline review labels only
- outcome labels must not create orders, `OrderIntent`, order drafts,
  execution approval, `LIVE`, or `PROD` behavior

## Fixed Hybrid Outcome Model

v4.8 uses a fixed hybrid outcome model.

### Journal-Entry-Level Primary Outcome Label

The primary `PaperShadowOutcomeLabel` unit must be journal-entry-level.

One outcome label represents one v4.7 `PaperShadowDecision`.

It must preserve direct traceability to:

- source paper-shadow journal id
- source paper-shadow decision id
- source candidate id
- source replay/scenario references
- source evaluation state
- source blocked reasons
- source report-only reasons
- source non-actionable reasons
- source promotion-gate context
- source profitability context
- source technical-evidence context

Rules:

- one paper-shadow decision produces at most one primary outcome label
- a grouped scenario or window must not be labeled as if it were one decision
- candidate-level labels remain the canonical review unit

### Hybrid Labeling Criterion

The outcome policy should consider both threshold-touch behavior and final
observation state.

Deterministic observation inputs should include:

- maximum favorable observation move
- maximum adverse observation move
- final observation move
- threshold touched markers
- adverse threshold touched markers
- neutral-range markers

Rules:

- the label must not be based only on final move
- the label must not be based only on threshold touch
- policy should support combined reasoning such as:
  - favorable threshold reached and final move remains constructive
  - adverse threshold reached before favorable context appears
  - neutral or mixed path without decisive threshold confirmation
- these remain observation outcomes, not realized trade results

### Derived Review Aggregations

Scenario/window summaries belong only in
`PaperShadowOutcomeReviewReport`.

They must be derived from candidate-level outcome labels and may aggregate by:

- scenario family
- replay window
- symbol
- decision type
- outcome label
- blocked reason
- report-only reason
- promotion gate status
- observation horizon

Rules:

- aggregates are reporting-only
- aggregates must not replace candidate-level outcome labels
- aggregates must not imply trade approval

## Core Schemas

v4.8 should define these design-level schemas:

- `ShadowOutcomeConfig`
- `ShadowOutcomeInputSet`
- `ShadowOutcomeFixture`
- `OutcomeObservationWindow`
- `OutcomeLabelPolicy`
- `PaperShadowOutcomeLabel`
- `PaperShadowOutcomeReviewReport`
- `PaperShadowOutcomeSafetyBoundary`
- `PaperShadowOutcomeGapReport`

All schemas must remain:

- local
- JSON fixture-driven
- deterministic
- track-aware
- non-executable

## ShadowOutcomeConfig

Recommended fields:

- config id
- strategy track
- market profile id
- explicit shadow-outcome opt-in flag
- allowed decision types
- report-only preservation mode
- blocked-context preservation mode
- inconclusive labeling mode
- aggregation mode

Rules:

- config requires `DOMESTIC_KR`
- unresolved market profile fails closed
- config must not include execution permissions
- config must not imply broker or account connectivity

## ShadowOutcomeInputSet

Recommended fields:

- input set id
- strategy track
- market profile summary
- source paper-shadow journal id
- source paper-shadow decision ids
- candidate ids
- replay window references
- scenario family markers
- promotion gate summary reference
- profitability context reference
- technical evidence reference
- advisory context markers

Rules:

- missing paper-shadow journal fails closed
- missing paper-shadow decision entry fails closed
- all references must remain explicit and local

## ShadowOutcomeFixture

Recommended fields:

- fixture id
- strategy track
- market profile id
- source paper-shadow journal id
- source paper-shadow decision id
- candidate id
- symbol
- fixture timestamp
- future observation points
- optional benchmark fixture points
- data quality flags

Rules:

- fixture-only input is mandatory
- fixture must not imply realtime or broker connectivity
- non-domestic track fails closed

## OutcomeObservationWindow

Recommended fields:

- observation window id
- start timestamp
- end timestamp
- horizon label
- minimum point count
- expected cadence marker
- stale tolerance marker

Rules:

- missing observation window fails closed
- impossible timestamp ordering fails closed
- insufficient future points should become insufficient-data or inconclusive
  context, not silent success

## OutcomeLabelPolicy

Recommended fields:

- policy id
- favorable threshold definition
- adverse threshold definition
- neutral band definition
- final move interpretation rule
- threshold precedence rule
- blocked-context preservation rule
- report-only handling rule
- insufficient-data rule
- safety rejection rule

Rules:

- policy must be deterministic
- policy must remain non-executable
- policy must preserve non-actionable context from upstream inputs
- policy must not convert observational labeling into trade approval

## PaperShadowOutcomeLabel

Recommended fields:

- outcome label id
- source paper-shadow journal id
- source paper-shadow decision id
- candidate id
- symbol
- strategy track
- market profile id
- decision type
- outcome label
- label rationale
- observation window summary
- maximum favorable observation move
- maximum adverse observation move
- final observation move
- threshold touch markers
- data quality flags
- blocked reasons
- report-only reasons
- non-actionable reasons

Rules:

- candidate-level labels are primary
- labels must not use trade or execution language
- labels are review outcomes only

## PaperShadowOutcomeReviewReport

Recommended fields:

- report id
- strategy track
- market profile id
- source journal id
- covered outcome label ids
- scenario family summaries
- replay window summaries
- symbol summaries
- label distribution summaries
- blocked/report-only/non-actionable summaries
- coverage warnings
- safety boundary summary

Rules:

- the review report is derived from candidate-level outcome labels
- it must not replace candidate-level labels
- it must remain reporting-only and non-executable

## PaperShadowOutcomeSafetyBoundary

Recommended fields:

- strategy track required marker
- domestic-only marker
- market profile resolved marker
- outcome labels non-executable marker
- no order artifact marker
- no execution approval marker
- no network marker
- no model-runtime marker

Rules:

- all safety markers should be explicit in reports
- any violation should fail closed

## PaperShadowOutcomeGapReport

Recommended fields:

- missing journal entries
- missing decision references
- missing observation points
- insufficient horizon coverage
- invalid timestamps
- stale data markers
- unsupported track markers
- unresolved market profile markers

Rules:

- gap reporting is diagnostic only
- gaps must not be silently ignored

## Outcome Input Design

The outcome input layer should include:

- source paper-shadow journal id
- source paper-shadow decision id
- candidate id
- symbol
- fixture timestamp
- observation window start/end
- future price/volume fixture points
- optional benchmark fixture points
- market profile id
- strategy track
- data quality flags

Rules:

- inputs are fixture-only
- missing journal entry fails closed
- missing outcome fixture fails closed
- missing observation window fails closed
- impossible timestamp ordering fails closed
- non-domestic track fails closed

## Outcome Labels

v4.8 should define non-executable outcome labels such as:

- `OUTCOME_FAVORABLE`
- `OUTCOME_ADVERSE`
- `OUTCOME_NEUTRAL`
- `OUTCOME_INCONCLUSIVE`
- `OUTCOME_BLOCKED_CONFIRMED`
- `OUTCOME_REPORT_ONLY`
- `OUTCOME_INSUFFICIENT_DATA`
- `OUTCOME_REJECTED_SAFETY`

Important rules:

- do not use labels such as `PROFIT_TRADE`, `LOSS_TRADE`, `BUY_SUCCESS`,
  `SELL_SUCCESS`, `ENTRY_SUCCESS`, or `EXECUTION_RESULT`
- labels describe observation outcomes, not trades
- labels must preserve non-actionable semantics

Recommended interpretations:

- `OUTCOME_FAVORABLE`: observation path met favorable policy criteria
  without becoming an execution result
- `OUTCOME_ADVERSE`: observation path met adverse policy criteria
- `OUTCOME_NEUTRAL`: observation path remained within neutral criteria
- `OUTCOME_INCONCLUSIVE`: observation path existed but policy could not
  determine a decisive favorable/adverse/neutral label
- `OUTCOME_BLOCKED_CONFIRMED`: upstream blocked decision remained consistent
  with observed context or should stay blocked in review
- `OUTCOME_REPORT_ONLY`: source decision or policy keeps the result
  explicitly non-actionable and review-only
- `OUTCOME_INSUFFICIENT_DATA`: fixture coverage is missing or inadequate
- `OUTCOME_REJECTED_SAFETY`: safety boundary, unsafe trigger, or invalid
  context prevents labeling

## Observation Metrics

v4.8 should design deterministic fixture-only metrics such as:

- maximum favorable observation move
- maximum adverse observation move
- final observation move
- observation volatility proxy
- observation volume confirmation
- threshold touched marker
- adverse threshold touched marker
- neutral range marker
- missing data marker
- stale data marker

Rules:

- these are not realized P/L
- these are not account returns
- these are not execution returns
- they are observation metrics only

## Decision-to-Outcome Mapping

v4.8 should define how v4.7 decisions map to outcome labels.

Base rules:

- `SHADOW_WATCH` may be labeled favorable, adverse, neutral, or inconclusive
- `SHADOW_REPORT_ONLY` should usually map to `OUTCOME_REPORT_ONLY` unless an
  explicit review policy allows observation-only labeling while preserving
  non-actionable status
- `SHADOW_BLOCKED_*` decisions should preserve blocked context
- `SHADOW_BLOCKED_SAFETY` should map to safety or rejected outcome context
- `SHADOW_INSUFFICIENT_CONTEXT` should map to insufficient-data or
  inconclusive context
- non-actionable decisions remain non-actionable

Recommended mapping guidance:

- `SHADOW_WATCH` + favorable threshold touch + constructive final state ->
  `OUTCOME_FAVORABLE`
- `SHADOW_WATCH` + adverse threshold touch dominating policy ->
  `OUTCOME_ADVERSE`
- `SHADOW_WATCH` + neutral-band persistence ->
  `OUTCOME_NEUTRAL`
- `SHADOW_WATCH` + conflicting or incomplete evidence ->
  `OUTCOME_INCONCLUSIVE`
- `SHADOW_REPORT_ONLY` -> `OUTCOME_REPORT_ONLY`
- `SHADOW_BLOCKED_QUALITY` / `SHADOW_BLOCKED_PROFITABILITY` /
  `SHADOW_BLOCKED_TECHNICAL_EVIDENCE` / `SHADOW_BLOCKED_RISK` ->
  `OUTCOME_BLOCKED_CONFIRMED` unless policy explicitly marks insufficient
  evidence
- `SHADOW_BLOCKED_SAFETY` -> `OUTCOME_REJECTED_SAFETY`
- `SHADOW_INSUFFICIENT_CONTEXT` -> `OUTCOME_INSUFFICIENT_DATA` or
  `OUTCOME_INCONCLUSIVE`

## Review Report Design

The review report should define metrics such as:

- total outcome labels
- favorable count
- adverse count
- neutral count
- inconclusive count
- report-only count
- insufficient-data count
- safety-rejected count
- blocked-confirmed count
- favorable rate among shadow-watch entries
- adverse rate among shadow-watch entries
- inconclusive rate
- average maximum favorable observation move
- average maximum adverse observation move
- scenario family coverage count
- symbol coverage count
- observation window coverage count

Rules:

- metrics are review diagnostics only
- metrics must not be interpreted as realized trade performance
- metrics must preserve non-actionable semantics

## Scenario and Window Aggregation

Outcome review reports may aggregate labels by:

- scenario family
- replay window
- symbol
- decision type
- outcome label
- blocked reason
- report-only reason
- promotion gate status
- observation horizon

Rules:

- aggregates must be derived from candidate-level outcome labels
- aggregates must not replace candidate-level outcome labels
- aggregates are reporting-only

## Integration With Previous Milestones

v4.8 should reference:

- v4.7 paper-shadow journal entries as the primary source unit
- v4.6 promotion gate evidence as supporting calibration context only
- v4.5 replay windows and scenario families for grouping and traceability
- v4.4 candidate evaluation states and compatibility status
- v4.3 scanner states as historical scanner context only
- v4.2 normalized domestic realtime event quality flags as provenance context
- v4.1 profitability context as non-actionable explanatory context
- v3.12 advisory context as non-runtime context only

Rules:

- none of these integrations may enable execution
- upstream blocked/report-only/non-actionable semantics must be preserved

## Advisory Context Integration

v3.12 prompt packs may later consume outcome review reports only as
non-executable advisory context.

Required rules:

- prompt packs must declare supported tracks
- prompt packs must treat outcome labels as non-executable review context
- prompt packs must not convert outcome labels into trade instructions
- prompt packs must not approve trades from blocked, report-only,
  insufficient-data, or safety-rejected outcomes
- no LLM or model runtime execution occurs in this milestone

## Safety and Fail-Closed Rules

The design must enforce:

- missing `StrategyTrack` fails
- non-`DOMESTIC_KR` track fails
- missing `MarketProfile` fails
- missing paper-shadow journal fails
- missing paper-shadow decision entry fails
- missing outcome fixture fails
- missing observation window fails
- impossible timestamp ordering fails
- unsafe trigger attempt fails
- outcome labels are always non-executable
- no outcome state may trigger orders, `OrderIntent`, order drafts,
  execution approval, `LIVE`, or `PROD`

Additional safety rules:

- stale or invalid fixture data must not be silently accepted as favorable
- unresolved profitability context must remain non-actionable
- review outputs must not be mislabeled as paper-trade results

## CLI Design Proposal

CLI commands should remain consistent with existing repo style:

- `domestic-shadow-outcome-config-validate --fixture-file ...`
- `domestic-shadow-outcome-label --fixture-file ... [--output-file ...]`
- `domestic-shadow-outcome-review-report --fixture-file ... [--output-file ...]`
- `domestic-shadow-outcome-safety-report --fixture-file ... [--output-file ...]`

Command roles:

- config validation checks track, market profile, and policy readiness
- label generation creates candidate-level outcome labels only
- review report generation aggregates existing candidate-level labels
- safety report surfaces fail-closed violations and gap conditions

## Fixture Design

v4.8 should design local JSON fixture examples for:

- valid outcome config
- valid shadow-watch favorable outcome
- valid shadow-watch adverse outcome
- neutral outcome
- inconclusive outcome
- report-only outcome
- blocked-confirmed outcome
- insufficient-data outcome
- missing track failure
- missing market profile failure
- missing paper-shadow journal failure
- missing paper-shadow decision failure
- missing outcome fixture failure
- impossible timestamp ordering failure
- `OVERSEAS_US` rejection
- unsafe trigger attempt failure

## System Smoke Design

System smoke must use temporary local JSON fixtures only.

Smoke output must confirm:

- `domestic_shadow_outcome_fixture_run=true`
- `strategy_track_required=true`
- `domestic_kr_only=true`
- `market_profile_resolved=true`
- `paper_shadow_journal_consumed=true`
- `outcome_fixture_consumed=true`
- `outcome_labels_generated=true`
- `outcome_review_report_generated=true`
- `outcome_labels_non_executable=true`
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

## Implementation Boundary for Later

If implemented later, v4.8 may add:

- strict local fixture loaders
- deterministic label policy evaluation
- candidate-level outcome label generation
- review-report aggregation
- safety and gap reporting

v4.8 must still not add:

- paper trading execution
- broker simulation
- order artifacts
- Kiwoom or broker connectivity
- realtime or FX network access
- cloud or local model inference

