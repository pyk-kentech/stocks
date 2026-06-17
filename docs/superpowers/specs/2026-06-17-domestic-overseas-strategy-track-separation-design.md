# v4.0 Domestic/Overseas Strategy Track Separation Design

## Scope

v4.0 designs a track-first separation layer for domestic Korean stocks and
overseas US stocks.

The design exists because Kiwoom is the only currently usable provider path,
and it must be modeled as `DOMESTIC_KR` only. Overseas or US stock provider
support remains unresolved and must stay simulation-only or design-only for
now.

This is design-only in this step. It does not implement runtime code, does not
connect any provider, and does not activate any live execution path.

## Release Baseline

The design assumes the current completed release line is:

- `v3.0.0-strategy-core-local-llm-safety-boundary`
- `v3.1.0-strategy-fixture-backtest-harness`
- `v3.2.0-technical-setup-evidence-pack`
- `v3.3.0-market-universe-volume-spike-discovery`
- `v3.4.0-llm-feature-store-signal-evaluation`
- `v3.5.0-trade-plan-basket-risk-engine`
- `v3.6.0-paper-trading-strategy-evaluation`
- `v3.7.0-walk-forward-replay-policy-optimizer`
- `v3.8.0-local-llm-advisory-adapter-hardening`
- `v3.9.0-local-model-runtime-adapter-contract`
- `v3.10.0-local-model-backend-selection-benchmark`
- `v3.11.0-local-model-backend-decision-report` -> `53f9dd2`

Also in context:

- `v3.12` has design only and is not being implemented here
- `v3.12` design document:
  `docs/superpowers/specs/2026-06-17-offline-prompt-pack-advisory-task-suite-design.md`
- `v3.12` design commit: `c90c259`

v4.0 does not modify the v3.11 tag and does not modify the existing v3.12
design commit.

## Problem Statement

Domestic Korean stocks and overseas or US stocks do not share the same trading
assumptions.

They differ across:

- fee rules
- tax rules
- FX exposure
- trading hours
- session structure
- settlement timing
- cash availability
- realtime data assumptions
- provider capability assumptions

Those differences are material enough that a single implicit market profile is
unsafe. The system needs explicit track separation.

## Goals

v4.0 should define a clean strategy-track separation model that:

- makes `StrategyTrack` a mandatory top-level input
- routes all market-specific assumptions through a resolved `MarketProfile`
- separates `DOMESTIC_KR` and `OVERSEAS_US` assumptions explicitly
- allows shared base strategy logic only after track resolution
- preserves simulation-only handling for unresolved overseas provider paths
- remains offline, deterministic, and schema-driven in its first future
  implementation

## Core Principle

v4.0 uses track-first architecture.

`StrategyTrack` is not a lightweight profile selector. It is the top-level
mandatory input for all downstream strategy, fee, tax, FX, realtime-data,
settlement, and provider-capability decisions.

Required routing flow:

- `StrategyTrack`
- resolve `MarketProfile`
- inject track-aware assumptions
- run shared or track-specific logic

If `StrategyTrack` is missing, ambiguous, or inconsistent with the rest of the
fixture, validation must fail closed.

## Non-Goals

v4.0 does not:

- call broker APIs
- access credentials
- access accounts
- connect WebSocket or realtime feeds
- submit orders
- create `OrderIntent`
- create order drafts
- approve execution
- use LIVE mode
- use PROD mode
- change production policy
- implement real provider integration
- implement account-read
- implement token handling
- implement realtime market data connections

## StrategyTrack Definition

v4.0 should define exactly two strategy tracks:

- `DOMESTIC_KR`
- `OVERSEAS_US`

Rules:

- track is mandatory
- track must be explicit in fixtures and validation inputs
- no default track inference
- no mixed-track evaluation inside one unresolved strategy request

The future implementation should reject:

- missing track
- unknown track
- track conflicting with market or provider assumptions

## Top-Level Mandatory Input Rule

`StrategyTrack` must be the first routing key for market-specific assumptions.

The following downstream systems must be track-aware:

- strategy evaluation
- trade-plan calculation
- risk checks
- fee modeling
- tax modeling
- FX modeling
- net-profit modeling
- realtime-data capability checks
- provider-capability checks
- settlement and cash availability assumptions

Neither `DOMESTIC_KR` nor `OVERSEAS_US` may silently inherit assumptions from
the other track.

## MarketProfile Definition

v4.0 should define a `MarketProfile` model that is derived from
`StrategyTrack`.

