# Broker Mock Adapter Boundary Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Design a strictly mock-only, paper-only, disabled-by-default broker mock adapter boundary that can later translate internal `HistoricalPaperOrderIntent` outputs into future broker mock or paper API requests without enabling any real order, real account mutation, live trading, production execution, credential loading, network call, Kiwoom API call, LS API call, or broker API call in v6.0.

**Architecture:** Keep the v5.10 internal simulator as the sole producer of internal paper decisions and internal `HistoricalPaperOrderIntent` objects, then define a separate `BrokerMock*` boundary layer that is explicitly incompatible with real order, real account, and real execution surfaces. Future Kiwoom mock and LS mock adapters sit behind this boundary as deferred adapters only, while safety guards, gap taxonomy, CLI design, and smoke coverage all fail closed unless an explicit mock-only opt-in is provided in a later implementation milestone.

**Tech Stack:** Python 3.11, Pydantic v2, existing strict model/guard/report patterns, local fixture-only inputs, pure-Python boundary validation, pytest, system smoke

---

## 1. Why Internal Simulator And Broker Mock API Must Be Separated

The v5.10 simulator is intentionally self-contained. It owns paper decisions, paper fills, paper ledger updates, and paper-only performance reporting with no external adapter boundary. That isolation is what currently prevents accidental drift toward broker semantics.

v6.0 should preserve that property by keeping two distinct layers:

- internal paper simulation objects
- external-facing broker mock boundary objects

This separation is required for four reasons:

1. Internal paper simulation uses deterministic local assumptions, while a future broker mock adapter may need request/response semantics, capability discovery, mock account snapshots, mock execution reports, and mock rejection codes.
2. Internal `HistoricalPaperOrderIntent` is a simulator artifact and must never become structurally compatible with any real `OrderIntent` or production execution payload.
3. Broker mock APIs tend to resemble real broker APIs. Without a hard boundary, mock-only experiments can accidentally normalize field names, account metadata, credential hooks, or execution flows that are unsafe to carry upstream.
4. Future Kiwoom mock and LS mock adapters will have provider-specific quirks. Those differences should be absorbed by dedicated `BrokerMock*` translation surfaces, not by contaminating the internal simulator domain model.

Design rule:

- `HistoricalPaperOrderIntent` remains internal and simulated.
- `BrokerMockOrderIntent` is a separate boundary object.
- No direct reuse of real order, account, or execution schemas is allowed.

## 2. Adapter Boundary Architecture

Planned conceptual flow:

1. `HistoricalPaperTradingRun` produces internal `HistoricalPaperOrderIntent`.
2. A future boundary translator validates mock-only opt-in and safety flags.
3. The translator emits `BrokerMockOrderIntent`.
4. A future broker mock adapter converts that intent into `BrokerMockOrderRequest`.
5. A future mock adapter returns `BrokerMockOrderResponse`, `BrokerMockExecutionReport`, and optional `BrokerMockAccountSnapshot`.
6. Results are recorded only as mock-only, paper-only, non-production artifacts.

The adapter boundary should be modeled as three strict zones:

- **Zone A: Internal Simulator Domain**
  - `HistoricalPaperOrderIntent`
  - `PaperLedger`
  - `PaperPosition`
  - `PaperTrade`
- **Zone B: Mock Boundary Translation Layer**
  - `BrokerMockAdapterConfig`
  - `BrokerMockCapability`
  - `BrokerMockOrderIntent`
  - `BrokerMockAdapterSafetyReport`
  - `BrokerMockAdapterGapReport`
  - `BrokerMockAdapterAuditRecord`
- **Zone C: Future Provider-Specific Mock Adapters**
  - `KiwoomMockAdapterBoundary`
  - `LSMockAdapterBoundary`

Safety rule:

- Zone A must be usable without Zone B.
- Zone B must remain disabled by default.
- Zone C must not exist as executable code in v6.0.

## 3. Broker Mock Capability Model

`BrokerMockCapability` should describe what a future mock adapter claims to support without performing any call.

Suggested capability areas:

- supported markets
- supported asset types
- supported paper order types
- supported mock time-in-force values
- support for mock order submission
- support for mock cancellation
- support for mock status polling
- support for mock account snapshots
- support for mock position snapshots
- support for deterministic replay mode
- support for asynchronous callback simulation

Each capability declaration must also carry safety assertions:

- mock-only
- paper-only
- disabled-by-default
- explicit opt-in required
- no-real-order
- no-real-account-mutation
- no-live-trading
- no-network-call in v6.0

Unsupported or ambiguous capabilities must fail closed and generate explicit gaps instead of silently downgrading behavior.

## 4. Broker Mock Order Intent Schema

`BrokerMockOrderIntent` is the boundary-safe translation target for internal paper intents.

Required fields:

- mock order intent id
- source paper order intent id
- source paper decision id
- source signal candidate id
- symbol
- market
- side
- mock order type
- requested quantity or notional
- requested paper limit or reference price if applicable
- session timestamp
- strategy track
- market profile
- mock adapter target id
- mock-only safety flags
- audit lineage ids

Required exclusions:

- no real `OrderIntent`
- no real account id
- no real broker account number
- no credential token
- no exchange session secret
- no production routing key
- no real broker order id
- no live execution approval field

Compatibility rule:

- Translation from `HistoricalPaperOrderIntent` to `BrokerMockOrderIntent` must be one-way and explicit.
- No implicit cast or shared base class with real order surfaces is allowed.

## 5. Broker Mock Execution Report Schema

`BrokerMockExecutionReport` should represent mock execution outcomes only.

Required fields:

- mock execution report id
- source mock order intent id
- source mock order request id
- mock order response id
- symbol
- side
- mock status
- mock filled quantity
- mock average fill price
- mock fee estimate
- mock slippage estimate
- mock execution timestamp
- mock rejection code or reason if any
- mock-only safety flags
- lineage and audit ids

Allowed statuses:

- `MOCK_ACCEPTED`
- `MOCK_REJECTED`
- `MOCK_PARTIAL_FILL`
- `MOCK_FILLED`
- `MOCK_CANCELLED`
- `MOCK_EXPIRED`

Hard boundary:

- no real broker execution id
- no production exchange execution reference
- no settlement integration
- no cash movement trigger
- no custody mutation trigger

## 6. Broker Mock Account Snapshot Schema

`BrokerMockAccountSnapshot` and `BrokerMockPositionSnapshot` should exist only as mock boundary surfaces, separate from internal paper ledger and separate from any real account model.

Suggested account snapshot fields:

- mock account snapshot id
- mock adapter id
- snapshot timestamp
- base currency
- reported mock cash
- reported mock buying power
- reported mock equity
- reported mock unrealized P/L
- reported mock realized P/L
- mock position snapshot ids
- mock-only safety flags

Suggested position snapshot fields:

- mock position snapshot id
- symbol
- market
- quantity
- average price
- mark price
- unrealized P/L
- realized P/L
- exposure value
- source mock account snapshot id

Boundary rule:

- `BrokerMockAccountSnapshot` must never be treated as a real account state.
- It must never backfill or overwrite the internal `PaperLedger`.
- Reconciliation between internal paper ledger and future mock account snapshots should be report-only and gap-driven.

## 7. Kiwoom Mock API Future Adapter Boundary

`KiwoomMockAdapterBoundary` is future-only in v6.0.

This section should define only the contract shape:

- expected adapter identity
- capability declaration shape
- translation requirements from `BrokerMockOrderIntent`
- expected mock response and mock execution report mapping
- expected mock account snapshot mapping
- fail-closed handling for unsupported order fields, unsupported market codes, and unsupported session states

Hard v6.0 rule:

- no Kiwoom API call
- no Kiwoom credential loading
- no Kiwoom session bootstrap
- no mock transport implementation
- no endpoint constants or request signing logic

The plan should treat Kiwoom-specific behavior as a future adapter implementation target behind the generic boundary.

## 8. LS Mock API Future Adapter Boundary

`LSMockAdapterBoundary` is also future-only in v6.0.

Planned contract shape mirrors the Kiwoom mock boundary:

- adapter identity
- declared capabilities
- translation rules from `BrokerMockOrderIntent`
- mapping rules into `BrokerMockOrderResponse`
- mapping rules into `BrokerMockExecutionReport`
- mapping rules into `BrokerMockAccountSnapshot`
- fail-closed behavior for unsupported LS mock features

Hard v6.0 rule:

- no LS API call
- no LS credential loading
- no LS transport
- no LS session handling
- no endpoint implementation

## 9. Credential And Environment Boundary

v6.0 must design an environment boundary that explicitly blocks credential and runtime integration.

Rules:

- no credential loading in v6.0
- no token loading
- no secret manager integration
- no `.env` dependency
- no broker account number loading
- no sandbox login handshake
- no network configuration bootstrap

