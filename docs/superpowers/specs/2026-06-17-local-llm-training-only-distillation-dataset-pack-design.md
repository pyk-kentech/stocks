# v4.10 Local LLM Training-Only Distillation Dataset Pack Design

## Scope

v4.10 designs an offline deterministic training-only and distillation-only
dataset-pack layer for domestic shadow review advisory context bundles.

This milestone is design-only.

It does not implement runtime code, does not train an LLM, does not call a
local model runtime, does not call a cloud LLM, does not execute prompt packs,
does not execute prompt stubs, does not generate trade recommendations, does
not create runtime advisory decisions, does not call Kiwoom APIs or broker
APIs, does not access accounts, credentials, tokens, WebSocket feeds,
realtime feeds, FX feeds, or order paths, and does not create `OrderIntent`,
order drafts, execution approvals, `LIVE`, or `PROD` behavior.

v4.10 remains:

- local fixture-only
- offline
- deterministic
- domestic-track only
- training-only dataset packaging only
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
- `v3.12.0-offline-prompt-pack-advisory-task-suite` -> `656c7ea`

v4.10 must preserve:

- v4.0 track-first routing and `DOMESTIC_KR` separation
- v4.1 report-only and non-actionable profitability safety
- v4.2 domestic realtime quality and stale-data fail-closed behavior
- v4.3 scanner-state non-executable semantics
- v4.4 candidate-evaluation blocked/report-only/non-actionable semantics
- v4.5 replay provenance and scenario/window traceability
- v4.6 promotion-gate evidence as supporting context only
- v4.7 non-executable paper-shadow journal semantics
- v4.8 outcome labels as observation labels, not trade results
- v4.9 training-only advisory-context packaging and no-runtime guarantees
- v3.12 advisory-only prompt-pack safety boundaries

## Design Goal

v4.10 should define a local fixture-only dataset-pack layer that converts v4.9
`ShadowReviewAdvisoryContextBundle` objects into training-only and
distillation-only dataset records.

This milestone must not run LLM inference or LLM training. It only defines how
future local LLM or small ML models may consume safe, non-executable, audited
context records for offline learning.

## Architecture Position

v4.10 sits after v4.9 advisory-context bundle generation.

Required flow:

- `ShadowReviewAdvisoryContextBundle`
- `TrainingOnlyDistillationPolicy`
- `DistillationDatasetRecord`
- `DistillationDatasetPack`
- `DistillationDatasetValidationReport`
- `DistillationDatasetGapReport`

Interpretation:

- v4.9 remains responsible for advisory-context bundle generation
- v4.10 consumes validated, non-executable v4.9 bundles only
- v4.10 transforms bundle-level and sub-summary-level evidence into dataset
  records
- v4.10 prepares training-only and distillation-only records only
- v4.10 does not train, infer, or execute any model
- v4.10 does not produce trade decisions

## Architecture Rules

The following rules are mandatory:

- `StrategyTrack` is a top-level mandatory input
- only `DOMESTIC_KR` is allowed
- `OVERSEAS_US` must fail validation
- missing or unresolved `MarketProfile` must fail closed
- v4.9 context bundles must remain non-executable
- v4.8 outcome labels must remain observation labels, not trade results
- v4.7 paper-shadow decisions must remain non-executable journal entries
- dataset records must not contain executable trade instructions
- dataset records must not be used as runtime advice in v4.10
- dataset packs must not call LLMs or local model runtimes
- dataset packs must not create orders, `OrderIntent`, order drafts, execution
  approval, `LIVE`, or `PROD` behavior

## Fixed Hybrid Record Unit Model

v4.10 uses a fixed hybrid dataset-record model.

### Primary Record Unit

The primary `DistillationDatasetRecord` unit should be sub-summary level.

Primary record generation should come from:

- scenario family sub-summaries
- replay window sub-summaries
- observation horizon sub-summaries

This keeps training samples granular enough for future local distillation or
small-model supervision, while preserving source traceability back to the v4.9
bundle.

Rules:

- sub-summary records are the primary dataset unit
- each record must preserve source bundle id and source trace references
- records must remain non-executable

### Optional Aggregate Record

v4.10 may additionally include an optional bundle-level aggregate record.

