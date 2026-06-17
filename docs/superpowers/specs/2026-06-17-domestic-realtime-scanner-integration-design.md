# v4.3 Domestic Realtime Scanner Integration Design

## Scope

v4.3 designs an offline deterministic bridge from v4.2 normalized domestic
realtime events into scanner inputs, candidate reports, and watchlist change
proposals.

This milestone is design-only.

It does not implement runtime code, does not call Kiwoom APIs, does not call
broker APIs, does not access credentials, accounts, tokens, WebSocket feeds,
realtime feeds, FX feeds, or order paths, and does not create `OrderIntent`,
order drafts, execution approvals, `LIVE`, or `PROD` behavior.

v4.3 remains:

- local fixture-only
- offline
- deterministic
- domestic-track only
- scanner/report/watchlist oriented
- non-executing

## Release Baseline

The completed foundations relevant to this design are:

- `v4.0.0-domestic-overseas-strategy-track-separation` -> `d6d430d`
- `v4.1.0-market-profile-fee-tax-fx-net-profit-calculator` -> `3df8289`
- `v3.12.0-offline-prompt-pack-advisory-task-suite` -> `656c7ea`
- `v4.2.0-domestic-kiwoom-realtime-data-track` -> `45b071c`

v4.3 must preserve:

- v4.0 track-first architecture
- v4.1 report-only and non-actionable profitability safety
- v3.12 advisory-only prompt-pack safety
- v4.2 domestic-only realtime normalization and stale-data fail-closed policy

## Architecture Position

The v4.3 component sits after v4.2 normalized domestic realtime events.

Required architecture flow:

- `StrategyTrack`
- `MarketProfile`
- `RealtimeProviderProfile`
- `NormalizedRealtimeEvent`
- `ScannerInputSnapshot`
- `ScannerCandidate`
- `WatchlistUpdatePlan`
- `ScannerDecisionReport`

Required rules:

- `StrategyTrack` is a top-level mandatory input
- only `DOMESTIC_KR` is allowed
- `OVERSEAS_US` must fail validation
- unresolved `MarketProfile` must fail closed
- v4.2 normalized event quality flags must be preserved
- default stale-data policy is `FAIL_CLOSED`
- explicit `REPORT_ONLY` mode may allow non-actionable candidates and reports
  only
- `WatchlistUpdatePlan` is only a watchlist state-change proposal
- `WatchlistUpdatePlan` is not a buy or sell signal, trade approval,
  `OrderIntent`, order draft, or execution trigger

## Scanner Architecture

The scanner layer converts validated domestic realtime event snapshots into
deterministic scanner-ready reports.

The offline flow is:

- validate `StrategyTrack`
- resolve `MarketProfile`
- validate domestic `RealtimeProviderProfile`
- consume normalized realtime event fixtures produced by v4.2
- convert eligible events into `ScannerInputSnapshot`
- derive deterministic scanner signals
- evaluate candidate and watchlist state transitions
- produce `ScannerDecisionReport`

The scanner does not trade. It only prepares:

- scanner candidates
- watchlist add and remove proposals
- compatibility outputs for v3.3-style discovery semantics
- quality and safety diagnostics

## Hybrid State Model

v4.3 must use a hybrid state model.

Internal v4.3 scanner candidate states:

- `SCANNER_READY`
- `REPORT_ONLY_STALE`
- `BLOCKED_QUALITY`
- `WATCHLIST_ADD`
- `WATCHLIST_REMOVE`
- `INSUFFICIENT_DATA`
- `REJECTED_NON_DOMESTIC`
- `REJECTED_UNSAFE_TRIGGER`

v3.3-compatible report-level discovery status:

- `DISCOVER`
- `WATCH`
- `EXCLUDE`

Core rules:

- `SCANNER_READY` means scanner/report/watchlist-ready only
- `SCANNER_READY` does not mean trade-ready
- `REPORT_ONLY_STALE`, `BLOCKED_QUALITY`, `INSUFFICIENT_DATA`,
  `REJECTED_NON_DOMESTIC`, and `REJECTED_UNSAFE_TRIGGER` must never be treated
  as actionable approval
- even if the v3.3-compatible field is `DISCOVER` or `WATCH`, the candidate
  remains non-actionable if quality, staleness, profitability, or safety gates
  block it
- no state may trigger orders, `OrderIntent`, order drafts, execution approval,
  `LIVE`, or `PROD` behavior

Mapping principles:

