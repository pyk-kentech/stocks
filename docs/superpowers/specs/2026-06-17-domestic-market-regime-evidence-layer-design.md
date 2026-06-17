# v4.11 Domestic Market Regime Evidence Layer Design

## Scope

v4.11 designs an offline deterministic market-regime evidence layer for the
domestic Korean equity track.

This milestone is design-only.

It does not implement runtime code, does not fetch realtime or historical
market data, does not call Kiwoom APIs or broker APIs, does not access
accounts, credentials, tokens, WebSocket feeds, FX feeds, or order paths, does
not create buy/sell/entry/exit signals, does not create `OrderIntent`, order
drafts, or execution approvals, does not use `LIVE` or `PROD`, does not call
cloud LLMs or local model runtimes, does not train ML models, and does not
execute prompt packs or prompt stubs.

v4.11 remains:

- local fixture-only
- offline
- deterministic
- domestic-track only
- evidence and classification only
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
- `v4.9.0-domestic-shadow-review-advisory-context-pack` -> `ffba7c1`
- `v4.10.0-local-llm-training-only-distillation-dataset-pack` -> `c860b08`
- `v3.12.0-offline-prompt-pack-advisory-task-suite` -> `656c7ea`

v4.11 must preserve:

- v4.0 track-first routing and `DOMESTIC_KR` separation
- v4.1 report-only and non-actionable profitability safety
- v4.2 stale-data fail-closed posture
- v4.3 non-executable scanner semantics
- v4.4 candidate-evaluation blocked/report-only/non-actionable semantics
- v4.5 replay provenance and window traceability
- v4.6 pack-level calibration and promotion-gate safety
- v4.7 paper-shadow non-executable journaling
- v4.8 outcome labels as observation labels, not trade results
- v4.9 advisory-context packaging safety boundaries
- v4.10 non-executable distillation dataset safety boundaries
- v3.12 advisory-only prompt-pack safety boundaries

## Design Goal

v4.11 should define a local fixture-only market-regime evidence layer that
classifies domestic Korean market context from fixture evidence such as index
movement, sector breadth, liquidity, volatility, turnover, and risk-off
conditions.

This milestone must remain evidence-only and classification-only. It must not
produce trade signals, trading approvals, order-like intent, or runtime advice.

## Architecture Position

v4.11 sits after v4.10 and before any future regime-aware scoring, calibration,
or advisory conditioning work.

Required flow:

- `StrategyTrack`
- `MarketProfile`
- `MarketRegimeFixture`
- `MarketRegimeEvidenceSnapshot`
- `MarketRegimeClassification`
- `MarketRegimeReport`
- `RegimeAwareContextReference`

Interpretation:

- v4.11 is separate from per-candidate scanner and evaluation logic because it
  describes top-down market context rather than symbol-level trade opportunity
- v4.11 produces market evidence and market classification only
- v4.11 does not create buy/sell/entry/exit signals
- v4.11 may later be referenced by v4.4, v4.5, v4.6, v4.8, v4.9, and v4.10
  without changing their current implementations

## Architecture Rules

The following rules are mandatory:

- `StrategyTrack` is a top-level mandatory input
- only `DOMESTIC_KR` is allowed
- `OVERSEAS_US` must fail validation
- missing or unresolved `MarketProfile` must fail closed
- market regime evidence must come from explicit local JSON fixtures only
- the regime layer must not fetch real index, sector, breadth, volume, FX,
  rate, or news data
- the regime layer must not create buy/sell/entry/exit signals
- the regime layer must not create orders, `OrderIntent`, order drafts,
  execution approval, `LIVE`, or `PROD` behavior
- the regime layer must not call cloud LLMs or local model runtimes

## Fixed Two-Stage Regime Model

v4.11 uses a fixed two-stage deterministic regime model.

### Stage 1

Stage 1 evaluates safety, sufficiency, and report-only conditions first.

This stage decides whether the evidence snapshot is:

- fail-closed
- insufficient-data
- report-only
- eligible for normal regime classification

Rules:

- missing critical evidence fails closed
- stale critical evidence fails closed by default
- `REGIME_REPORT_ONLY` is not the default fallback for stale core evidence
- `REGIME_REPORT_ONLY` is allowed only for explicitly declared non-actionable
  reporting contexts and only when the stale condition is limited to auxiliary
  metadata or non-critical reporting context