Recommended fields:

- market id
- country
- base currency
- exchange or session profile
- trading hours
- settlement or cash availability rule
- fee or tax profile reference
- realtime data profile reference
- provider capability reference

The profile may use placeholders or schema-level references in v4.0 rather than
fully implemented fee or session engines.

## MarketProfile Contract

Recommended `MarketProfile` fixture or schema shape:

```json
{
  "strategy_track": "DOMESTIC_KR",
  "market_profile": {
    "market_id": "KRX",
    "country": "KR",
    "base_currency": "KRW",
    "exchange_session_profile": "KRX_REGULAR",
    "trading_hours": "placeholder",
    "settlement_cash_availability": "placeholder",
    "fee_tax_profile_reference": "fee_tax/domestic_kr.json",
    "realtime_data_profile_reference": "realtime/domestic_kr.json",
    "provider_capability_reference": "providers/kiwoom_domestic_kr.json"
  }
}
```

Validation should require:

- one explicit `strategy_track`
- one resolved `market_profile`
- track and market profile consistency
- no cross-track fee, FX, or provider references

## ProviderCapabilityByTrack Definition

v4.0 should define `ProviderCapabilityByTrack` with these fields:

- provider id
- track
- supported markets
- supported asset types
- domestic support
- overseas support
- realtime support
- order support
- account support
- status enum

Allowed status enum values:

- `AVAILABLE_DOMESTIC_ONLY`
- `SIMULATION_ONLY`
- `FUTURE_PROVIDER_CANDIDATE`
- `REJECTED_UNSUPPORTED_MARKET`
- `NEEDS_MORE_EVIDENCE`

## DOMESTIC_KR Profile

The domestic Korean profile must include:

- provider candidate: Kiwoom
- provider status: `AVAILABLE_DOMESTIC_ONLY`
- currency: KRW
- market: KRX
- domestic stock universe
- domestic fee and tax placeholders
- KRX-specific rule placeholders:
  - price limit
  - volatility interruption
  - single price auction
- domestic realtime data capability placeholder
- no overseas assumptions

This profile should be considered the only currently usable provider-backed
track in v4.0 design terms.

## OVERSEAS_US Profile

The overseas US profile must include:

- provider: unresolved
- status: `SIMULATION_ONLY`
- future provider candidates:
  - LS
  - KIS
- currency: USD
- FX reference: USD/KRW
- SEC fee placeholder
- FX spread placeholder
- overseas capital gains tax placeholder
- US session profile:
  - pre-market
  - regular session
  - after-hours
- no live, order, or account integration

This profile must remain simulation-only or design-only until real provider
evidence and capability validation exist.

## Provider Modeling Rules

Provider assumptions must be track-scoped.

Rules:

- Kiwoom must be modeled as `DOMESTIC_KR` only
- Kiwoom must not be reused for `OVERSEAS_US`
- unresolved overseas providers must not be treated as available by default
- provider capability resolution must be explicit per track
- lack of provider evidence should resolve to simulation-only or needs-more-
  evidence status

## Strategy Compatibility Rules

The design must explicitly state:

- base strategy logic can be shared
- market-specific assumptions must be injected through `MarketProfile`
- domestic and overseas strategies must not blindly share:
  - fee assumptions
  - tax assumptions
  - FX assumptions
  - trading-hour assumptions
  - settlement assumptions
  - realtime data assumptions
  - provider capability assumptions

Shared logic is allowed only after a valid track-aware profile has been
resolved.

## Validation Fail-Closed Rules

Validation should fail closed when:

- `StrategyTrack` is missing
- `StrategyTrack` is ambiguous
- track conflicts with provider capability assumptions
- track conflicts with market currency assumptions
- track conflicts with fee, FX, or session references
- overseas track tries to use domestic-only provider capability
- domestic track tries to use overseas-only assumptions without explicit model

The system must prefer rejection over silent fallback.

## Net-Profit Implications

v4.0 should explicitly state:

- gross return is not enough
- expected net profit must be track-aware
- future `v4.1` should implement a fee, tax, FX, and net-profit calculator
- trade eligibility should eventually depend on expected net profit after costs

This prevents shared gross-return logic from pretending that domestic and
overseas returns are economically equivalent.

## Fee, Tax, FX, And Settlement Separation

v4.0 does not implement those engines, but it must separate them at the schema
and validation level.

Required separation areas:

- domestic fee placeholders vs overseas fee placeholders
- domestic tax placeholders vs overseas tax placeholders
- KRW base-currency assumptions vs USD base-currency assumptions
- FX conversion reference placeholders for overseas track
- domestic settlement placeholders vs overseas settlement placeholders

No track may reuse another track's unresolved cost assumptions by default.

## Realtime Data Separation

Realtime assumptions must also be track-aware.

Rules:

- domestic realtime capability is modeled only as a placeholder capability
  reference
- overseas realtime capability remains unresolved and simulation-only
- no realtime connection implementation belongs in v4.0
- no WebSocket, token, or session handling belongs in v4.0

## Suggested Models

Recommended schema names:

- `StrategyTrack`
- `MarketProfile`
- `ProviderCapabilityByTrack`
- `TrackResolvedStrategyRequest`
- `TrackComparisonReport`

`TrackResolvedStrategyRequest` should contain:

- track
- market profile
- provider capability profile
- shared strategy payload
- track-specific placeholder references

## Fixture Design

v4.0 should use explicit local JSON fixtures only.

Recommended fixture types:

- strategy track profile fixture
- provider capability by track fixture
- track comparison fixture

Each fixture should be self-contained and deterministic.

## CLI Design Proposal

Recommended CLI names:

- `strategy-track-profile-validate --fixture-file ...`
- `strategy-track-profile-show --fixture-file ...`
- `strategy-track-compare --fixture-file ... [--output-file ...]`

Recommended behavior:

`strategy-track-profile-validate`

- validate explicit track, market profile, provider capability, and cross-field
  consistency

`strategy-track-profile-show`

- display normalized track profile and resolved market assumptions

`strategy-track-compare`

- compare domestic and overseas track assumptions side by side
- emit deterministic local JSON report only

No command may call a broker, provider API, account path, or realtime
connection.

## System Smoke Design

System smoke should use temporary local JSON strategy-track fixtures only.

Expected smoke indicators:

- `strategy_track_fixture_run=true`
- `broker_api_called=false`
- `credentials_accessed=false`
- `external_network_calls=false`
- `orders_created=false`
- `live_or_prod_used=false`

The smoke path must not:

- call broker APIs
- access credentials
- access accounts
- connect realtime feeds
- create `OrderIntent`
- create order drafts
- submit orders

## Testing Plan

The future implementation should require:

- strict `StrategyTrack` validation
- strict `MarketProfile` validation
- strict `ProviderCapabilityByTrack` validation
- missing track fail-closed tests
- ambiguous track fail-closed tests
- domestic profile validation tests
- overseas profile validation tests
- domestic-only Kiwoom capability tests
- simulation-only overseas profile tests
- track comparison report tests
- no broker/Kiwoom/account/order/network import tests in core modules
- offline deterministic system-smoke preservation

All tests must remain local, deterministic, and fixture-driven.

## Future Implementation Boundary

Allowed for future v4.0 implementation:

- local schema implementation
- local fixture loaders
- deterministic validation and reporting
- track-aware comparison and normalization logic

Forbidden for future v4.0 implementation:

- broker API calls
- credential access
- account access
- realtime market data connections
- token handling
- order submission
- `OrderIntent` creation
- order draft creation
- execution approval
- LIVE or PROD activation

## Safety Invariants

v4.0 must preserve these invariants:

- no broker API calls
- no credential access
- no account access
- no realtime connections
- no order submission
- no `OrderIntent`
- no order draft
- no execution approval
- no LIVE
- no PROD
- no production policy change
- no silent track inference
- no silent domestic and overseas assumption sharing

## Verification Baseline For Future Implementation

Any future v4.0 implementation should be validated with:

```bash
git status --short
python3.11 -m pytest -q
python3.11 -m compileall -q src
git diff --check
python3.11 -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs
```

Expected safety indicators:

- `strategy_track_fixture_run=true`
- `broker_api_called=false`
- `credentials_accessed=false`
- `external_network_calls=false`
- `orders_created=false`
- `live_or_prod_used=false`

## Summary

v4.0 should introduce explicit domestic and overseas strategy-track separation
by making `StrategyTrack` the mandatory top-level routing input for all
downstream market-specific assumptions.

`DOMESTIC_KR` should model Kiwoom-backed domestic Korean stock assumptions only.
`OVERSEAS_US` should remain unresolved and simulation-only, with future provider
candidates documented but not activated.

The first future implementation should stop at local schema, fixture
validation, and deterministic comparison or reporting. No provider integration
belongs in v4.0.
