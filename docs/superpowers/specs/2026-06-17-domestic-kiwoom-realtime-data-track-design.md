# v4.2 Domestic Kiwoom Realtime Data Track Design

## Scope

v4.2 designs a domestic Korean stock realtime-data track for future Kiwoom
integration.

This design prepares the project for:

- realtime market monitoring
- volume-spike discovery
- scanner inputs
- watchlist updates
- track-aware strategy evaluation

In this milestone, all of that remains fixture-only, offline, deterministic,
and non-executing.

This is design-only. It does not implement runtime code, does not connect
Kiwoom, does not open WebSocket sessions, and does not activate broker or
order paths.

## Release Baseline

The completed foundations relevant to this design are:

- `v4.0.0-domestic-overseas-strategy-track-separation` -> `d6d430d`
- `v4.1.0-market-profile-fee-tax-fx-net-profit-calculator` -> `3df8289`
- `v3.12.0-offline-prompt-pack-advisory-task-suite` -> `656c7ea`

v4.2 must preserve:

- v4.0 track-first routing
- v4.1 profitability and report-only safety
- v3.12 prompt-pack advisory safety

## Architecture Position

The v4.2 domestic realtime track sits under `DOMESTIC_KR` only.

Required routing flow:

- `StrategyTrack = DOMESTIC_KR`
- resolved `MarketProfile`
- resolved domestic realtime provider profile
- offline realtime fixture normalization and quality evaluation
- scanner or advisory inputs in non-executing form

Rules:

- the component must reject `OVERSEAS_US`
- the component must not bypass v4.0 track-first validation
- the component must not bypass v4.1 profitability or report-only safety
- realtime data must not directly create orders, `OrderIntent`, order drafts,
  or execution approvals

## Kiwoom Scope

Kiwoom is modeled only as a future domestic realtime-data provider candidate.

Rules:

- Kiwoom must remain `DOMESTIC_KR` only
- the design must not claim overseas or US support
- the design must not implement real Kiwoom API calls
- the design must not require credentials
- the design must not require account access
- the design must not require token handling

The purpose of v4.2 is to define the shape and safety boundaries of future
domestic realtime ingestion, not to activate the provider.

## Realtime Data Concepts

v4.2 should define these design-level schemas:

- `RealtimeProviderProfile`
- `RealtimeSubscriptionPlan`
- `RealtimeSubscriptionLimit`
- `RealtimeMarketEvent`
- `RealtimeQuoteEvent`
- `RealtimeTradeEvent`
- `RealtimeOrderbookEvent`
- `RealtimeVolumeSpikeEvent`
- `RealtimeDataQualityReport`
- `RealtimeStalenessPolicy`
- `RealtimeScannerInputSnapshot`

These schemas should remain local, fixture-driven, deterministic, and
provider-profile aware.

## RealtimeProviderProfile

Recommended fields:

- provider id
- strategy track
- market id
- supported asset types
- provider mode
- max symbol capacity placeholder
- subscription grouping placeholder
- event types supported
- normalized field availability
- provider staleness threshold
- received timestamp tolerance threshold
- status

Recommended status values:

- `SIMULATION_ONLY`
- `FUTURE_PROVIDER_CANDIDATE`
- `NEEDS_EVIDENCE`
- `DISABLED`

Rules:

- `strategy_track` must be `DOMESTIC_KR`
- provider profile must reject `OVERSEAS_US`
- fixture-only provider profiles must be clearly marked non-live

## RealtimeSubscriptionPlan

Recommended fields:

- plan id
- strategy track
- provider id
- watch universe
- symbol list
- subscription groups
- priority tiers
- dynamic add policy
- dynamic remove policy
- stale subscription handling
- fallback mode when capacity is exceeded

Rules:

- subscription planning is local and declarative only
- no real subscription execution belongs in v4.2
- plan must be tied to domestic Korean symbols only

## RealtimeSubscriptionLimit

Recommended fields:

- provider id
- max subscribed symbols placeholder
- max groups placeholder
- priority tier policy
- overflow policy
- downgrade policy
- limit evidence placeholder

Rules:

- symbol limits must remain provider-profile specific
- exceeding limits must not silently drop into undefined behavior
- fallback behavior must be explicit in the plan

