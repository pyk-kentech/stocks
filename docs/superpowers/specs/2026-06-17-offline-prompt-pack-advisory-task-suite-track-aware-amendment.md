# v3.12 Offline Prompt Pack / Advisory Task Suite Track-Aware Amendment

## Purpose

This amendment updates the existing v3.12 offline prompt pack design so it can
coexist safely with the completed v4.0 and v4.1 foundations:

- `v4.0.0-domestic-overseas-strategy-track-separation` -> `d6d430d`
- `v4.1.0-market-profile-fee-tax-fx-net-profit-calculator` -> `3df8289`

The original v3.12 design remains valid as a general offline prompt pack
governance layer. However, if a v3.12 prompt pack is used for trading-related
or market-advisory tasks, it must become explicitly `StrategyTrack` and
`MarketProfile` aware.

This amendment is design-only. It does not implement runtime code.

## Review Outcome

An amendment is required.

The existing v3.12 design focuses on:

- prompt pack structure
- language and domain coverage
- safety trap coverage
- deterministic fixture references
- advisory boundary refusal

Those controls are necessary, but they are no longer sufficient for
trading-related advisory tasks after v4.0 and v4.1.

The original design does not explicitly require:

- `StrategyTrack`
- resolved `MarketProfile`
- `FeeTaxProfile`
- `CurrencyProfile`
- `FXCostProfile`
- `NetProfitEstimate`
- `TrackAwareProfitabilityCheck`

Without those requirements, a future v3.12 implementation could validate a
prompt pack that still silently mixes domestic and overseas assumptions or
produces advisory text from placeholder or non-actionable profitability data.

## Amendment Scope

This amendment applies only to trading-related or market-advisory prompt tasks.

Examples:

- trade plan risk explanation
- net-profit explanation
- profitability challenge
- missing-data explanation for trading context
- advisory refusal when cost or market context is incomplete

This amendment does not force every generic prompt pack task to depend on
v4.1. Purely generic summarization tasks may remain market-context-independent
if they are explicitly declared non-trading and non-profitability-aware.

## 1. StrategyTrack Requirement

Trading-related or market-advisory prompt tasks must require explicit
`StrategyTrack`.

Rules:

- `StrategyTrack` must be declared in the prompt task context
- supported tracks must be declared explicitly per prompt pack or per task
- missing `StrategyTrack` must fail closed
- ambiguous track must fail closed
- prompt tasks must not infer track from ticker format, language, exchange
  nickname, or user text alone

Supported tracks in current scope:

- `DOMESTIC_KR`
- `OVERSEAS_US`

## 2. MarketProfile Requirement

Trading-related or market-advisory prompt tasks must consume a resolved
`MarketProfile`.

Rules:

- prompt tasks must accept resolved market context, not infer it
- missing `MarketProfile` must fail closed
- prompt tasks must not infer fee, tax, FX, session, settlement, or provider
  assumptions from ticker format or freeform text alone
- prompt tasks must treat `StrategyTrack -> MarketProfile resolution` as a
  required upstream dependency

Required context for track-aware advisory tasks should include at minimum:

- `StrategyTrack`
- `MarketProfile`
- provider capability summary
- advisory context status

## 3. Net-Profit Awareness

Trading-related or market-advisory prompt tasks must distinguish:

- gross return
- estimated net return
- report-only estimate
- non-actionable estimate

If v4.1 context is present, prompt tasks must consume the distinction between:

- `TradeCostEstimate`
- `NetProfitEstimate`
- `BreakEvenMoveEstimate`
- `TrackAwareProfitabilityCheck`

Rules:

- advisory output must not approve a trade when v4.1 marks the result
  non-actionable
- advisory output must not present gross return as sufficient if net-profit
  context exists and says otherwise
- advisory output must explicitly preserve report-only or non-actionable status
- prompt tasks must not erase block reasons from `TrackAwareProfitabilityCheck`

## 4. Domestic / Overseas Separation

`DOMESTIC_KR` and `OVERSEAS_US` prompt tasks must not silently share:

- fee assumptions
- tax assumptions
- FX assumptions
- session assumptions
- settlement assumptions
- realtime-data assumptions
- provider capability assumptions

Shared prompt templates are allowed only if they receive explicit resolved
track-aware context and do not invent market assumptions internally.

## 5. Prompt Pack Validation Rules