- `REGIME_INSUFFICIENT_DATA` is allowed only when the snapshot remains safe but
  lacks enough fixture evidence to classify a normal market regime

### Stage 2

Only snapshots that pass Stage 1 proceed to deterministic regime
classification.

Stage 2 applies threshold-based local rules to:

- index trend
- breadth strength
- sector momentum or rotation
- volatility spike
- liquidity thinness
- risk-on or risk-off state

Rules:

- no ML model training
- no LLM classification
- no external data fetch
- thresholds come from local config or fixture values only

## Core Schemas

v4.11 should define these design-level schemas:

- `MarketRegimeConfig`
- `MarketRegimeInputSet`
- `MarketRegimeFixture`
- `MarketRegimeEvidenceSnapshot`
- `IndexRegimeEvidence`
- `SectorRegimeEvidence`
- `BreadthRegimeEvidence`
- `LiquidityRegimeEvidence`
- `VolatilityRegimeEvidence`
- `RiskRegimeEvidence`
- `MarketRegimeClassification`
- `MarketRegimeReport`
- `MarketRegimeGapReport`
- `MarketRegimeSafetyBoundary`
- `RegimeAwareContextReference`

All schemas must remain:

- local
- JSON fixture-driven
- deterministic
- track-aware
- non-executable

## MarketRegimeConfig

Recommended fields:

- config id
- strategy track
- market profile id
- explicit regime-classification opt-in flag
- stale evidence policy
- report-only eligibility mode
- threshold profile id
- evidence sufficiency mode
- wording validation mode
- non-executable enforcement mode

Rules:

- config requires `DOMESTIC_KR`
- config must not imply signal generation or trade approval
- config must not include execution permissions

## MarketRegimeInputSet

Recommended fields:

- input set id
- strategy track
- market profile summary
- observation window metadata
- index evidence
- sector evidence
- breadth evidence
- liquidity evidence
- volatility evidence
- risk evidence
- data quality flags
- stale markers
- explicit report-only marker
- source trace references

Rules:

- inputs are fixture-only
- missing regime fixture fails closed
- missing market profile fails closed
- stale core evidence fails closed by default

## MarketRegimeFixture

Recommended fields:

- schema version
- fixture id
- created at
- market regime config
- market regime input set

Rules:

- fixture requires `DOMESTIC_KR`
- fixture must resolve `MarketProfile` to domestic Korean assumptions only
- fixture must not contain execution wording or unsafe trigger markers

## MarketRegimeEvidenceSnapshot

The evidence snapshot is the normalized internal unit for v4.11.

It should contain:

- snapshot id
- fixture id
- strategy track
- market profile id
- normalized observation window
- normalized evidence buckets
- data quality flags
- stale summary
- missing evidence summary
- non-executable marker

Rules:

- one fixture yields one normalized evidence snapshot
- snapshot must preserve source references and quality flags
- snapshot must not imply trade approval

## Evidence Bucket Schemas

### IndexRegimeEvidence

Recommended fields:

- index id
- close reference
- return over configured short window
- return over configured medium window
- drawdown proxy
- trend threshold references
- stale flag
- data quality flags

### SectorRegimeEvidence

Recommended fields:

- sector universe reference
- sector return distribution
- top-sector concentration
- leadership concentration bucket
- sector rotation proxy
- stale flag
- data quality flags

### BreadthRegimeEvidence

Recommended fields:

- breadth proxy value
- advancing count proxy
- declining count proxy
- breadth ratio
- breadth threshold references
- stale flag
- data quality flags

### LiquidityRegimeEvidence

Recommended fields:

- turnover proxy
- volume expansion or contraction proxy
- liquidity thinness threshold references
- stale flag
- data quality flags

### VolatilityRegimeEvidence

Recommended fields:

- volatility proxy
- volatility expansion or spike proxy
- volatility threshold references
- stale flag
- data quality flags

### RiskRegimeEvidence

Recommended fields:

- risk-off warning proxy
- stress marker count
- defensive-condition markers
- stale flag
- data quality flags

Rules for all evidence buckets:

- all evidence comes from local fixture data only
- missing critical evidence fails closed or yields
  `REGIME_INSUFFICIENT_DATA`