## RealtimeMarketEvent

This is the normalized common base event.

Recommended fields:

- provider id
- strategy track
- market id
- symbol
- event type
- provider timestamp
- received timestamp
- data quality flags
- source fixture id

Rules:

- the normalized base must preserve source timestamps
- missing timestamps must not be hidden
- invalid timing must surface as quality flags

## RealtimeQuoteEvent

Recommended fields beyond base event:

- last price
- best bid
- best ask
- bid size
- ask size
- quote spread
- cumulative volume if available

## RealtimeTradeEvent

Recommended fields beyond base event:

- trade price
- trade size
- cumulative volume
- cumulative value placeholder
- aggressive side placeholder if available

## RealtimeOrderbookEvent

Recommended fields beyond base event:

- top bid levels
- top ask levels
- aggregate bid depth
- aggregate ask depth
- imbalance placeholder

## RealtimeVolumeSpikeEvent

Recommended fields:

- symbol
- event timestamp
- observed volume
- baseline volume placeholder
- spike ratio
- supporting price context
- quality flags
- source snapshot id

This event is a derived offline analytical object and must not be treated as an
execution signal by itself.

## RealtimeDataQualityReport

Recommended fields:

- provider id
- strategy track
- market id
- symbol count
- event count
- stale event count
- invalid timestamp count
- incomplete field count
- dropped event count placeholder
- quality status
- warnings
- block reasons

This report should explain whether the fixture is suitable for monitoring,
scanner input, replay explanation, or only diagnostics.

## RealtimeStalenessPolicy

Recommended fields:

- default policy
- provider timestamp required
- received timestamp required
- maximum provider to received lag
- maximum event age at evaluation time
- impossible timestamp rejection rule
- timestamp mismatch treatment
- explicit report-only override flag

Default policy:

- `FAIL_CLOSED`

Rules:

- stale realtime data must fail closed by default
- stale realtime data must not feed actionable scanner decisions, trade
  eligibility, advisory approval, `OrderIntent`, order draft, or execution
  paths
- `REPORT_ONLY` downgrade is allowed only when the fixture or context
  explicitly declares non-actionable reporting mode
- `REPORT_ONLY` output must clearly mark stale data as non-actionable
- fixture-only stale data may be used for quality reports, diagnostics, and
  offline replay explanation only
- missing timestamps, impossible timestamps, or provider/received timestamp
  mismatch beyond threshold must be treated as stale or invalid

## RealtimeScannerInputSnapshot

Recommended fields:

- strategy track
- market profile reference
- provider profile reference
- symbol
- last normalized quote or trade context
- latest volume spike context
- freshness status
- quality status
- report-only flag

This snapshot should be the bridge from normalized event streams to later
scanner or evidence layers.

## Subscription Planning

v4.2 should include design support for:

- watch universe
- max subscribed symbols placeholder
- subscription groups
- priority tiers
- dynamic add and remove policy
- fallback when symbol limit is exceeded
- stale subscription handling
- no real subscription execution

Recommended planning behavior:

- high-priority symbols stay pinned
- lower-priority symbols rotate or downgrade when capacity is exceeded
- overflow resolves to explicit fallback categories, not silent omission
- stale subscriptions should degrade to report-only diagnostics or fail closed
  depending on context

## TR / Request vs Realtime Distinction

v4.2 must explicitly distinguish:

- realtime push or event data
- TR or request lookup data

Rules:

- realtime push or event data is preferred for broad monitoring
- TR or request polling should be reserved for supplemental lookup
- large-universe polling should be avoided
- rate-limit assumptions must remain provider-profile specific
- no actual TR request implementation belongs in this milestone

This distinction matters because future Kiwoom integration should not be
designed around unrealistic large-universe polling loops.

## Event Normalization

Normalized event fields should include:

- provider id
- track
- market id
- symbol
- event type
- provider timestamp
- received timestamp
- price
- volume
- cumulative volume
- bid and ask fields if available
- data quality flags
- source fixture id

Rules:

- normalization must preserve raw timing semantics
- missing provider timestamp must not be backfilled silently
- invalid symbols or event types must be rejected or flagged
- fixture origin must remain visible

## Scanner Integration Design

Future normalized realtime events should be able to feed:

- volume-spike discovery
- watchlist updates
- technical setup evidence
- strategy-track-aware evaluation
- paper and replay validation
- offline advisory and prompt-pack context

Rules:

- scanner inputs must remain track-aware
- domestic realtime data must feed only domestic market assumptions
- normalized events may enrich evidence, but must not directly approve trades
- report-only or stale events must not become actionable scanner outcomes

## Safety And Fail-Closed Rules

v4.2 must include:

- missing `StrategyTrack` fails
- non-`DOMESTIC_KR` track fails
- missing `MarketProfile` fails
- missing provider profile fails
- stale realtime data fails closed by default
- incomplete event data must not become actionable
- fixture-only data must be clearly marked
- realtime data must not directly trigger orders

Additional fail-closed rules:

- missing provider timestamp fails or degrades only under explicit
  non-actionable report-only context
- impossible timestamp fails closed
- provider and received timestamp mismatch beyond threshold fails closed by
  default
- stale or invalid events must not feed scanner approvals, trade eligibility,
  advisory approval, or execution-adjacent artifacts

## CLI Design Proposal

Suggested CLI commands:

- `domestic-realtime-profile-validate --fixture-file ...`
- `domestic-realtime-plan-show --fixture-file ...`
- `domestic-realtime-event-normalize --fixture-file ... [--output-file ...]`
- `domestic-realtime-quality-report --fixture-file ... [--output-file ...]`

Expected behavior:

- local JSON fixture only
- deterministic JSON output
- explicit quality flags and staleness results
- explicit domestic-only track validation

## Fixture Design

v4.2 should define local JSON fixture examples for:

- valid Kiwoom domestic realtime provider profile
- valid subscription plan
- subscription limit exceeded case
- valid trade event normalization
- valid quote or orderbook event normalization
- volume spike event
- stale data failure
- missing track failure
- `OVERSEAS_US` rejection
- unsafe order-trigger attempt failure

Suggested fixture sections:

- strategy track
- resolved market profile
- provider profile
- subscription plan if relevant
- event payloads
- staleness policy
- expected validation mode
- expected quality outcome

## System Smoke Design

System smoke must use temporary local JSON fixtures only.

Expected smoke indicators:

- `domestic_realtime_fixture_run=true`
- `strategy_track_required=true`
- `domestic_kr_only=true`
- `market_profile_resolved=true`
- `kiwoom_api_called=false`
- `broker_api_called=false`
- `credentials_accessed=false`
- `external_network_calls=false`
- `orders_created=false`
- `live_or_prod_used=false`

No smoke path may require:

- Kiwoom API calls
- broker API calls
- credentials
- accounts
- WebSocket connections
- realtime market fetch
- realtime FX fetch
- order creation
- execution approval

## Suggested Future Implementation Boundary

Allowed for future v4.2 implementation:

- local schema implementation
- local fixture loaders
- normalized domestic realtime event validators
- offline subscription planning reports
- offline data quality reports
- domestic scanner input snapshots

Forbidden for future v4.2 implementation:

- real Kiwoom API calls
- broker API calls
- credential or token access
- account access
- WebSocket sessions
- realtime market fetching
- realtime FX fetching
- order submission
- `OrderIntent` creation
- order draft creation
- execution approval
- LIVE or PROD activation
- overseas extension through Kiwoom

## Safety Invariants

v4.2 must preserve these invariants:

- `DOMESTIC_KR` only
- no `OVERSEAS_US` support through Kiwoom
- no Kiwoom API calls
- no broker API calls
- no credentials or tokens
- no accounts
- no WebSocket
- no realtime network fetching
- no `OrderIntent`
- no order draft
- no execution approval
- no LIVE
- no PROD
- no production policy change
- stale realtime data fails closed by default
- report-only downgrade is explicit and non-actionable only

## Summary

v4.2 should introduce a domestic-only realtime-data design track for future
Kiwoom integration under `StrategyTrack = DOMESTIC_KR`.

It must remain track-first, domestic-only, fixture-only, and fail-closed.
Stale realtime data must fail closed by default, with explicit report-only
diagnostic use as the only downgrade path.

The first future implementation should stop at local schema, normalization,
quality reporting, and offline scanner-input preparation. No provider
integration or execution path belongs in v4.2.