This record preserves the review-wide distribution and pack-level context
without replacing sub-summary records.

Rules:

- aggregate records are secondary
- aggregate records must not replace sub-summary records
- aggregate records remain training-only and non-executable

## Fixed Primary and Auxiliary Label Model

Each `DistillationDatasetRecord` uses:

- one `primary_label`
- zero or more `auxiliary_labels`

This supports both simple downstream classification and richer context tagging.

Example:

- primary: `LABEL_FAVORABLE_OBSERVATION`
- auxiliary: `LABEL_REPORT_ONLY_CONTEXT`
- auxiliary: `LABEL_BLOCKED_PROFITABILITY_CONTEXT`
- auxiliary: `LABEL_INSUFFICIENT_CONTEXT`

Rules:

- the primary label represents the dominant observation or context class
- auxiliary labels preserve blocked/report-only/non-actionable nuance
- all labels must remain non-trade, non-execution, and non-actionable

## Core Schemas

v4.10 should define these design-level schemas:

- `TrainingOnlyDistillationConfig`
- `TrainingOnlyDistillationInputSet`
- `TrainingOnlyDistillationPolicy`
- `DistillationDatasetRecord`
- `DistillationDatasetPack`
- `DistillationLabelSet`
- `DistillationFeatureSet`
- `DistillationPromptStub`
- `DistillationDatasetValidationReport`
- `DistillationDatasetGapReport`
- `DistillationDatasetSafetyBoundary`

All schemas must remain:

- local
- JSON fixture-driven
- deterministic
- track-aware
- training-only
- non-executable

## TrainingOnlyDistillationConfig

Recommended fields:

- config id
- strategy track
- market profile id
- explicit training-only opt-in flag
- record unit mode
- aggregate-record inclusion mode
- label mode
- prompt stub inclusion mode
- split metadata mode
- leakage prevention mode

Rules:

- config requires `DOMESTIC_KR`
- config must mark training-only explicitly
- config must not imply runtime advice, inference, or training execution

## TrainingOnlyDistillationInputSet

The input layer should include:

- source advisory context bundle id
- source outcome review report id
- source paper-shadow journal id
- source promotion gate id
- strategy track
- market profile id
- supported advisory task names
- scenario family coverage
- symbol coverage
- observation horizon coverage
- outcome label summary
- blocked/report-only/non-actionable summary
- risk summary
- data quality summary
- training-only marker
- non-executable marker

Rules:

- inputs are fixture-only
- missing advisory context bundle fails closed
- missing training-only marker fails closed
- missing non-executable marker fails closed
- missing market profile fails closed
- non-domestic track fails closed

## TrainingOnlyDistillationPolicy

Recommended fields:

- policy id
- primary record source modes
- aggregate record enable flag
- allowed primary labels
- allowed auxiliary labels
- forbidden label patterns
- prompt stub safety wording requirements
- feature completeness thresholds
- label distribution thresholds
- leakage policy markers

Rules:

- policy must be deterministic
- policy must reject unsafe labels and unsafe prompt text
- policy must preserve training-only and non-executable boundaries

## DistillationDatasetRecord

Each `DistillationDatasetRecord` should include:

- record id
- dataset pack id
- source bundle id
- source evidence item ids
- strategy track
- market profile id
- scenario family
- symbol if available
- observation horizon
- structured feature fields
- safe label fields
- optional short deterministic context summary
- source trace references
- `training_only=true`
- `runtime_decision_allowed=false`
- `llm_runtime_allowed=false`
- `cloud_llm_called=false`
- `local_model_runtime_called=false`
- `non_executable=true`
- `no_trade_instruction=true`

Rules:

- records must remain inert dataset entries
- records must not imply runtime advisory execution
- records must not contain executable wording

## DistillationLabelSet

v4.10 should define safe training labels such as:

- `LABEL_FAVORABLE_OBSERVATION`
- `LABEL_ADVERSE_OBSERVATION`
- `LABEL_NEUTRAL_OBSERVATION`
- `LABEL_INCONCLUSIVE_OBSERVATION`
- `LABEL_REPORT_ONLY_CONTEXT`
- `LABEL_BLOCKED_QUALITY_CONTEXT`
- `LABEL_BLOCKED_PROFITABILITY_CONTEXT`
- `LABEL_BLOCKED_TECHNICAL_EVIDENCE_CONTEXT`
- `LABEL_BLOCKED_RISK_CONTEXT`
- `LABEL_BLOCKED_SAFETY_CONTEXT`
- `LABEL_INSUFFICIENT_CONTEXT`

