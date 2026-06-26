# v12.0 Account-Read / Portfolio Reconciliation Pipeline Design

## Goal

Build a safe, read-only account-read and portfolio reconciliation pipeline that compares:

- local paper evaluation ledger from v11
- local intended portfolio state
- local/manual/mock broker account-read snapshots
- future opt-in real account-read snapshots

v12 remains read-only. It does not submit orders, mutate accounts, cancel orders, rebalance, or open any execution path.

This milestone stays within a single `v12.0` scope. Do not split into `v12.1` or `v12.2`.

## Scope Boundary

### In scope

- Canonical read-only account snapshot modeling
- Local/manual/mock account-read fixture parsing
- Provider capability and request-preview reporting
- Blocked-by-default real account-read opt-in decision modeling
- Paper-vs-account reconciliation
- Optional target-vs-account reconciliation
- Instrument mapping and mismatch reporting
- Freshness, completeness, safety, gap, and readiness reporting
- v13 readiness and missing-prerequisite reporting

### Out of scope

- Live trading
- Order submission
- Order cancellation
- Order modification
- Account mutation
- Account transfer
- Rebalancing
- Broker paper trading
- Real account-read network execution
- Model training
- Strategy optimization
- Executable order output
- Buy/sell recommendation output
- v13 execution implementation

## Public v12 Surface

v12 uses two independent public surfaces:

- `account_read_*`
- `portfolio_reconciliation_*`

Required account-read models:

- `AccountReadProvider`
- `AccountReadMode`
- `AccountReadSourceKind`
- `AccountReadCredentialPolicy`
- `AccountReadOptIn`
- `AccountReadRequestPreview`
- `AccountReadExecutionDecision`
- `CanonicalAccountSnapshot`
- `CanonicalCashBalance`
- `CanonicalHolding`
- `CanonicalPosition`
- `CanonicalAccountValuation`
- `CanonicalAccountReadMetadata`
- `AccountReadFreshnessReport`
- `AccountReadCompletenessReport`
- `AccountReadSafetyReport`
- `AccountReadGapReport`
- `AccountReadAuditRecord`
- `AccountReadPipelineResult`

Required reconciliation models:

- `PortfolioReconciliationPlan`
- `PortfolioReconciliationInputBundle`
- `LocalPaperPortfolioSnapshotRef`
- `LocalTargetPortfolioSnapshot`
- `AccountPortfolioSnapshot`
- `InstrumentMappingRecord`
- `PositionReconciliationRecord`
- `CashReconciliationRecord`
- `PortfolioValuationReconciliationRecord`
- `PortfolioReconciliationReport`
- `PortfolioMismatchReport`
- `PortfolioReconciliationReadinessReport`
- `PortfolioReconciliationSafetyReport`
- `PortfolioReconciliationGapReport`
- `PortfolioReconciliationPipelineResult`

## Architecture

v12 splits read-only account modeling from reconciliation logic.

Module boundaries:

- `account_read_models.py`
  - account-read enums, canonical snapshot family, safety and report models
- `account_read_guard.py`
  - marker blocking, redaction enforcement, pytest network blocking, path checks
- `account_read_fixture.py`
  - local JSON-only fixture loader
- `account_read_adapter.py`
  - provider capability matrix
  - request preview
  - blocked-by-default execution decision
  - schema-ready vs schema-gap modeling
- `account_read_snapshot_engine.py`
  - canonical account snapshot assembly
  - freshness, completeness, safety, gap reports
- `portfolio_reconciliation_models.py`
  - reconciliation plan, records, mismatch, readiness, safety, gap models
- `portfolio_reconciliation_engine.py`
  - instrument mapping
  - paper-vs-account and target-vs-account reconciliation
  - mismatch classification logic
- `portfolio_reconciliation_integration_engine.py`
  - orchestration only
  - joins account-read output with v11/v10/v8/v7 context
  - assembles final reconciliation, integration, safety, gap, and v13-readiness outputs

`portfolio_reconciliation_integration_engine.py` must not contain primary account canonicalization or primary reconciliation calculation logic.

## Input Policy

### Allowed account-read inputs

- local manual account snapshot fixture
- local mocked account-read response fixture
- local redacted account-read capture fixture
- future opt-in real account-read preview input only when exact official API evidence exists

### Forbidden account-read inputs

- order API
- orderable quantity mutation or checks that imply execution readiness
- broker write endpoints
- account transfer
- margin change
- credit order paths
- real order id creation
- live execution payloads
- raw credential
- raw token
- env reads in tests
- provider or network calls in tests

## Provider / API Evidence Policy

Do not invent Kiwoom, LS, or broker account-read schemas.

If exact official account-read API evidence exists in the repo or local evidence docs, represent provider/API readiness as:

- `SCHEMA_READY_READONLY`
- `MOCKED_ADAPTER_READY`
- `OPT_IN_REAL_READONLY_BOUNDARY`

If exact evidence is missing:

- `SCHEMA_GAP`
- `PROVIDER_SETUP_REQUIRED`
- `MANUAL_FIXTURE_ONLY`

Hard rule:

- v12 tests never call real Kiwoom, LS, broker, provider, or network
- v12 tests never read real env vars or credentials
- real account-read remains explicit opt-in and blocked by default

## Real Account-Read Boundary Policy

v12 implements:

- request preview
- allowlist and opt-in gate
- execution decision

v12 does not implement:

- actual real account-read network execution

Any future real account-read boundary requires all of:

- `allow_real_account_read = true`
- `acknowledge_readonly_only = true`
- `acknowledge_no_orders = true`
- `acknowledge_no_account_mutation = true`
- `acknowledge_user_initiated = true`
- exact allowlisted read-only API id
- safe domain enum
- explicit token-provider config
- non-pytest runtime
- request scan passes
- response redaction policy passes
- no order or mutation markers appear
- no raw token/API key/credential printed or persisted

If any condition is missing:

- block account-read
- make no network call
- emit account-read safety and gap reports

## Canonical Account Snapshot

`CanonicalAccountSnapshot` includes:

- `snapshot_id`
- `provider`
- `account_ref`
- `account_ref_hash`
- `captured_at`
- `observed_at`
- `available_at`
- `currency`
- cash balances
- holdings
- positions
- valuation summary
- source refs
- freshness status
- completeness status
- redaction status
- `non_executable=true`
- `report_only=true`

`CanonicalHolding` and `CanonicalPosition` include:

- `instrument_id`
- `provider_symbol`
- `market`
- `currency`
- `quantity`
- `available_quantity` when safely read-only
- `average_cost` when safely read-only
- `last_price` when available
- `market_value`
- `unrealized_pnl` when available
- `source_ref`
- `observed_at`
- `available_at`
- quality flags
- `non_executable=true`

Must never include:

- raw account number
- raw credential
- token
- authorization header
- executable order object
- order route
- mutation endpoint payload

## Account Reference Policy

`account_ref` is fixture-configurable.

Default:

- redacted text plus hash

Stricter fixture mode:

- hash only

Raw account numbers must never appear in canonical outputs, CLI outputs, persisted reports, or tests.

## Core Data Flow

1. Provider capability and preview stage
   - classify provider readiness
   - build request preview if evidence exists
   - build blocked-by-default execution decision

2. Canonical account snapshot stage
   - parse local/manual/mock account-read input
   - normalize into canonical cash, holding, position, valuation structures
   - apply redaction and freshness/completeness checks

3. Local portfolio reference stage
   - normalize v11 paper portfolio state
   - optionally normalize local target portfolio state

4. Instrument mapping stage
   - link v8 instrument id, provider symbol, account symbol, and paper symbol
   - reject guessed matches when ambiguous

5. Reconciliation stage
   - mandatory `paper vs account`
   - optional `target vs account`
   - classify position, cash, valuation, mapping, stale, and completeness differences

6. Readiness and integration stage
   - v11 continuity
   - v10/v8 mapping continuity
   - v7.10 scale comparison
   - v7.13 non-executable rehearsal compatibility
   - v13 readiness and missing-prerequisite reporting

## Reconciliation Logic

Mandatory view:

- `paper vs account`

Optional view:

- `target vs account`

Reconciliation dimensions:

- instrument mapping
- position existence
- quantity difference
- average cost difference
- market value difference
- cash difference
- currency mismatch
- stale price or account read
- account holding exists but paper portfolio missing
- paper portfolio exists but account holding missing
- account snapshot incomplete
- unmapped symbol
- blocked or redacted account field

Allowed outputs:

- `match`
- `mismatch`
- `stale`
- `missing_in_account`
- `missing_in_paper`
- `unmapped_instrument`
- `cash_mismatch`
- `valuation_mismatch`
- `quantity_mismatch`
- `data_gap`
- `account_read_gap`
- `rejected`

No reconciliation output may:

- suggest placing orders
- say buy now or sell now
- generate order intent
- create executable instructions

## Instrument Mapping

Mapping dimensions:

- v8 domestic instrument id
- provider symbol
- broker or account holding symbol
- local paper ledger symbol

Mapping statuses:

- `MAPPED`
- `UNMAPPED`
- `AMBIGUOUS`
- `MARKET_MISMATCH`
- `CURRENCY_MISMATCH`
- `DATA_GAP`

Rules:

- no guessed mapping if ambiguous
- ambiguous mapping must not reconcile as matched
- preserve market and currency identity

## Average Cost Policy

If `average_cost` is unavailable in the account snapshot:

- skip average cost comparison
- keep quantity, presence, cash, and valuation reconciliation active
- emit `DATA_GAP` or completeness gap for average cost
- do not infer average cost from market value or quantity

## Freshness and Completeness

Required account-read snapshot timing:

- `observed_at`
- `available_at`
- `captured_at`
- `source_ref`

If missing:

- emit `DATA_GAP`
- or `STALE`
- or `RESEARCH_ONLY`
- or `REJECTED`
  depending on severity

Freshness report covers:

- snapshot age
- stale threshold
- stale holdings
- stale cash
- stale valuation
- incomplete fields
- redacted fields

## Integration Reports

### v11 integration

- compare paper ledger and portfolio with account snapshot
- report divergence
- no account mutation path

### v10 integration

- connect account snapshot instruments to dataset instrument ids
- report mappability

### v8 integration

- use domestic instrument mapping and market/currency metadata

### v7.10 integration

- compare simulated sizing assumptions with actual holding scale
- report-only only

### v7.13 integration

- confirm controlled mock dry-run remains non-executable
- no live execution path

### v13 readiness

Produce a readiness and gap report only. Do not implement execution.

Missing requirement examples:

- account-read freshness
- reconciliation match quality
- instrument mapping confidence
- order safety gate
- kill switch
- duplicate order guard
- broker execution adapter evidence
- manual approval gate

## v13 Readiness Policy

v13 readiness is tiered:

- `NOT_READY`
- `PARTIAL`
- `READY_FOR_MANUAL_REVIEW`

Interpretation:

- `NOT_READY`
  - key freshness, mapping, reconciliation, or safety requirements missing
- `PARTIAL`
  - some evidence is present, but execution prerequisites remain incomplete
- `READY_FOR_MANUAL_REVIEW`
  - sufficient reconciliation and safety evidence for human review, but still no automatic execution path

## CLI Surface

Add:

- `account-read-provider-capability-report`
- `account-read-request-preview-report`
- `account-read-fixture-parse-report`
- `account-read-snapshot-report`
- `account-read-freshness-report`
- `account-read-completeness-report`
- `account-read-safety-report`
- `account-read-gap-report`
- `portfolio-reconciliation-plan-report`
- `portfolio-reconciliation-report`
- `portfolio-mismatch-report`
- `portfolio-reconciliation-readiness-report`
- `portfolio-reconciliation-integration-report`
- `portfolio-reconciliation-safety-report`
- `portfolio-reconciliation-gap-report`

CLI behavior:

- default local fixture and mock mode
- no real account-read by default
- no real provider or network path in tests
- no env/credential/API-key/token reads in tests
- output redacted JSON
- no order or account mutation commands
- no executable order output

## Safety Guard

Block:

- order API ids
- order endpoints
- order payloads
- cancel or modify order paths
- account mutation paths
- raw account numbers
- raw tokens
- raw API keys
- app keys and secret keys
- authorization headers
- credential file paths
- env read attempts
- broker order ids
- executable order objects
- live or prod markers in unsafe context
- WebSocket use
- provider or network call attempts in pytest
- unsafe path traversal
- non-redacted account snapshots
- reconciliation wording that suggests placing orders
- machine outputs containing `BUY_NOW`, `SELL_NOW`, `PLACE_ORDER`, or `EXECUTE_ORDER`

## Status Enums

Account-read statuses:

- `ACCOUNT_READ_READY`
- `ACCOUNT_READ_PREVIEW_READY`
- `ACCOUNT_READ_FIXTURE_READY`
- `ACCOUNT_READ_SNAPSHOT_READY`
- `ACCOUNT_READ_BLOCKED_DEFAULT`
- `ACCOUNT_READ_OPT_IN_REQUIRED`
- `ACCOUNT_READ_SCHEMA_GAP`
- `ACCOUNT_READ_PROVIDER_SETUP_REQUIRED`
- `ACCOUNT_READ_STALE`
- `ACCOUNT_READ_INCOMPLETE`

Reconciliation and safety statuses:

- `PORTFOLIO_RECONCILIATION_READY`
- `PORTFOLIO_MATCH`
- `PORTFOLIO_MISMATCH`
- `POSITION_MISMATCH`
- `CASH_MISMATCH`
- `VALUATION_MISMATCH`
- `INSTRUMENT_MAPPING_READY`
- `INSTRUMENT_MAPPING_GAP`
- `DATA_GAP`
- `STALE`
- `BLOCKED_ACCOUNT_MUTATION`
- `BLOCKED_ORDER_API`
- `BLOCKED_CREDENTIAL_POLICY`
- `BLOCKED_NETWORK_IN_TEST`
- `BLOCKED_EXECUTABLE_OUTPUT`
- `RESEARCH_ONLY`
- `REJECTED`

