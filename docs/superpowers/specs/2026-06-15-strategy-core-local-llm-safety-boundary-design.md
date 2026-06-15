# v3.0 Strategy Core And Local LLM Safety Boundary Design

## Scope

v3.0 starts the strategy line with an offline, deterministic recommendation
layer. It consumes one explicitly selected local JSON fixture, creates
auditable strategy decisions, optionally records advisory-only local LLM
reviews, and may create draft OrderIntent candidates.

v3.0 does not query existing provider-pack, signal, or realtime SQLite data.
It does not call brokers, Kiwoom, account-read services, credentials, tokens,
or a network. It does not evaluate RiskGate or ExecutionGate and does not
submit or execute orders. PROD and LIVE remain blocked.

## Architecture And Dependency Boundaries

The strategy workflow is split into focused modules:

- `strategy_core.py` defines strategy models, the `StrategyEngine` protocol,
  and the deterministic baseline engine. It consumes only validated
  `StrategyFeatureSnapshot`, `StrategyCandidate`, and `StrategyConfig`
  values. It has no repository, broker, Kiwoom, account-read, credential,
  network, or order dependency.
- `strategy_fixture.py` reads exactly one explicit JSON file and validates it
  into strategy core inputs. It does not discover files, read environment
  variables, query SQLite, or read data outside the selected fixture.
- `strategy_advisor.py` defines `LocalLLMAdvisor` and the default
  `DisabledLocalLLMAdvisor`. The advisor returns advisory review records only.
  It cannot change decisions, create orders, or approve gates.
- `strategy_service.py` coordinates fixture loading, deterministic engine
  execution, optional advisory review, and SQLite audit persistence.
- `strategy_order_intent_draft.py` converts eligible persisted decisions into
  draft `OrderIntent` records without calling RiskGate, ExecutionGate, broker
  adapters, or execution services.

The existing local LLM HTTP client is not automatically connected to the
strategy workflow. v3.0 defaults to the disabled advisor and provides no CLI
option that enables network-backed LLM access.

## Explicit Fixture Contract

`strategy-run` requires `--fixture-file` and reads only that exact local JSON
file. The top-level fixture contains:

- fixture schema version
- `StrategyConfig`
- one or more `StrategyFeatureSnapshot` objects
- one or more `StrategyCandidate` objects referencing snapshot IDs

Snapshots contain normalized strategy features and provenance supplied by the
fixture. Candidates contain the proposed direction and draft-order parameters
needed for a recommendation. Strict Pydantic models reject unknown fields,
invalid enums, invalid numeric ranges, broken snapshot references, and invalid
JSON.

Structural fixture errors return a JSON-safe `FAILED` result without a
traceback. A structurally valid snapshot that lacks features required for a
decision produces an auditable `NEEDS_MORE_DATA` decision.

The fixture loader does not query provider-pack, signal, realtime, or any
other SQLite tables. A later release may add a separate DB-to-snapshot adapter
or `strategy-run-from-db` command while keeping the strategy core dependent
only on `StrategyFeatureSnapshot`.

## Strategy Models

`StrategyFeatureSnapshot` records a ticker, region, observed time, normalized
feature values, source references, and safe metadata.

`StrategyCandidate` references one snapshot and contains a proposed BUY or
SELL direction, order type, quantity or notional, optional limit and stop
prices, rationale, and safe metadata.

`StrategyDecision` records the deterministic engine result, confidence,
reasons, warnings, draft eligibility, and whether later sell-safety is
required.

Allowed `StrategyDecisionStatus` values are:

- `WATCH`
- `AVOID`
- `CANDIDATE_BUY`
- `CANDIDATE_SELL`
- `BLOCKED`
- `NEEDS_MORE_DATA`

`StrategyDecisionReason` is a normalized reason enum covering missing data,
high risk, forbidden instruments or order types, insufficient signal,
candidate eligibility, and advisory-only review boundaries.

`StrategyRun` records input checksum, engine identity, status, counts, safety
metadata, warnings, and errors. `StrategyConfig` contains only deterministic
rule thresholds and required feature names.

## Deterministic Baseline Policy

The baseline engine evaluates each candidate in a fixed order:

1. Block MARKET and forbidden margin, short, credit, leverage, options,
   futures, or fractional-share candidates.