- internal v4.3 states are used for realtime safety, stale handling, quality
  diagnostics, and watchlist-change explanation
- `DISCOVER / WATCH / EXCLUDE` is a compatibility field for existing v3.3
  discovery semantics
- compatibility mapping must never weaken v4.3 safety constraints

Recommended compatibility mapping:

- `SCANNER_READY` -> `DISCOVER` or `WATCH` depending on scanner confidence and
  watchlist policy
- `WATCHLIST_ADD` -> `WATCH`
- `WATCHLIST_REMOVE` -> `EXCLUDE`
- `REPORT_ONLY_STALE` -> `WATCH` or `EXCLUDE`, but always non-actionable
- `BLOCKED_QUALITY` -> `EXCLUDE`
- `INSUFFICIENT_DATA` -> `WATCH` or `EXCLUDE`, but always non-actionable
- `REJECTED_NON_DOMESTIC` -> `EXCLUDE`
- `REJECTED_UNSAFE_TRIGGER` -> `EXCLUDE`

## Core Schemas

v4.3 should define these design-level schemas:

- `RealtimeScannerConfig`
- `ScannerInputSnapshot`
- `ScannerCandidate`
- `VolumeSpikeSignal`
- `PriceMomentumSignal`
- `LiquiditySignal`
- `WatchlistUpdatePlan`
- `ScannerDecisionReport`
- `ScannerDataQualityGate`
- `ScannerSafetyBoundary`

All schemas must remain:

- local
- JSON fixture-driven
- deterministic
- track-aware
- advisory-only

## RealtimeScannerConfig

Recommended fields:

- config id
- strategy track
- market profile reference or embedded resolved market profile
- provider profile reference or embedded provider profile
- stale policy mode
- report-only mode flag
- scanner thresholds for volume spike
- scanner thresholds for price momentum
- scanner thresholds for liquidity
- watchlist add thresholds
- watchlist remove thresholds
- blocked quality policies
- candidate mapping policy
- compatibility mapping policy

Rules:

- config requires `DOMESTIC_KR`
- missing track must fail
- unresolved market profile must fail
- non-domestic provider profile must fail

## ScannerInputSnapshot

Recommended fields:

- snapshot id
- strategy track
- resolved market profile
- provider profile id
- symbol
- event type mix
- last trade context
- quote context
- orderbook context
- derived volume spike context
- freshness status
- report-only flag
- preserved quality flags
- fixture source markers

Rules:

- snapshots must preserve v4.2 quality flags
- stale or invalid source events must remain visible in snapshot diagnostics
- fixture-only origin must be explicit

## ScannerCandidate

Recommended fields:

- candidate id
- snapshot id
- symbol
- internal scanner state
- compatibility discovery status
- candidate reason codes
- block reasons
- warnings
- volume spike signal
- price momentum signal
- liquidity signal
- watchlist intent
- profitability context summary
- advisory context allowed flag
- actionable approval flag, always false in v4.3

Rules:

- v4.3 candidates are scanner candidates only
- candidates must not express trade approval
- compatibility discovery status must not override internal safety state

## VolumeSpikeSignal

Recommended fields:

- symbol
- observed volume
- baseline volume
- spike ratio
- spike threshold
- signal pass boolean
- freshness status
- quality flags

This signal may later align with v3.3 volume-spike discovery, but in v4.3 it
remains scanner-only.

## PriceMomentumSignal

Recommended fields:

- symbol
- recent price
- reference price
- price change percent
- momentum threshold
- direction
- signal pass boolean
- quality flags

This is a scanner heuristic only. It must not be treated as trade approval.

## LiquiditySignal

Recommended fields:

- symbol
- best bid
- best ask
- spread
- bid depth
- ask depth
- liquidity threshold pass
- quality flags

Liquidity is used only for scanner/watchlist evaluation and later advisory
context, not for execution.

## WatchlistUpdatePlan

Recommended fields:

- plan id
- strategy track
- additions
- removals
- retained symbols
- blocked symbols
- report-only symbols
- plan reason codes
- source candidate ids

Rules:

- this plan is only a watchlist state-change proposal
- it must not become a buy or sell signal
- it must not create order objects

## ScannerDecisionReport

Recommended fields:

- report id
- strategy track
- market profile summary
- provider profile summary
- candidate count
- ready count
- watchlist add count
- watchlist remove count
- blocked count
- report-only count
- compatibility decision counts
- warnings
- block reasons
- candidates
- watchlist update plan
- metadata flags

Metadata should include:

- `domestic_scanner_fixture_run=true`
- `strategy_track_required=true`
- `domestic_kr_only=true`
- `market_profile_resolved=true`
- `normalized_realtime_event_consumed=true`
- `scanner_candidate_report_generated=true`
- `kiwoom_api_called=false`
- `broker_api_called=false`
- `credentials_accessed=false`
- `external_network_calls=false`
- `orders_created=false`
- `live_or_prod_used=false`

## ScannerDataQualityGate

Recommended fields:

- freshness gate
- timestamp gate
- completeness gate
- unsafe trigger gate
- report-only downgrade gate
- preserved quality flags
- decision outcome

Rules:

- stale data fails closed by default
- incomplete data must not become actionable
- invalid timestamps must block or downgrade according to explicit policy
- data quality gates must run before candidate state mapping

## ScannerSafetyBoundary

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
- profitability approval allowed, false without actionable context

Rules:

- scanner output is advisory/report/watchlist only
- scanner output must not bypass any later risk or execution gate

## Domestic-Only Enforcement

v4.3 must explicitly enforce domestic-only routing.

Required failures:

- missing `StrategyTrack`
- non-`DOMESTIC_KR` track
- missing `MarketProfile`
- unresolved `MarketProfile`
- missing v4.2 normalized event profile
- missing provider profile
- `OVERSEAS_US`
- provider attempting non-domestic capability claims

Kiwoom rules:

- Kiwoom remains domestic Korean stock only
- Kiwoom may not be extended to overseas tracks in v4.3
- v4.3 may refer to Kiwoom only through local profile and fixture metadata

## Event-to-Scanner Conversion

Normalized v4.2 events become scanner inputs through deterministic conversion.

Trade events may supply:

- price movement context
- recent volume context
- cumulative volume context
- basic momentum deltas

Quote events may supply:

- bid and ask spread context
- quote stability context
- near-term liquidity hints

Orderbook events may supply:

- top-of-book depth
- orderbook imbalance context
- thinning liquidity warnings

Volume spike events may supply:

- derived volume acceleration context
- direct reuse of v4.2 spike ratio fields

Stale or invalid events:

- must preserve quality flags
- must fail closed by default
- may be downgraded only through explicit `REPORT_ONLY` mode

Report-only events:

- may support quality reporting, diagnostics, replay explanation, or watch-only
  reporting
- must not create scanner-ready actionable interpretation

Fixture-only source markers:

- every converted snapshot must keep fixture provenance
- no snapshot may imply live feed consumption

## Scanner Candidate Rules

Candidate generation must be deterministic and local.

Volume spike candidates:

- require valid volume context
- require configured spike threshold pass
- fail or downgrade if stale or incomplete

Price momentum candidates:

- require valid price references
- require deterministic threshold pass
- remain scanner-only even when strong

Liquidity candidates:

- require quote or orderbook depth context
- block when liquidity fields are missing beyond policy tolerance

Watchlist add candidates:

- are generated when scanner signals pass configured watchlist-add thresholds
- may still remain non-actionable due to profitability or safety gates

Watchlist remove candidates:

- are generated when liquidity deterioration, repeated stale data, or explicit
  exclusion rules apply

Blocked candidates:

- must retain block reasons
- must map to non-actionable states

Report-only candidates:

- may be surfaced for diagnostics and watch-only explanation
- must not be interpreted as trade approval

## Stale and Quality Policy

v4.3 inherits v4.2 stale-data policy.

Rules:

- stale realtime data fails closed by default
- report-only downgrade is allowed only when explicitly declared
- stale or report-only data must not produce actionable scanner decisions
- incomplete event data must not become actionable
- impossible timestamps, missing timestamps, or provider/received timestamp
  mismatches beyond threshold must block or downgrade
- data quality flags must be preserved in candidate reports

Recommended quality outcomes:

- `SCANNER_READY` only when all required scanner gates pass
- `REPORT_ONLY_STALE` only under explicit report-only mode
- `BLOCKED_QUALITY` for stale fail-closed, timestamp invalidity, unsafe flags,
  or critical completeness loss
- `INSUFFICIENT_DATA` for missing fields that prevent deterministic evaluation

## Integration with v3.3 Discovery

v4.3 may later feed or reuse v3.3 market discovery concepts.

Design rules:

- v4.3 must preserve compatibility with `DISCOVER / WATCH / EXCLUDE`
- compatibility is report-level only
- realtime scanner candidates must not silently replace v3.3 batch discovery
  semantics
