## v13.0 Controlled Execution Preflight / Approval / Kill-Switch Pipeline Design

### Milestone

- Version: `v13.0`
- Final tag: `v13.0.0-controlled-execution-preflight-approval-killswitch-pipeline`
- Version discipline: do not create `v13.1`, `v13.2`, or any additional `v13.x` milestone

### Goal

Implement a conservative controlled execution system that connects prior read-only, dataset, paper-evaluation, and reconciliation layers into a strict execution preflight and approval pipeline.

v13 is not autonomous trading, not profitability optimization, not model training, not broker paper trading API, and not account mutation by default. v13 must default to blocked, must not place real orders in tests, must not call real broker/provider/network in tests, must not read real credentials/env/API keys/tokens in tests, and must not output executable live orders unless explicit runtime opt-in, manual approval, all-green readiness, kill-switch clearance, duplicate-order guard, and exact adapter evidence all pass.

### Upstream Inputs

v13 consumes:

- v12 account-read and portfolio reconciliation reports
- v11 paper evaluation reports
- v10 feature-store dataset manifests and leakage reports
- v9 macro/regime reports
- v8 Kiwoom domestic stock snapshots and read-only provider evidence
- v7.10 position sizing / risk budget context
- v7.11 event-risk context
- v7.12 outlier/leadership routing context
- v7.13 controlled mock dry-run rehearsal context
- existing order-intent / execution-gate / mock adapter boundaries from earlier versions

### Public Outputs

v13 produces:

- controlled execution readiness report
- execution preflight report
- manual approval packet
- kill-switch status report
- duplicate-order guard report
- order-intent validation report
- execution adapter capability report
- mock execution rehearsal report
- dry-run execution report
- live execution blocked/default report
- execution audit report
- execution gap report
- execution safety report

### Architecture

v13 uses a new independent `controlled_execution_*` public layer. Existing `order_intent`, execution gate, controlled mock dry-run, and mock adapter modules may be reused as internal references or compatibility inputs, but they do not define the v13 public contract.

The pipeline is split into five layers:

1. Prerequisite ingestion
   - Read v10/v11/v12/v9/v8/v7.10/v7.11/v7.12/v7.13 outputs and local execution evidence.
   - Normalize them into canonical v13 prerequisite inputs.
2. Control-plane evaluation
   - Compute readiness, preflight, risk, reconciliation, kill-switch, and duplicate-order guard through separate engines.
3. Intent and draft assembly
   - Build `ControlledExecutionIntent` and `ControlledExecutionOrderDraft` only after preflight evaluation.
   - Keep all drafts non-executable by default.
4. Approval and adapter binding
   - Bind exact draft hash, expiry, and single-use approval reference.
   - Produce adapter capability reports and blocked live-boundary previews.
5. Rehearsal, audit, and reporting
   - Support mock execution and dry-run only.
   - Emit local redacted audit records, safety reports, and gap reports.

Strict default policy:

- default mode is `BLOCKED_DEFAULT` or `READINESS_REPORT_ONLY`
- tests may use only `MOCK_EXECUTION_ONLY`, `DRY_RUN_NO_BROKER`, and `PREFLIGHT_ONLY`
- live execution remains represented only as a blocked opt-in boundary preview in v13

### Execution Modes

Represent these modes:

- `BLOCKED_DEFAULT`
- `READINESS_REPORT_ONLY`
- `PREFLIGHT_ONLY`
- `MANUAL_APPROVAL_PACKET_ONLY`
- `MOCK_EXECUTION_ONLY`
- `DRY_RUN_NO_BROKER`
- `LIVE_EXECUTION_OPT_IN_BOUNDARY`
- `REJECTED`

Default mode:

- `BLOCKED_DEFAULT` or `READINESS_REPORT_ONLY`

Test-allowed modes:

- `MOCK_EXECUTION_ONLY`
- `DRY_RUN_NO_BROKER`
- `PREFLIGHT_ONLY`

Tests must never use:

- real live execution
- real broker/provider/network
- real credentials/env/token/API key

### Data Model

Canonical public models:

- `ControlledExecutionMode`
- `ControlledExecutionProvider`
- `ControlledExecutionAdapterStatus`
- `ControlledExecutionCredentialPolicy`
- `ControlledExecutionOptIn`
- `ControlledExecutionPrerequisiteStatus`
- `ControlledExecutionReadinessReport`
- `ControlledExecutionPreflightRequest`
- `ControlledExecutionPreflightDecision`
- `ControlledExecutionIntent`
- `ControlledExecutionOrderDraft`
- `ControlledExecutionApprovalPacket`
- `ControlledExecutionManualApproval`
- `ControlledExecutionKillSwitchState`
- `ControlledExecutionDuplicateGuardState`
- `ControlledExecutionRiskCheckResult`
- `ControlledExecutionReconciliationCheckResult`
- `ControlledExecutionAdapterCapabilityReport`
- `ControlledExecutionMockExecutionResult`
- `ControlledExecutionDryRunResult`
- `ControlledExecutionAuditRecord`
- `ControlledExecutionSafetyReport`
- `ControlledExecutionGapReport`
- `ControlledExecutionPipelineResult`