Important rules:

- do not use labels such as `BUY`, `SELL`, `ENTRY`, `EXIT`, `ORDER`,
  `TRADE_SUCCESS`, `PROFIT_TRADE`, `LOSS_TRADE`, `EXECUTION_RESULT`, or
  `APPROVED_ENTRY`
- labels must describe training context or observation outcomes, not trades

Recommended label structure:

- `primary_label`
- `auxiliary_labels`
- `label_source_summary`

## DistillationFeatureSet

v4.10 should define safe distillation feature groups such as:

- outcome count features
- favorable/adverse/neutral/inconclusive ratios
- blocked reason counts
- report-only counts
- non-actionable counts
- scenario family coverage features
- symbol coverage features
- observation horizon coverage features
- risk summary features
- data quality features
- market profile reference features
- profitability context reference features
- technical evidence context reference features

Rules:

- features must be derived from fixture data only
- features must not require LLM inference
- features must not require external market data
- features must not imply trade approval

## DistillationPromptStub

v4.10 may define optional `DistillationPromptStub` objects for future local LLM
training only.

Rules:

- prompt stubs are inert dataset text templates
- prompt stubs must not be executed in v4.10
- prompt stubs must not ask the model to recommend trades
- prompt stubs must not ask for buy/sell/entry/exit advice
- prompt stubs may ask for classification of non-executable context, risk
  reasons, or observation label explanation
- prompt stubs must include explicit safety wording:
  - `This is training-only context.`
  - `Do not provide trade instructions.`
  - `Do not output buy/sell/order/execution advice.`

## DistillationDatasetPack

`DistillationDatasetPack` should include:

- dataset pack id
- fixture id
- source bundle ids
- record count
- label distribution
- scenario coverage
- symbol coverage
- observation horizon coverage
- blocked/report-only/non-actionable distribution
- training-only marker
- non-executable marker
- split policy metadata if applicable
- leakage prevention metadata
- validation report id
- gap report id

Rules:

- pack is the top-level dataset export artifact
- pack must remain training-only and non-executable
- pack must not imply model execution readiness

## Split and Leakage Policy

v4.10 should design deterministic local policies for:

- train/validation/test split metadata
- time-window separation
- scenario-family separation
- symbol separation option
- no future leakage marker
- source trace preservation
- dataset versioning
- deterministic hash/id generation

Important rules:

- v4.10 should design split metadata and validation rules only
- v4.10 should not train a model

## Validation Report Design

v4.10 should define validation checks:

- track compatibility check
- market profile check
- source bundle presence check
- training-only marker check
- non-executable marker check
- no executable wording check
- no unsafe labels check
- no order-like artifact check
- no LLM runtime check
- no prompt execution check
- label distribution check
- feature completeness check
- coverage sufficiency check
- leakage policy check
- gap report check

Recommended validation report fields:

- validation report id
- dataset pack id
- strategy track
- market profile id
- valid flag
- training-only marker present flag
- non-executable marker present flag
- feature completeness result
- label distribution result
- leakage policy result
- warnings
- block reasons

## Gap Report Design

v4.10 should define gap categories:

- `MISSING_ADVISORY_CONTEXT_BUNDLE`
- `MISSING_TRAINING_ONLY_MARKER`
- `MISSING_NON_EXECUTABLE_MARKER`
- `MISSING_MARKET_PROFILE`
- `INSUFFICIENT_LABEL_DISTRIBUTION`
- `INSUFFICIENT_SCENARIO_COVERAGE`
- `INSUFFICIENT_SYMBOL_COVERAGE`
- `INSUFFICIENT_OBSERVATION_HORIZON_COVERAGE`
- `EXECUTABLE_WORDING_DETECTED`
- `UNSAFE_LABEL_DETECTED`
- `PROMPT_EXECUTION_NOT_ALLOWED`
- `LLM_RUNTIME_NOT_ALLOWED`
- `LOCAL_MODEL_RUNTIME_NOT_ALLOWED`
- `ORDER_ARTIFACT_DETECTED`
- `POTENTIAL_LEAKAGE_DETECTED`
- `UNSUPPORTED_TRACK`