- deterministic fixture-only replay must remain possible
- volume spike signals should align conceptually with v3.3 volume spike
  discovery, but v4.3 still operates on normalized realtime-derived snapshots

Potential future use:

- merge v4.3 scanner candidates into a broader market universe review
- compare realtime-derived `WATCH` items against batch discovery candidates
- keep a unified compatibility field without collapsing v4.3 internal states

## Integration with v3.2 Technical Evidence

v4.3 may later request or reference technical evidence.

Potential referenced fields:

- MACD
- RSI
- MA
- HMA
- ATR
- volume evidence
- divergence evidence
- setup grade
- evidence freshness

Rules:

- v4.3 does not directly approve trades based on technical evidence
- technical evidence may enrich scanner candidate explanation only
- stale or weak technical evidence must remain diagnostic, not approving

## Integration with v4.1 Profitability Safety

v4.3 may later filter or annotate candidates with profitability safety.

Potential referenced concepts:

- `TrackAwareProfitabilityCheck`
- estimated net profit
- break-even movement
- cost-aware minimum target move
- report-only profitability context
- non-actionable profitability context

Rules:

- candidates must not be approved when profitability context is non-actionable
- placeholder or needs-evidence fee or tax context must default to
  `REPORT_ONLY`
- report-only profitability context may annotate candidates but must not enable
  scanner-ready trade interpretation

## Integration with v3.12 Advisory Prompt Packs

v4.3 scanner reports may later become advisory context for prompt packs.

Rules:

- prompt packs must declare supported tracks
- prompt packs must respect report-only and non-actionable scanner states
- prompt packs must not convert scanner candidates into direct trade
  instructions
- prompt packs must not infer market assumptions without explicit
  `StrategyTrack` and resolved `MarketProfile`
- no LLM or model runtime execution belongs in v4.3

## CLI Design Proposal

Recommended CLI commands:

- `domestic-scanner-config-validate --fixture-file ...`
- `domestic-scanner-candidates --fixture-file ... [--output-file ...]`
- `domestic-scanner-watchlist-plan --fixture-file ... [--output-file ...]`
- `domestic-scanner-quality-report --fixture-file ... [--output-file ...]`

Command purposes:

- config validation checks domestic-only and schema safety
- candidates produces deterministic scanner candidate reports
- watchlist plan produces add/remove proposals only
- quality report explains stale, blocked, report-only, and unsafe inputs

## Fixture Design

v4.3 fixture set should include local JSON examples for:

- valid domestic scanner config
- valid normalized event input
- volume spike candidate
- price momentum candidate
- liquidity candidate
- watchlist add plan
- watchlist remove plan
- stale event fail-closed case
- explicit report-only stale candidate
- missing track failure
- missing market profile failure
- `OVERSEAS_US` rejection
- unsafe order-trigger attempt failure

Fixture requirements:

- explicit local JSON only
- deterministic timestamps and event values
- explicit fixture source markers
- no hidden runtime dependencies

## System Smoke Design

System smoke must use temporary local JSON fixtures only.

Smoke must confirm:

- `domestic_scanner_fixture_run=true`
- `strategy_track_required=true`
- `domestic_kr_only=true`
- `market_profile_resolved=true`
- `normalized_realtime_event_consumed=true`
- `scanner_candidate_report_generated=true`
- `kiwoom_api_called=false`
- `broker_api_called=false`
- `credentials_accessed=false`
- `external_network_calls=false`
- `orders_created=false`
- `live_or_prod_used=false`

The smoke run remains offline and deterministic.

## Hard Restrictions

v4.3 design must preserve all of the following:

- no Kiwoom API calls
- no broker API calls
- no credentials access
- no account access
- no WebSocket connections
- no realtime market-data fetch
- no realtime FX fetch
- no order submission
- no `OrderIntent`
- no order drafts
- no execution approval
- no `LIVE`
- no `PROD`
- no real provider integration
- no account-read
- no token handling
- no modification to v4.0, v4.1, v4.2, or v3.12 implementation

## Recommended v4.3 Implementation Boundary

When implementation begins later, the allowed boundary should be:

- strict local JSON fixture loader
- domestic scanner config validation
- deterministic event-to-scanner snapshot conversion
- deterministic scanner candidate generation
- compatibility discovery mapping
- watchlist update planning
- scanner quality report generation
- offline system smoke

Forbidden boundary:

- live subscriptions
- Kiwoom runtime connection
- broker integration
- account integration
- order path creation
- execution path activation
- non-domestic track support