Naming rules:

- prefer `OrderDraft`, `ApprovalPacket`, and `ExecutionIntent`
- do not expose a normal executable `Order` object in the public v13 surface
- any executable payload type is outside normal v13 reports and must never appear in tests

Model boundary rules:

- `ControlledExecutionIntent`
  - human-readable execution intent only
  - includes instrument id, provider symbol, market, side, reference price, quantity proposal, notional proposal, risk budget ref, source report refs, reason codes, preflight status, non-executable flag
- `ControlledExecutionOrderDraft`
  - includes draft id, instrument id, side, quantity, order type, limit price when applicable, time-in-force when applicable, idempotency key, risk checks, reconciliation checks, approval hash, adapter target enum, status
  - must remain non-executable by default
  - must not contain raw broker payload, account number, token, or authorization header
- `ControlledExecutionApprovalPacket`
  - includes exact draft hash, expiry, single-use approval reference, risk summary, reconciliation summary, kill-switch summary, duplicate summary, adapter capability summary, and non-executable redacted preview
- `ControlledExecutionManualApproval`
  - validates runtime approval reference against exact draft hash, packet hash, expiry, and single-use constraints
- `ControlledExecutionMockExecutionResult`
  - local simulated execution only
- `ControlledExecutionDryRunResult`
  - blocked or redacted broker-like preview only

Safety fields across v13 report models must enforce:

- read-only
- report-only or non-executable unless explicitly mock-execution-only or dry-run-no-broker
- no raw account number
- no raw token/API key/auth header
- no raw executable broker payload

### All-Green Preflight Gating

`ControlledExecutionPreflightDecision` uses hard-gate evaluation. All prerequisite groups must be green before any order draft can be promoted beyond blocked/report-only state.

If any prerequisite is missing, stale, unsafe, ambiguous, blocked, or rejected:

- do not create executable order
- do not call broker
- do not route order
- do not mutate account
- return blocked readiness and gap reports with explicit reason codes

Required prerequisite groups:

1. Dataset and signal prerequisites
   - v10 feature dataset manifest exists
   - v10 leakage status is not blocked
   - v11 paper evaluation report exists
   - v11 signal generation did not use labels
   - v11 fill/ledger metrics exist
   - v11 evaluation is not rejected or leakage-blocked
   - v11 performance report may be present but v13 must not optimize based on it
2. Macro and event prerequisites
   - v9 macro/regime snapshot exists
   - event-risk state exists
   - severe event block blocks or downgrades execution
   - stale macro/event data blocks execution readiness
3. Domestic snapshot prerequisites
   - v8 domestic stock snapshot exists
   - price/liquidity/rank/outlier context exists as required
   - stale quote/price blocks execution
   - unsafe liquidity/spread blocks execution
4. Risk prerequisites
   - v7.10 risk/sizing context exists
   - risk budget is explicit
   - max position size is bounded
   - stop/loss policy is explicit when applicable
   - unbounded size is forbidden
   - margin/credit remains blocked by default unless explicitly supported and still blocked by policy
5. Account and reconciliation prerequisites
   - v12 account-read snapshot exists
   - account snapshot is fresh
   - account refs are redacted
   - portfolio reconciliation report exists
   - instrument mapping is unambiguous
   - cash/position mismatch is resolved or explicitly classified
   - account-read path is read-only
   - no account mutation path exists
6. Adapter prerequisites
   - broker execution adapter evidence exists
   - exact API schema evidence exists for any live boundary
   - adapter is explicitly allowlisted
   - account/order mutation endpoints are isolated
   - mock adapter is ready
   - dry-run adapter is ready
   - live adapter is blocked by default
7. Manual approval prerequisites
   - manual approval packet can be generated
   - human approval token/reference is supplied only at runtime
   - approval expires
   - approval is single-use
   - approval binds to exact order draft hash
   - approval cannot be reused for modified order drafts
8. Kill-switch prerequisites
   - global kill-switch is not active
   - per-symbol kill-switch is not active
   - per-market kill-switch is not active
   - daily loss limit is not breached
   - max order count limit is not breached
   - max exposure limit is not breached
   - cooldown is not active