Future opt-in design, for later versions only:

- adapters may eventually require mock credentials or mock account identifiers
- any future credential access must live behind a dedicated adapter config boundary
- internal simulator modules must remain unaware of credentials
- default state remains disabled

Recommended config stance:

- `BrokerMockAdapterConfig` should require explicit `enabled=false` by default
- future adapter selection should be absent or `NONE` by default
- any future mock credential path should be defined conceptually but forbidden in v6.0 runtime

## 10. Safety Guard Design

`BrokerMockAdapterSafetyReport` and the future guard should reject or block:

- real order fields
- real account mutation fields
- real broker metadata
- live trading markers
- LIVE/PROD markers
- credential, token, or secret fields
- network call markers
- Kiwoom API markers
- LS API markers
- generic broker API markers
- order API markers
- account API markers
- provider API markers
- cloud LLM metadata
- local LLM runtime metadata
- parquet source or export markers

Required safety flags:

- `mock_only=true`
- `paper_only=true`
- `disabled_by_default=true`
- `explicit_opt_in_required=true`
- `non_executable_by_default=true`
- `no_real_order=true`
- `no_real_account_mutation=true`
- `no_live_trading=true`
- `no_live_prod=true`
- `no_production_broker=true`
- `no_credentials_loaded=true`
- `no_network_call=true`
- `no_kiwoom_api_call=true`
- `no_ls_api_call=true`
- `no_broker_api_call=true`
- `no_order_api_call=true`
- `no_account_api_call=true`
- `no_provider_api_call=true`
- `no_cloud_llm=true`
- `no_local_llm_runtime=true`

The guard should be fail-closed:

- if adapter enablement is ambiguous, block
- if intent lineage is incomplete, block
- if adapter target is missing, block
- if any execution-like field looks real, block

## 11. Gap Taxonomy

Recommended v6.0 gap categories:

- `BROKER_MOCK_BOUNDARY_DEFINED`
- `BROKER_MOCK_REPORT_ONLY`
- `BROKER_MOCK_DISABLED_BY_DEFAULT`
- `BROKER_MOCK_EXPLICIT_OPT_IN_REQUIRED`
- `BROKER_MOCK_MISSING_ADAPTER_CONFIG`
- `BROKER_MOCK_MISSING_CAPABILITY_DECLARATION`
- `BROKER_MOCK_MISSING_SOURCE_PAPER_INTENT`
- `BROKER_MOCK_MISSING_SOURCE_SIGNAL_CANDIDATE`
- `BROKER_MOCK_LINEAGE_INCOMPLETE`
- `BROKER_MOCK_UNSUPPORTED_MARKET`
- `BROKER_MOCK_UNSUPPORTED_TRACK`
- `BROKER_MOCK_UNSUPPORTED_ORDER_TYPE`
- `BROKER_MOCK_REAL_ORDER_FIELD_DETECTED`
- `BROKER_MOCK_REAL_ACCOUNT_MUTATION_DETECTED`
- `BROKER_MOCK_LIVE_TRADING_NOT_ALLOWED`
- `BROKER_MOCK_LIVE_PROD_NOT_ALLOWED`
- `BROKER_MOCK_PRODUCTION_BROKER_NOT_ALLOWED`
- `BROKER_MOCK_CREDENTIALS_NOT_ALLOWED`
- `BROKER_MOCK_NETWORK_CALL_NOT_ALLOWED`
- `BROKER_MOCK_KIWOOM_API_NOT_ALLOWED`
- `BROKER_MOCK_LS_API_NOT_ALLOWED`
- `BROKER_MOCK_BROKER_API_NOT_ALLOWED`
- `BROKER_MOCK_ORDER_API_NOT_ALLOWED`
- `BROKER_MOCK_ACCOUNT_API_NOT_ALLOWED`
- `BROKER_MOCK_PROVIDER_API_NOT_ALLOWED`
- `BROKER_MOCK_CLOUD_LLM_NOT_ALLOWED`
- `BROKER_MOCK_LOCAL_LLM_RUNTIME_NOT_ALLOWED`
- `BROKER_MOCK_PARQUET_NOT_ALLOWED`
- `BROKER_MOCK_ADAPTER_BOUNDARY_FUTURE_ONLY`

These categories should support both design review and later implementation validation.

## 12. CLI Design

v6.0 is design-only, but the later CLI should remain boundary-report oriented.