- stale core evidence fails closed unless the snapshot is explicitly and safely
  marked non-actionable report-only
- data quality warnings must be preserved

## Safe Regime Labels

Recommended safe, non-executable regime labels:

- `REGIME_RISK_ON`
- `REGIME_RISK_OFF`
- `REGIME_INDEX_UPTREND`
- `REGIME_INDEX_DOWNTREND`
- `REGIME_SECTOR_MOMENTUM`
- `REGIME_SECTOR_ROTATION`
- `REGIME_BREADTH_STRONG`
- `REGIME_BREADTH_WEAK`
- `REGIME_VOLATILITY_SPIKE`
- `REGIME_LIQUIDITY_THIN`
- `REGIME_CHOPPY_MARKET`
- `REGIME_INSUFFICIENT_DATA`
- `REGIME_REPORT_ONLY`

Forbidden wording examples:

- `BUY_MARKET`
- `SELL_MARKET`
- `ENTER_LONG`
- `EXIT_POSITION`
- `TRADE_APPROVED`
- any order-like or execution-like wording

Rules:

- labels describe market context only
- labels must never imply position entry, exit, or trade approval

## Classification Policy

v4.11 uses deterministic fixture-only classification rules.

Recommended rule families:

- threshold-based index trend classification
- breadth strength or weakness classification
- sector momentum or rotation classification
- volatility spike classification
- liquidity thinness classification
- risk-on or risk-off classification
- insufficient-data classification
- report-only classification

Recommended precedence:

1. safety and fail-closed checks
2. insufficient-data and report-only checks
3. dominant market-context classification
4. secondary condition preservation

## Multi-Label Regime Model

Each classification should contain:

- one `primary_regime_label`
- zero or more `secondary_regime_labels`
- one evidence-strength bucket
- blocked, report-only, and non-actionable markers

Rules:

- the primary label represents the dominant market context
- secondary labels preserve additional state such as volatility spike, weak
  breadth, sector rotation, or liquidity thinness
- no label may imply trade approval

Recommended evidence-strength buckets:

- `EVIDENCE_STRONG`
- `EVIDENCE_MODERATE`
- `EVIDENCE_WEAK`
- `EVIDENCE_INSUFFICIENT`

## MarketRegimeReport

`MarketRegimeReport` should include:

- report id
- fixture id
- strategy track
- market profile id
- evidence snapshot id
- primary regime label
- secondary regime labels
- evidence strength bucket
- blocked reasons
- data quality flags
- missing evidence summary
- stale evidence summary
- report-only marker
- non-executable marker
- source trace references

Rules:

- report is evidence-only
- report must remain non-executable
- report must not emit order-like recommendations

## MarketRegimeGapReport

Recommended gap categories:

- `MISSING_MARKET_PROFILE`
- `MISSING_REGIME_FIXTURE`
- `MISSING_INDEX_EVIDENCE`
- `MISSING_SECTOR_EVIDENCE`
- `MISSING_BREADTH_EVIDENCE`
- `MISSING_LIQUIDITY_EVIDENCE`
- `MISSING_VOLATILITY_EVIDENCE`
- `STALE_REGIME_EVIDENCE`
- `INSUFFICIENT_REGIME_EVIDENCE`
- `UNSUPPORTED_TRACK`
- `EXECUTABLE_WORDING_DETECTED`
- `UNSAFE_TRIGGER_DETECTED`

Recommended report fields:

- report id
- fixture id
- strategy track
- market profile id
- gap categories
- missing critical evidence count
- stale evidence count
- wording violation count
- unsupported-track count

## MarketRegimeSafetyBoundary

Recommended fields:

- advisory or evidence only
- non-executable only
- signal generation allowed
- order creation allowed
- order-intent creation allowed
- order-draft creation allowed
- execution approval allowed
- cloud-llm allowed
- model-runtime allowed
- live-or-prod allowed

Required values:

- evidence-only = true
- non-executable-only = true
- signal generation allowed = false
- order creation allowed = false
- order-intent creation allowed = false
- order-draft creation allowed = false
- execution approval allowed = false
- cloud-llm allowed = false
- model-runtime allowed = false
- live-or-prod allowed = false

## RegimeAwareContextReference

v4.11 uses a fixed hybrid reference model.