9. Duplicate-order prerequisites
   - no duplicate open intent
   - no duplicate pending order draft
   - no duplicate instrument/time/side collision
   - idempotency key exists
   - prior execution audit does not show unresolved pending state
10. Credential and network prerequisites
   - no raw token/API key/credential in reports
   - no env read in tests
   - no provider/network call in tests
   - any real live boundary requires explicit runtime opt-in
   - tests use fake token/provider/adapters only

### Approval Policy

The approval path uses local audit/history as the default runtime storage strategy, with manual fixture approval support for tests.

`ControlledExecutionApprovalPacket` includes:

- order draft summary
- exact order draft hash
- risk summary
- account/reconciliation summary
- kill-switch summary
- duplicate guard summary
- data freshness summary
- adapter capability summary
- expiry timestamp
- single-use approval reference
- non-executable preview

Approval rules:

- approval is required for any live boundary
- approval must be explicit
- approval must bind to exact draft hash
- approval expires
- approval cannot be reused
- approval cannot approve modified draft
- tests use fake approval references only

`ControlledExecutionManualApproval` validation rules:

- exact `order_draft_hash` match
- packet is not expired
- approval reference is single-use
- approval reuse is blocked
- approval for modified draft is invalid

### Kill-Switch Policy

Implement these switch types:

- global kill switch
- market kill switch
- instrument kill switch
- daily loss limit switch
- max order count switch
- max exposure switch
- event-risk switch
- stale-data switch
- cooldown switch

Kill-switch statuses:

- `CLEAR`
- `ACTIVE`
- `TRIPPED_DAILY_LOSS`
- `TRIPPED_MAX_ORDERS`
- `TRIPPED_MAX_EXPOSURE`
- `TRIPPED_EVENT_RISK`
- `TRIPPED_STALE_DATA`
- `DATA_GAP`
- `REJECTED`

If any switch is not clear:

- block execution preflight
- produce safety report
- do not emit executable order output

### Duplicate-Order Guard Policy

Implement local duplicate detection for:

- same instrument + side + time window
- same idempotency key
- unresolved pending draft
- unresolved mock execution
- same paper signal replay row
- repeated approval packet reuse
- ambiguous prior audit state

Duplicate statuses:

- `NO_DUPLICATE`
- `DUPLICATE_INTENT`
- `DUPLICATE_DRAFT`
- `DUPLICATE_IDEMPOTENCY_KEY`
- `PENDING_STATE_UNRESOLVED`
- `APPROVAL_REUSE_DETECTED`
- `DATA_GAP`
- `REJECTED`

If duplicate risk exists:

- block execution
- do not emit executable order output

### Adapter Capability

Represent these adapter targets:

- `MOCK_EXECUTION_ADAPTER`
- `DRY_RUN_ADAPTER`
- `KIWOOM_LIVE_EXECUTION_BOUNDARY`
- `LS_LIVE_EXECUTION_BOUNDARY`
- `UNKNOWN`

v13 implementation scope:

- mock execution adapter
- dry-run no-broker adapter
- live execution boundary capability report

v13 does not require real live execution to pass tests.

Live adapter policy:

- live boundary remains blocked by default
- exact official API schema evidence is required
- explicit runtime opt-in is required
- manual approval is required
- kill-switch clear is required
- duplicate guard clear is required
- account-read/reconciliation all-green is required
- tests must never invoke live adapter
- if official schema evidence is missing, report `ADAPTER_SCHEMA_GAP`

`LIVE_EXECUTION_OPT_IN_BOUNDARY` is exposed only as capability and blocked submit preview. The preview must remain non-executable.

### Mock Execution and Dry-Run

Mock execution:

- accepts only approved local order drafts
- simulates submission result
- records audit entry
- never calls broker
- never mutates account

Dry-run:

- builds redacted broker-like preview only if schema evidence exists
- no network
- no submit
- no account mutation
- no executable payload output unless explicitly marked blocked/redacted

Outputs:

- mock execution result
- dry-run preview
- audit report
- safety report

### Audit and Idempotency

Every preflight, approval check, mock execution, dry-run, duplicate check, and kill-switch evaluation must produce a local audit record.

`ControlledExecutionAuditRecord` includes:

- action id
- timestamp
- source refs
- order draft hash
- approval ref hash
- idempotency key
- mode
- decision
- reason codes
- redaction status
- non-executable
- report-only

Audit must not include:

- raw account number
- token
- API key
- authorization header
- raw executable broker payload
- credential path

Idempotency policy:

- every draft must carry an idempotency key
- unresolved pending audit state blocks new execution
- approval reuse must be detectable from audit/history