Recommended gap report fields:

- gap report id
- dataset pack id
- gap categories
- missing source counts
- insufficient coverage counts
- unsafe label counts
- prompt execution violation counts
- leakage warning counts

Rules:

- gap reporting is diagnostic only
- gap reporting must not imply model execution or training execution

## Safety and Fail-Closed Rules

The design must enforce:

- missing `StrategyTrack` fails
- non-`DOMESTIC_KR` track fails
- missing `MarketProfile` fails
- missing advisory context bundle fails
- missing training-only marker fails
- missing non-executable marker fails
- executable wording fails
- unsafe label fails
- prompt execution attempt fails
- LLM runtime marker enabled fails
- local model runtime marker enabled fails
- unsafe trigger attempt fails
- dataset output is always non-executable
- no dataset state may trigger orders, `OrderIntent`, order drafts,
  execution approval, `LIVE`, or `PROD`

## DistillationDatasetSafetyBoundary

Recommended fields:

- training only marker
- runtime decision allowed marker
- llm runtime allowed marker
- cloud LLM called marker
- local model runtime called marker
- prompt stubs executed marker
- order creation allowed marker
- order intent allowed marker
- order draft allowed marker
- execution approval allowed marker
- live/prod allowed marker

Rules:

- all safety markers should remain explicit
- any violation should fail closed

## Advisory and ML Downstream Compatibility

v4.10 should design how future milestones may consume dataset-pack outputs:

- future local LLM labeling or distillation training may consume dataset packs
- future small ML scorers may consume structured features
- future advisory prompt packs may consume only validated non-executable
  summaries
- v4.10 itself must not train or infer
- v4.10 itself must not produce trading advice

## CLI Design Proposal

CLI commands should remain consistent with existing repo style:

- `domestic-distillation-dataset-config-validate --fixture-file ...`
- `domestic-distillation-dataset-build --fixture-file ... [--output-file ...]`
- `domestic-distillation-dataset-validate --fixture-file ... [--output-file ...]`
- `domestic-distillation-dataset-gap-report --fixture-file ... [--output-file ...]`
- `domestic-distillation-dataset-safety-report --fixture-file ... [--output-file ...]`

## Fixture Design

v4.10 should design local JSON fixture examples for:

- valid distillation dataset config
- valid advisory context bundle input
- valid dataset record
- valid dataset pack
- valid prompt stub as inert training-only template
- insufficient label distribution
- insufficient scenario coverage
- insufficient symbol coverage
- insufficient observation horizon coverage
- missing advisory context bundle failure
- missing training-only marker failure
- missing non-executable marker failure
- executable wording detection failure
- unsafe label detection failure
- prompt execution attempt failure
- forbidden LLM runtime marker failure
- forbidden local model runtime marker failure
- missing track failure
- `OVERSEAS_US` rejection
- unsafe trigger attempt failure

## System Smoke Design

System smoke must use temporary local JSON fixtures only.

Smoke output should confirm:

- `domestic_distillation_dataset_fixture_run=true`
- `strategy_track_required=true`
- `domestic_kr_only=true`
- `market_profile_resolved=true`
- `advisory_context_bundle_consumed=true`
- `distillation_dataset_records_generated=true`
- `distillation_dataset_pack_generated=true`
- `distillation_dataset_validation_generated=true`
- `distillation_dataset_gap_report_generated=true`
- `training_only_dataset_marker_present=true`
- `distillation_dataset_non_executable=true`
- `prompt_stubs_not_executed=true`
- `llm_runtime_allowed=false`
- `local_model_runtime_allowed=false`
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

If implemented later, v4.10 may add:

- strict local fixture loaders
- deterministic dataset record generation
- deterministic pack generation
- deterministic validation reporting
- deterministic gap reporting
- deterministic prompt stub packaging

v4.10 must still not add:

- LLM training execution
- local model runtime calls
- cloud LLM calls
- prompt execution
- trading advice generation
- order artifacts
- Kiwoom or broker connectivity
- realtime or FX network access