### Top-Level Unit

The primary unit is `one report -> one reference`.

This keeps downstream integration simple for v4.4, v4.5, v4.6, v4.8, v4.9,
and v4.10.

### Mandatory Internal References

Each top-level reference must also preserve:

- source report id
- source evidence snapshot id
- evidence-category references
- strategy track
- market profile id
- primary regime label
- secondary regime labels
- report-only marker
- stale marker
- missing-evidence marker
- non-executable marker

Rules:

- one report yields one primary context reference
- the reference must preserve traceability to the underlying snapshot and
  evidence buckets
- the reference must remain non-executable

## Integration with Previous Milestones

v4.11 may later be referenced by:

- v4.4 candidate evaluation as regime context
- v4.5 replay as regime snapshot per replay window
- v4.6 calibration as regime-aware policy comparison context
- v4.7 paper-shadow journal as market regime context at decision time
- v4.8 outcome review as regime-conditioned outcome analysis
- v4.9 advisory context bundle as regime summary context
- v4.10 distillation dataset records as regime-derived feature context

Rules:

- v4.11 designs references only
- v4.11 does not modify previous implementations in this milestone

## Fixture Design

v4.11 should define local JSON fixture examples for:

- valid market regime config
- valid risk-on regime
- valid risk-off regime
- index uptrend regime
- index downtrend regime
- sector momentum regime
- sector rotation regime
- breadth weak regime
- volatility spike regime
- liquidity thin regime
- choppy market regime
- insufficient-data regime
- report-only stale regime
- missing-track failure
- missing-market-profile failure
- missing-index-evidence failure
- missing-sector-evidence failure
- stale-evidence failure
- `OVERSEAS_US` rejection
- executable-wording detection failure
- unsafe-trigger-attempt failure

## CLI Design Proposal

Recommended CLI commands:

- `domestic-market-regime-config-validate --fixture-file ...`
- `domestic-market-regime-classify --fixture-file ... [--output-file ...]`
- `domestic-market-regime-report --fixture-file ... [--output-file ...]`
- `domestic-market-regime-gap-report --fixture-file ... [--output-file ...]`
- `domestic-market-regime-safety-report --fixture-file ... [--output-file ...]`

Expected behavior:

- `config-validate` validates fixture structure and fail-closed preconditions
- `classify` produces `MarketRegimeClassification`
- `report` produces `MarketRegimeReport`
- `gap-report` produces `MarketRegimeGapReport`
- `safety-report` confirms non-executable boundaries

## System Smoke Design

System smoke must use temporary local JSON fixtures only.

Smoke output should confirm:

- `domestic_market_regime_fixture_run=true`
- `strategy_track_required=true`
- `domestic_kr_only=true`
- `market_profile_resolved=true`
- `market_regime_evidence_consumed=true`
- `market_regime_classification_generated=true`
- `market_regime_report_generated=true`
- `market_regime_gap_report_generated=true`
- `market_regime_non_executable=true`
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

## Safety and Fail-Closed Rules

The following rules are mandatory:

- missing `StrategyTrack` fails
- non-`DOMESTIC_KR` track fails
- missing `MarketProfile` fails
- missing regime fixture fails
- missing critical evidence fails closed
- stale evidence fails closed unless explicitly safe report-only metadata rules
  apply
- executable wording fails validation
- unsafe trigger attempt fails
- regime output is always non-executable
- no regime state may trigger orders, `OrderIntent`, order drafts, execution
  approval, `LIVE`, or `PROD`
- no regime state may call cloud LLMs or local model runtimes

## Implementation Boundary for Later

Allowed for a later implementation milestone:

- local JSON fixture loader
- deterministic evidence normalization
- deterministic two-stage regime classifier
- report generator
- gap report generator
- safety report generator
- offline system smoke

Forbidden for a later implementation milestone:

- real index fetch
- real sector fetch
- real breadth fetch
- real volatility fetch
- real liquidity fetch
- realtime FX fetch
- news fetch
- Kiwoom or broker API calls
- account or credential access
- WebSocket connection
- order submission
- `OrderIntent`
- order draft creation
- execution approval
- `LIVE` or `PROD`
- cloud LLM calls
- local model runtime calls
- prompt pack or prompt stub execution
- ML training