### CLI Surface

Add these commands:

- `controlled-execution-readiness-report`
- `controlled-execution-preflight-report`
- `controlled-execution-approval-packet-report`
- `controlled-execution-manual-approval-check-report`
- `controlled-execution-kill-switch-report`
- `controlled-execution-duplicate-guard-report`
- `controlled-execution-adapter-capability-report`
- `controlled-execution-mock-execution-report`
- `controlled-execution-dry-run-report`
- `controlled-execution-audit-report`
- `controlled-execution-safety-report`
- `controlled-execution-gap-report`

CLI behavior:

- default to report/preflight only
- no live execution by default
- no provider/network/env/credential/account mutation/order submit in tests
- output redacted JSON
- any command representing live submission intent must require explicit opt-in and manual approval
- v13 does not add a normal live submission CLI path

### System Smoke

System smoke uses tiny local fixtures to verify:

- v10/v11/v12 prerequisite ingestion
- all-green preflight success in mock-only path
- approval packet generation
- fake manual approval validation
- kill-switch clear path
- duplicate guard clear path
- mock execution rehearsal
- dry-run preview generation
- redacted audit generation
- no network
- no env read
- no account mutation
- no executable output

Also include at least one blocked path fixture:

- stale account snapshot, active kill-switch, or duplicate approval reuse must produce blocked readiness

### Tests

Create or modify:

- `docs/superpowers/plans/2026-06-18-v13-controlled-execution-preflight-approval-killswitch-pipeline.md`
- `src/stock_risk_mcp/controlled_execution_models.py`
- `src/stock_risk_mcp/controlled_execution_guard.py`
- `src/stock_risk_mcp/controlled_execution_fixture.py`
- `src/stock_risk_mcp/controlled_execution_preflight_engine.py`
- `src/stock_risk_mcp/controlled_execution_approval_engine.py`
- `src/stock_risk_mcp/controlled_execution_killswitch_engine.py`
- `src/stock_risk_mcp/controlled_execution_duplicate_guard.py`
- `src/stock_risk_mcp/controlled_execution_adapter.py`
- `src/stock_risk_mcp/controlled_execution_rehearsal_engine.py`
- `src/stock_risk_mcp/controlled_execution_audit_engine.py`
- `src/stock_risk_mcp/cli.py`
- `src/stock_risk_mcp/system_smoke.py`
- `tests/test_controlled_execution_models.py`
- `tests/test_controlled_execution_guard.py`
- `tests/test_controlled_execution_preflight_engine.py`
- `tests/test_controlled_execution_approval_engine.py`
- `tests/test_controlled_execution_killswitch_engine.py`
- `tests/test_controlled_execution_duplicate_guard.py`
- `tests/test_controlled_execution_adapter.py`
- `tests/test_controlled_execution_rehearsal_engine.py`
- `tests/test_controlled_execution_integration_cli.py`
- `tests/test_system_smoke.py`

Unit test coverage must include:

- model validation and redaction
- strict all-green preflight gating
- approval hash binding, expiry, single-use, and modified-draft rejection
- global/market/instrument/risk/event/stale kill-switch behavior
- duplicate guard and idempotency behavior
- adapter capability reporting
- mock execution and dry-run rehearsal
- CLI wiring
- system smoke integration

Hard test constraints:

- no real broker/provider/network call in tests
- no real credentials/env/API key/token read in tests
- no live execution in tests
- no executable payload output in tests

### Milestone Close Criteria

v13.0 closes when all of the following are true:

- new `controlled_execution_*` public surface is complete
- strict all-green readiness and preflight gating works
- approval hash, expiry, and single-use binding work
- global/market/instrument/risk/event/stale kill-switch logic works
- duplicate guard and idempotency guard work
- mock execution and dry-run rehearsal work
- local redacted audit trail works
- CLI and system smoke are wired
- focused pytest passes
- full pytest passes
- final tag is created once and only once:
  - `v13.0.0-controlled-execution-preflight-approval-killswitch-pipeline`

### Explicit Non-Goals

v13 is not:

- autonomous live trading
- strategy optimization
- model training
- paper trading profitability promise
- broker paper trading API integration
- account mutation by default
- real order placement in tests

### Implementation Notes

The implementation should follow repository patterns established by:

- `paper_evaluation_*`
- `account_read_*`
- `portfolio_reconciliation_*`
- `controlled_mock_dry_run_*`
- existing local/offline fixture, CLI, and `system_smoke` conventions

The public contract stays manifest/report oriented. Any future real execution support remains outside v13 unless a later milestone explicitly opens that scope.