Recommended future commands:

- `historical-broker-mock-boundary-report --fixture-file ...`
- `historical-broker-mock-safety-report --fixture-file ...`
- `historical-broker-mock-gap-report --fixture-file ...`
- `historical-broker-mock-capability-report --fixture-file ...`

CLI constraints:

- local fixture file only
- no credentials
- no network
- no broker calls
- no Kiwoom calls
- no LS calls
- no order submission
- no account mutation
- no live trading path
- JSON output only at first
- parquet unsupported

CLI should initially report boundary readiness and safety posture, not execute any adapter path.

## 13. system_smoke Design

Future `system_smoke` should confirm only boundary artifacts, not real behavior.

Suggested smoke checks:

- `historical_broker_mock_boundary_fixture_run=true`
- `historical_broker_mock_boundary_report_generated=true`
- `historical_broker_mock_capability_report_generated=true`
- `historical_broker_mock_safety_report_generated=true`
- `historical_broker_mock_gap_report_generated=true`
- `historical_broker_mock_mock_only=true`
- `historical_broker_mock_paper_only=true`
- `historical_broker_mock_disabled_by_default=true`
- `historical_broker_mock_explicit_opt_in_required=true`
- `historical_broker_mock_non_executable_by_default=true`
- `historical_broker_mock_no_real_order=true`
- `historical_broker_mock_no_real_account_mutation=true`
- `historical_broker_mock_no_live_trading=true`
- `historical_broker_mock_no_live_prod=true`
- `historical_broker_mock_no_production_broker=true`
- `historical_broker_mock_no_credentials_loaded=true`
- `historical_broker_mock_no_network_call=true`
- `historical_broker_mock_no_kiwoom_api_call=true`
- `historical_broker_mock_no_ls_api_call=true`
- `historical_broker_mock_no_broker_api_call=true`
- `historical_broker_mock_no_order_api_call=true`
- `historical_broker_mock_no_account_api_call=true`
- `historical_broker_mock_no_provider_api_call=true`
- `historical_broker_mock_no_cloud_llm=true`
- `historical_broker_mock_no_local_llm_runtime=true`
- `historical_broker_mock_parquet_unsupported=true`

Global negative checks should remain false:

- `kiwoom_api_called=false`
- `ls_api_called=false`
- `broker_api_called=false`
- `account_api_called=false`
- `order_api_called=false`
- `credentials_accessed=false`
- `external_network_calls=false`

## 14. Tests

Later implementation should emphasize boundary and fail-closed behavior.

Required test groups:

- model construction tests for all `BrokerMock*` schema objects
- fixture loader tests for local JSON only
- safety guard tests for real-order, credential, network, provider, LIVE/PROD, Kiwoom, LS, broker, and parquet rejection
- translation tests from `HistoricalPaperOrderIntent` to `BrokerMockOrderIntent`
- lineage preservation tests
- disabled-by-default tests
- explicit-opt-in-required tests
- provider-specific future boundary contract tests using inert fixtures only
- CLI report-only tests
- system smoke boundary tests

No test in the first implementation phase should call any external broker mock API.

## 15. Non-Goals

Explicit non-goals for v6.0:

- no Kiwoom mock API implementation
- no LS mock API implementation
- no real broker adapter
- no credential loading
- no token loading
- no network execution
- no real account read
- no real account mutation
- no real order placement
- no real execution report
- no live order gate
- no production execution
- no live market data
- no external provider integration
- no cloud LLM
- no local LLM runtime
- no parquet support

## 16. Task-By-Task Execution Order

Recommended future implementation sequence:

1. Define `BrokerMock*` models, safety flags, and inert fixture loader.
2. Define safety guard and broker mock gap taxonomy.
3. Implement translation-only boundary engine from `HistoricalPaperOrderIntent` to `BrokerMockOrderIntent`.
4. Add report-only capability, safety, gap, and audit aggregation.
5. Add boundary-report CLI only.
6. Add focused tests.
7. Add `system_smoke` boundary checks.
8. Run targeted tests, smoke, then full pytest if feasible.
9. Commit and tag only after all report-only safety constraints pass.

Recommended first implementation milestone:

- v6.1 `Broker Mock Boundary Models And Safety Guard`

Deferred milestones:

- v6.2 translation engine and report-only CLI
- v6.3 provider-specific future boundary stubs
- v6.x any mock transport experimentation, still gated and still non-production
