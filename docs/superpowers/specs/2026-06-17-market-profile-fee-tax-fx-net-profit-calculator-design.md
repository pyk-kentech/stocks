# v4.1 MarketProfile Fee/Tax/FX/Net-Profit Calculator Design

## Scope

v4.1 designs a track-aware profitability calculation layer that runs only
after:

- `StrategyTrack`
- resolved `MarketProfile`

This layer exists to prevent gross-return-only reasoning from silently
ignoring market-specific fees, taxes, FX costs, settlement assumptions, and
reporting-currency impacts.

This is design-only in this step. It does not implement runtime code, does not
fetch broker or FX data, and does not activate any live or production path.

## Release Baseline

The current implemented baseline is:

- `v4.0.0-domestic-overseas-strategy-track-separation` -> `d6d430d`

Relevant context:

- v4.0 already enforces track-first routing:
  `StrategyTrack -> MarketProfile resolution -> track-aware evaluation`
- v4.0 added only local fixture, schema, validation, comparison, CLI, and
  smoke logic
- v3.12 remains design-only and is not part of v4.1

v4.1 must not modify v4.0 behavior in this design step.

## Problem Statement

Gross return is not enough.

Two trades with identical gross PnL can have materially different net results
because of:

- buy-side commission
- sell-side commission
- transaction tax
- regulatory fees
- FX spread
- conversion fees
- reporting-currency conversion
- annual realized-gain-dependent tax treatment
- market-specific break-even movement

Without a track-aware cost model, the system can overstate profitability and
understate the movement required to break even.

## Goals

v4.1 should define a deterministic, local, track-aware profitability design
that:

- consumes a resolved `MarketProfile`
- requires explicit `StrategyTrack`
- models fee, tax, FX, and reporting-currency assumptions separately
- estimates expected net PnL and expected net return after costs
- estimates break-even exit price and minimum required move after costs
- allows future trade eligibility to depend on post-cost profitability
- fails closed when track, market profile, or required cost profiles are
  missing or stale

## Core Principle

v4.1 is market-profile-driven, not inference-driven.

Required routing flow:

- `StrategyTrack`
- resolve `MarketProfile`
- resolve fee/tax/currency/FX cost profiles
- estimate track-aware gross and net profitability
- optionally feed future eligibility logic

The profitability layer must not infer market assumptions without an explicit
`StrategyTrack` and resolved `MarketProfile`.

If `StrategyTrack`, `MarketProfile`, `FeeTaxProfile`, `CurrencyProfile`, or
required `FXCostProfile` is missing or inconsistent, validation must fail
closed.

## Non-Goals

v4.1 does not:

- call broker APIs
- access accounts
- access credentials or tokens
- connect WebSocket or realtime feeds
- fetch realtime FX
- fetch realtime market data
- submit orders
- create `OrderIntent`
- create order drafts
- approve execution
- use LIVE mode
- use PROD mode
- change production policy
- hardcode final tax law values
- present outputs as legal or tax advice

## Core Schemas

v4.1 should define these schema-level structures:

- `FeeTaxProfile`
- `CurrencyProfile`
- `FXCostProfile`
- `TradeCostEstimate`
- `NetProfitEstimate`
- `BreakEvenMoveEstimate`
- `TrackAwareProfitabilityCheck`

These schemas should be local, explicit, deterministic, and fixture-driven.

## FeeTaxProfile

Recommended `FeeTaxProfile` fields:

- track
- market id
- asset type
- buy commission model
- sell commission model
- transaction tax model
- regulatory fee model
- annual tax treatment placeholder
- tax estimate mode
- effective date placeholder
- evidence source placeholder
- status

Allowed tax estimate modes:

- `EXCLUDED`
- `ESTIMATED_PER_TRADE`
- `ESTIMATED_ANNUALIZED`
- `REPORT_ONLY`

Allowed profile status values:

- `ACTIVE`
- `PLACEHOLDER`
- `NEEDS_EVIDENCE`
- `DISABLED`

Design rules:

- `ACTIVE` profiles may be used for normal net-profit estimation
- `PLACEHOLDER` and `NEEDS_EVIDENCE` profiles are allowed by default only in
  `REPORT_ONLY` mode
- `REPORT_ONLY` outputs must be clearly marked non-actionable
- `REPORT_ONLY` outputs must not produce trade eligibility approval
- `PLACEHOLDER` and `NEEDS_EVIDENCE` profiles must not be treated as final fee,
  tax, legal, or regulatory assumptions
- `SIMULATION_ONLY` may be documented as a future explicit opt-in what-if mode,
  but it must not be the default for placeholder profiles

## CurrencyProfile

Recommended `CurrencyProfile` fields:

- base currency
- settlement currency
- reporting currency
- FX reference pair
- FX rate source placeholder
- FX timestamp requirement
- stale FX policy
- missing FX policy

Design rules:

- domestic KRW-denominated trades may use identical base, settlement, and
  reporting currencies