For trading-related or market-advisory prompt packs, validation must be
expanded to require:

- declared supported tracks
- declared context requirements
- declared whether net-profit context is required
- declared whether report-only mode is supported
- declared whether the task is non-trading generic or trading-context-aware

Recommended additional prompt task metadata:

- `supported_tracks`
- `requires_market_profile`
- `requires_profitability_context`
- `supports_report_only_mode`
- `task_context_class`

Suggested `task_context_class` values:

- `GENERIC_NON_TRADING`
- `TRACK_AWARE_ADVISORY`
- `TRACK_AWARE_PROFITABILITY_ADVISORY`

Validation must fail closed when:

- a trading-related task omits supported tracks
- a trading-related task omits required market context
- profitability-aware tasks omit net-profit context requirements
- required market context is missing from the referenced fixture
- report-only compatibility is required but not declared

## 6. Advisory Safety Rules

The original v3.12 safety rules remain in force. They must be strengthened for
track-aware advisory tasks.

Still forbidden:

- `OrderIntent` creation
- order draft creation
- execution approval
- LIVE path
- PROD path
- broker access
- account access
- credential access
- network access

Additional rule:

- no actionable recommendation may be based only on placeholder,
  needs-evidence, report-only, or otherwise non-actionable market-profit
  context

If cost or profitability context is incomplete, stale, placeholder-only, or
explicitly non-actionable, the advisory task must preserve that state and fail
closed into explanation or refusal mode.

## 7. Profitability Context Handling

When profitability context is available from v4.1, trading-related prompt tasks
should consume:

- `FeeTaxProfile`
- `CurrencyProfile`
- `FXCostProfile`
- `TradeCostEstimate`
- `NetProfitEstimate`
- `BreakEvenMoveEstimate`
- `TrackAwareProfitabilityCheck`

Rules:

- `ACTIVE` cost profiles may support normal explanatory net-profit discussion
- `PLACEHOLDER` or `NEEDS_EVIDENCE` profiles defaulting to `REPORT_ONLY` must
  remain non-actionable in prompt output
- prompt output must not convert report-only estimates into approval language
- prompt output must not present placeholder fee or tax assumptions as final
  legal or tax truth

## 8. Fixture Implications

Prompt pack fixture references for trading-related tasks should be able to
point to local context fixtures that include:

- `StrategyTrack`
- resolved `MarketProfile`
- optional `TrackAwareProfitabilityCheck`
- explicit context completeness markers

Trading-related prompt tasks should fail validation if their declared context
requirements are absent from the referenced fixture family.

## 9. Readiness And Coverage Implications

The existing v3.12 readiness logic should be amended so that a prompt pack
cannot be considered ready for benchmark feed usage in trading-advisory
contexts unless:

- track coverage is declared explicitly
- market-context-aware tasks are validated against required inputs
- report-only handling is explicitly covered
- non-actionable profitability handling is explicitly covered
- domestic and overseas separation traps are represented

Recommended additional trap categories:

- `TRACK_MISSING_FAIL_CLOSED`
- `TRACK_AMBIGUITY_FAIL_CLOSED`
- `MARKET_PROFILE_REQUIRED`
- `REPORT_ONLY_PROFITABILITY_REFUSAL`
- `NON_ACTIONABLE_ESTIMATE_PRESERVATION`
- `DOMESTIC_OVERSEAS_ASSUMPTION_MIX_TRAP`

## 10. Amendment To Existing v3.12 Interpretation

The original v3.12 design remains correct for generic offline prompt pack
validation.

This amendment adds one critical interpretation rule:

- if a prompt pack task is trading-related or market-advisory, it must be
  treated as track-aware and market-context-aware

Therefore:

- v3.12 is not discarded
- v3.12 does not become globally dependent on v4.1
- but trading-related v3.12 prompt tasks must integrate with the v4.0/v4.1
  context model before implementation

## Summary

An amendment is needed before v3.12 implementation.

The existing v3.12 design is strong on prompt-pack structure and advisory
safety, but it is missing explicit requirements for `StrategyTrack`,
`MarketProfile`, and non-actionable profitability context.

Before implementing trading-related prompt packs, v3.12 must be amended so
that:

- missing or ambiguous track fails closed
- resolved market profile is required
- domestic and overseas assumptions never mix silently
- report-only or non-actionable profitability context never becomes actionable
  advisory output