## System Smoke

Extend `system_smoke.py` with offline v12 checks for:

- account-read local fixture parse
- redacted canonical account snapshot
- paper-vs-account reconciliation
- instrument mapping report
- freshness and completeness reports
- safety and gap reports
- no provider, network, env, account-mutation, or order actions
- no executable output

## Files

Create or modify:

- `docs/superpowers/plans/2026-06-18-v12-account-read-portfolio-reconciliation-pipeline.md`
- `src/stock_risk_mcp/account_read_models.py`
- `src/stock_risk_mcp/account_read_guard.py`
- `src/stock_risk_mcp/account_read_fixture.py`
- `src/stock_risk_mcp/account_read_adapter.py`
- `src/stock_risk_mcp/account_read_snapshot_engine.py`
- `src/stock_risk_mcp/portfolio_reconciliation_models.py`
- `src/stock_risk_mcp/portfolio_reconciliation_engine.py`
- `src/stock_risk_mcp/portfolio_reconciliation_integration_engine.py`
- `src/stock_risk_mcp/cli.py`
- `src/stock_risk_mcp/system_smoke.py`
- `tests/test_account_read_models.py`
- `tests/test_account_read_guard.py`
- `tests/test_account_read_adapter.py`
- `tests/test_account_read_snapshot_engine.py`
- `tests/test_portfolio_reconciliation_engine.py`
- `tests/test_portfolio_reconciliation_integration_cli.py`
- `tests/test_system_smoke.py`

## Testing

Use only local fixtures and mocked account-read adapters.

Focused tests must cover:

- canonical account snapshot models
- cash, holding, position, reconciliation, and status models
- redaction defaults
- raw account number blocking or redaction
- order API and mutation marker blocking
- executable output blocking
- provider/network/env blocking in pytest
- unsafe path blocking
- local fixture parse to canonical account snapshot
- mocked adapter schema-ready vs schema-gap behavior
- stale snapshot freshness reporting
- incomplete holdings completeness gaps
- matched and mismatched reconciliation cases
- unmapped and ambiguous instrument mapping
- no order recommendation wording
- v11 paper portfolio integration
- v10/v8 mapping integration
- v7.10 scale comparison
- v13 readiness and gap reporting
- CLI outputs
- system smoke offline coverage

## Verification

Run:

```bash
python3.11 -m pytest \
  tests/test_account_read_models.py \
  tests/test_account_read_guard.py \
  tests/test_account_read_adapter.py \
  tests/test_account_read_snapshot_engine.py \
  tests/test_portfolio_reconciliation_engine.py \
  tests/test_portfolio_reconciliation_integration_cli.py \
  tests/test_system_smoke.py \
  -q

python3.11 -m pytest tests/test_system_smoke.py -q

python3.11 -m pytest -q
```

If all pass:

```bash
git add \
  docs/superpowers/plans/2026-06-18-v12-account-read-portfolio-reconciliation-pipeline.md \
  src/stock_risk_mcp/account_read_models.py \
  src/stock_risk_mcp/account_read_guard.py \
  src/stock_risk_mcp/account_read_fixture.py \
  src/stock_risk_mcp/account_read_adapter.py \
  src/stock_risk_mcp/account_read_snapshot_engine.py \
  src/stock_risk_mcp/portfolio_reconciliation_models.py \
  src/stock_risk_mcp/portfolio_reconciliation_engine.py \
  src/stock_risk_mcp/portfolio_reconciliation_integration_engine.py \
  src/stock_risk_mcp/cli.py \
  src/stock_risk_mcp/system_smoke.py \
  tests/test_account_read_models.py \
  tests/test_account_read_guard.py \
  tests/test_account_read_adapter.py \
  tests/test_account_read_snapshot_engine.py \
  tests/test_portfolio_reconciliation_engine.py \
  tests/test_portfolio_reconciliation_integration_cli.py \
  tests/test_system_smoke.py

git commit -m "Implement account read portfolio reconciliation pipeline"
git tag v12.0.0-account-read-portfolio-reconciliation-pipeline
```

## Hard Invariants

- No live trading
- No real order
- No order submission
- No order cancellation
- No order modification
- No account mutation
- No account transfer
- No broker write APIs for reconciliation
- No executable order output
- No buy/sell recommendation output
- No broker paper trading API
- No provider/network calls in tests
- No env/credential/API-key/token reads in tests
- No raw account number output
- No raw authorization header output
- No WebSocket
- No v13 execution implementation

## Implementation Notes

- Reuse existing v11 portfolio and v10/v8 canonical data only as input references.
- Keep public models, CLI surfaces, safety contracts, and reports under `account_read_*` and `portfolio_reconciliation_*`.
- v12 ends at read-only account modeling, reconciliation evidence, and v13 readiness gaps.