- overseas USD trades may use USD base and settlement currencies with KRW
  reporting currency
- missing FX policy must fail closed for cross-currency reporting
- stale FX policy must fail closed for overseas profitability estimates unless
  the fixture explicitly marks the estimate as non-actionable report-only

## FXCostProfile

Recommended `FXCostProfile` fields:

- FX spread placeholder
- conversion fee placeholder
- buy-side conversion handling
- sell-side conversion handling
- realized vs unrealized FX distinction
- KRW reporting conversion handling for overseas trades
- FX rate timestamp placeholder
- FX evidence source placeholder
- status

Design rules:

- FX spread and conversion cost must be modeled separately from price movement
- realized and unrealized FX effects must not be conflated
- overseas reporting in KRW must include explicit reporting-currency conversion
- missing or stale FX for overseas track must fail closed unless the fixture is
  explicitly non-actionable report-only

## TradeCostEstimate

Recommended `TradeCostEstimate` fields:

- track
- market id
- entry price
- exit price
- quantity
- gross entry amount
- gross exit amount
- buy commission amount
- sell commission amount
- transaction tax amount
- regulatory fee amount
- FX spread cost amount
- FX conversion fee amount
- estimated tax amount
- total estimated costs
- reporting currency
- profile status summary

This structure should explain where total costs come from before net PnL is
computed.

## NetProfitEstimate

Recommended `NetProfitEstimate` fields:

- gross PnL amount
- total estimated costs
- expected net PnL amount
- expected net return percentage
- reporting currency
- tax estimate mode
- actionable status
- non-actionable reasons
- evidence completeness status

Design rules:

- gross and net values must be separated explicitly
- actionable status must be false for default placeholder or needs-evidence
  profiles
- outputs must explain whether tax was excluded, estimated per trade,
  annualized, or report-only

## BreakEvenMoveEstimate

Recommended `BreakEvenMoveEstimate` fields:

- break-even exit price
- break-even percentage move
- minimum target price after costs
- minimum required move after costs
- minimum risk/reward after costs
- track-specific rounding placeholder
- tick-size placeholder

Break-even logic must operate after cost accumulation, not before.

## TrackAwareProfitabilityCheck

Recommended `TrackAwareProfitabilityCheck` fields:

- strategy track
- resolved market profile reference
- fee/tax profile reference
- currency profile reference
- FX cost profile reference if required
- trade cost estimate
- net profit estimate
- break-even move estimate
- eligibility implication summary
- validation status
- warnings
- block reasons
- advisory-only metadata

This object should act as the future bridge between cost estimation and trade
eligibility gates, while remaining advisory-only in early implementation.

## DOMESTIC_KR Design

The domestic Korean track must include:

- currency: KRW
- no FX conversion for KRW-denominated trades
- domestic commission placeholders
- domestic transaction tax placeholders
- KRX-specific cost placeholder support
- annual tax treatment placeholder
- no hardcoded final tax law assumptions
- status may remain `PLACEHOLDER` or `NEEDS_EVIDENCE`

Design rules:

- domestic fee and tax profiles must still be explicit
- domestic track must not silently borrow overseas tax or FX assumptions
- domestic trades may still be non-actionable if fee or tax profiles remain
  placeholder-only

## OVERSEAS_US Design

The overseas US track must include:

- trade currency: USD
- reporting currency: KRW
- USD/KRW FX reference
- buy commission placeholders
- sell commission placeholders
- SEC or regulatory fee placeholder
- FX spread placeholder
- FX conversion cost placeholder
- overseas capital gains tax placeholder
- annual realized PnL dependency placeholder
- annual deduction or threshold placeholder without hardcoded final law values
- status may remain `PLACEHOLDER` or `NEEDS_EVIDENCE`

Design rules:

- overseas trade profitability must distinguish trade-currency PnL from
  reporting-currency PnL
- overseas tax treatment may depend on year-to-date realized gain state in
  future implementation
- stale or missing USD/KRW reference must fail closed for actionable outputs

## Net-Profit Calculation Flow

The conceptual calculation flow should be:

1. Resolve `StrategyTrack`
2. Resolve `MarketProfile`
3. Resolve `FeeTaxProfile`
4. Resolve `CurrencyProfile`
5. Resolve `FXCostProfile` if needed
6. Calculate gross entry amount
7. Calculate gross exit amount
8. Calculate gross PnL
9. Calculate buy-side fees
10. Calculate sell-side fees
11. Calculate transaction and regulatory fees
12. Calculate FX conversion costs if applicable
13. Calculate estimated tax impact if enabled
14. Sum total estimated costs
15. Calculate expected net PnL
16. Calculate expected net return percentage
17. Calculate break-even price movement
18. Calculate minimum required move after costs
19. Mark output actionable or non-actionable based on profile completeness and
    mode

## Break-Even Design

v4.1 must support:

- break-even exit price
- break-even percentage move
- minimum target price after costs
- minimum risk/reward threshold after costs
- track-specific rounding placeholder
- track-specific tick-size placeholder

Design rules:

- break-even must include fee, tax, FX, and regulatory costs where enabled
- break-even must be computed in a track-aware way
- break-even output should explain whether tax and FX costs were fully modeled,
  excluded, or report-only placeholders

## Trade Eligibility Implications

This section is design-only.

Future trade eligibility should be able to block or downgrade trades when:

- expected net profit is less than or equal to zero
- expected net return is below a minimum threshold
- break-even move is too large
- FX data is missing or stale
- fee or tax profile is missing
- track is ambiguous
- provider capability contradicts market assumptions
- output is non-actionable because profiles are placeholder-only or
  needs-evidence

Design rules:

- non-actionable report-only outputs may inform analysis, but must not approve
  trade eligibility
- live or production eligibility must remain disabled

## Validation Rules

v4.1 validation must include:

- `StrategyTrack` is required
- resolved `MarketProfile` is required
- `FeeTaxProfile` is required
- `CurrencyProfile` is required
- `FXCostProfile` is required for non-KRW or cross-currency reporting
- missing track must fail closed
- missing market profile must fail closed
- incomplete fee or tax profile must fail closed for actionable outputs
- stale or missing FX must fail closed for overseas trades
- placeholder fee or tax profiles may be allowed by default only in
  `REPORT_ONLY` mode
- `REPORT_ONLY` outputs must be clearly marked non-actionable estimates
- `REPORT_ONLY` outputs must not produce trade eligibility approval
- `ACTIVE` profiles may be used for normal net-profit estimation
- `PLACEHOLDER` or `NEEDS_EVIDENCE` profiles must not drive actionable
  profitability or trade eligibility decisions
- future `SIMULATION_ONLY` what-if mode may be documented as an explicit opt-in
  extension, but it must remain non-actionable and must not be the default
- live or production eligibility must remain disabled

## CLI Design Proposal

Suggested CLI commands:

- `market-profit-profile-validate --fixture-file ...`
- `market-profit-estimate --fixture-file ...`
- `market-profit-compare-tracks --fixture-file ... [--output-file ...]`
- `market-profit-break-even --fixture-file ...`

Expected CLI behavior:

- local JSON fixture only
- deterministic JSON output
- explicit report-only or actionable status surfaced in output
- clear block reasons when data is incomplete or stale

## Fixture Design

v4.1 should define local JSON fixture examples for:

- domestic KR trade estimate
- overseas US trade estimate
- missing track failure
- stale FX failure
- placeholder tax profile in report-only mode
- net-profit-positive case
- net-profit-blocked case

Suggested fixture sections:

- strategy track
- resolved market profile
- fee/tax profile
- currency profile
- FX cost profile if required
- trade inputs:
  - entry price
  - exit price or target price
  - quantity
  - reporting currency
  - tax estimate mode
- expected validation mode
- expected output status

## System Smoke Design

System smoke must use temporary local JSON fixtures only.

Expected smoke indicators:

- `market_profit_fixture_run=true`
- `strategy_track_required=true`
- `market_profile_resolved=true`
- `broker_api_called=false`
- `credentials_accessed=false`
- `external_network_calls=false`
- `orders_created=false`
- `live_or_prod_used=false`

Smoke must confirm that no broker, account, credential, network, or execution
path is touched.

## Suggested Future Implementation Boundary

Allowed for future v4.1 implementation:

- local schema implementation
- local fixture loaders
- deterministic fee, tax, FX, and break-even estimators
- advisory-only profitability reports
- non-actionable report-only outputs for placeholder profiles

Forbidden for future v4.1 implementation:

- realtime FX fetches
- broker API calls
- account access
- credential or token access
- order submission
- `OrderIntent` creation
- order draft creation
- execution approval
- LIVE or PROD activation
- hardcoded final legal or tax conclusions

## Safety Invariants

v4.1 must preserve these invariants:

- no broker API calls
- no account access
- no credentials or tokens
- no realtime FX fetches
- no realtime market data fetches
- no order submission
- no `OrderIntent`
- no order draft
- no execution approval
- no LIVE
- no PROD
- no production policy change
- no silent market-assumption inference without track resolution
- no placeholder fee or tax profiles used as actionable approval inputs by
  default

## Summary

v4.1 should introduce a track-aware fee, tax, FX, and net-profit estimation
layer that consumes a resolved `MarketProfile` after explicit
`StrategyTrack` routing.

The design must make net profitability, break-even movement, and future
eligibility logic depend on post-cost estimates instead of gross return alone.

`ACTIVE` profiles may support normal net-profit estimation. `PLACEHOLDER` and
`NEEDS_EVIDENCE` profiles may be allowed by default only in `REPORT_ONLY`
mode, where outputs remain clearly non-actionable and cannot approve trades or
live behavior.