2. Return `NEEDS_MORE_DATA` when required normalized features are absent.
3. Return `BLOCKED` for explicit hard-risk features.
4. Return `AVOID` for high-risk scores above the configured threshold.
5. Return `CANDIDATE_BUY` or `CANDIDATE_SELL` when the candidate direction and
   directional score meet configured thresholds.
6. Return `WATCH` otherwise.

For identical validated inputs and config, decision status, reasons,
confidence, and draft eligibility are identical. Generated IDs and timestamps
are audit fields and are not part of deterministic comparison.

## Local LLM Advisory Boundary

`LocalLLMAdvisor` receives only the validated fixture-derived snapshot,
candidate, and deterministic decision. It may return an advisory summary,
advisory reasons, warnings, and metadata.

The default disabled advisor:

- makes no network call
- reads no credentials, tokens, account data, databases, or extra files
- returns a disabled health result
- creates no review unless explicitly requested by the strategy service

`LocalLLMReview` is advisory and immutable. It cannot change the persisted
strategy decision, mark a decision executable, create an OrderIntent, approve
RiskGate, approve ExecutionGate, or submit an order.

## Draft OrderIntent Policy

`strategy-create-order-intent-draft` accepts a persisted strategy decision ID.
It creates an existing `OrderIntent` with status `CREATED` only when:

- the decision is `CANDIDATE_BUY` or `CANDIDATE_SELL`
- the referenced candidate and snapshot are present
- the candidate order type is LIMIT or STOP_LIMIT
- no forbidden instrument or leverage metadata is present

The command does not call `OrderIntentService.evaluate`, RiskGate,
ExecutionGate, paper execution, a broker adapter, or Kiwoom. The draft
metadata identifies the strategy run and decision and states that gate
approval is still required. SELL drafts also state that local-ledger
sell-safety is required later.

MARKET, margin, short, credit, leverage, options, futures, and fractional
shares are blocked. A blocked draft attempt returns a JSON-safe result and
does not persist an OrderIntent.

## SQLite Audit

Add the requested tables:

- `strategy_runs`
- `strategy_feature_snapshots`
- `strategy_candidates`
- `strategy_decisions`
- `local_llm_reviews`

Each table stores a unique public ID, minimal indexed lookup columns, the
strict model JSON, and an observed timestamp. Strategy inputs and outputs are
append-only audit records. Draft OrderIntents use the existing `order_intents`
table and remain in `CREATED` status until existing gates are separately run.

## CLI

Add:

- `strategy-run --db <path> --fixture-file <explicit-json>`
- `strategy-decisions --db <path> [--status ...] [--limit ...]`
- `strategy-decision-show --db <path> --decision-id <id>`
- `strategy-candidates --db <path> [--limit ...]`
- `strategy-candidate-show --db <path> --candidate-id <id>`
- `strategy-create-order-intent-draft --db <path> --decision-id <id>`
- `local-llm-health`

All commands emit JSON-safe output. List and show commands read only the new
strategy audit tables. `local-llm-health` instantiates only the disabled
advisor and reports no network, credential, account, broker, or order access.

## Safety Verification

Focused tests prove:

- fixture-only deterministic strategy runs
- strict validation and `NEEDS_MORE_DATA` handling
- no DB signal/realtime lookup
- no broker, Kiwoom, account-read, credential, token, or network dependency
  in strategy core, fixture, advisor, and service modules
- deterministic baseline decisions and high-risk blocks
- advisory-only disabled local LLM behavior
- draft-only eligible BUY and SELL conversion
- later sell-safety requirement for SELL
- MARKET and forbidden exposure blocks
- JSON-safe CLI output without secrets

System smoke adds a temporary local strategy fixture and verifies the
deterministic strategy step without external data or network access.
`external_network_calls=false` remains required.

## Documentation And Future Path

README and WORK_SUMMARY document the difference between v2.x execution safety
infrastructure and the v3.0 non-executing strategy recommendation layer.

Future releases may add:

- v3.1 backtest harness
- v3.2 signal ranking and a separate DB-to-feature-snapshot adapter
- v3.3 local LLM prompt and evaluation adapter

Live execution, PROD, direct strategy broker access, and LLM execution
approval remain blocked and require separate future safety boundaries.
