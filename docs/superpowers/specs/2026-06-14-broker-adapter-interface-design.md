# v2.10 Broker Adapter Interface Design

## Goal

Add a broker-neutral adapter boundary and deterministic local
`MockBrokerAdapter` without connecting to a real broker, reading credentials,
or making network calls.

v2.10 extends the approved v2.9 flow:

```text
OrderIntent
-> RiskGate
-> ExecutionGate
-> BrokerAdapterService
-> BrokerAdapter
-> MockBrokerAdapter only
-> SQLite audit records
```

The existing v2.9 `PaperExecutor` remains unchanged. `MockBrokerAdapter` is a
separate adapter-boundary implementation used to prove how future broker
adapters must be called after approval.

## Architecture And Isolation

Files and responsibilities:

- `broker_models.py`: broker enums and JSON-safe request/receipt/health models
- `broker_adapter.py`: broker-neutral `Protocol`
- `mock_broker_adapter.py`: deterministic, local-only adapter
- `broker_adapter_service.py`: approved-intent orchestration and audit
- `repository.py`: append-only broker audit persistence
- `cli.py`: four JSON commands

Strategies, signals, agents, and optimizers never receive a `BrokerAdapter`.
Only `BrokerAdapterService` may submit after it verifies the persisted
ExecutionGate approval.

No real broker registry or dynamic plugin loading is added in v2.10. The
service accepts only `BrokerId.MOCK` with `BrokerEnvironment.LOCAL_MOCK`.

## Models

### Enums

- `BrokerId`: `MOCK`, `KIWOOM`, `ALPACA`, `UNKNOWN`
- `BrokerEnvironment`: `LOCAL_MOCK`, `PAPER`, `SANDBOX_DISABLED`,
  `LIVE_DISABLED`
- `BrokerCapability`: `MARKET_DATA`, `ACCOUNT_READ`, `ORDER_SUBMIT`,
  `ORDER_CANCEL`, `ORDER_REPLACE`, `WEBSOCKET_MARKET_DATA`,
  `CONDITION_SEARCH`
- `BrokerConnectionStatus`: `DISCONNECTED`, `CONNECTED`, `DISABLED`, `ERROR`
- `BrokerOrderStatus`: `ACCEPTED`, `REJECTED`, `FILLED`,
  `PARTIALLY_FILLED`, `CANCELLED`, `UNKNOWN`

### BrokerOrderRequest

The request is an immutable audit snapshot derived from an approved
`OrderIntent`. It stores broker/environment routing, order fields, creation
time, and metadata.

`metadata_json` may contain `mock_fill_price` for deterministic MARKET fills.
It contains no credentials, account IDs, environment dumps, or secret values.

### BrokerOrderReceipt

Every submit or cancel outcome produces a receipt. A local deterministic fill
uses:

- `status=FILLED`
- `accepted=true`
- deterministic filled quantity/price/notional
- a local mock broker order ID

Rejected outcomes use:

- `status=REJECTED`
- `accepted=false`
- no filled values
- a clear JSON-safe message

### BrokerAdapterHealth

Health records broker/environment, connection status, capabilities, message,
and check time. Health checks are local capability checks, not network
connectivity checks.

## BrokerAdapter Protocol

```python
class BrokerAdapter(Protocol):
    broker_id: BrokerId
    environment: BrokerEnvironment

    def health_check(self) -> BrokerAdapterHealth: ...
    def capabilities(self) -> list[BrokerCapability]: ...
    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderReceipt: ...
    def cancel_order(self, broker_order_id: str) -> BrokerOrderReceipt: ...
```

Capability enums reserve future boundaries. v2.10 does not implement real
market-data, account, balance, position, websocket, or condition-search calls.

## MockBrokerAdapter

`MockBrokerAdapter` is deterministic and local only:

- `broker_id=MOCK`
- `environment=LOCAL_MOCK`
- health is `CONNECTED`
- capabilities are `ORDER_SUBMIT` and `ORDER_CANCEL`
- no `MARKET_DATA` or `ACCOUNT_READ`
- no secrets
- no network
- no live trading

Submission behavior:

- LIMIT fills at positive `limit_price`
- STOP_LIMIT fills at positive `limit_price`; it does not simulate a
  broker-native stop trigger
- MARKET rejects unless `metadata_json.mock_fill_price` is positive
- missing/non-positive quantity or deterministic fill price rejects
- cancel produces a deterministic local `CANCELLED` receipt when a broker
  order ID is supplied; it does not contact a broker

The adapter itself has no repository dependency and does not decide whether an
intent passed RiskGate or ExecutionGate.

## BrokerAdapterService

The service builds requests and controls submission. Before submission it:

1. loads the persisted `OrderIntent`
2. requires `OrderIntentStatus.EXECUTION_APPROVED`
3. loads the latest approved `ExecutionGateDecision`
4. verifies the decision belongs to the same intent
5. requires `ExecutionMode.PAPER`
6. requires `BrokerId.MOCK`
7. requires `BrokerEnvironment.LOCAL_MOCK`
8. builds and saves a new `BrokerOrderRequest`

Normal blocked/rejected outcomes produce JSON-safe service results, not CLI
tracebacks.

### Duplicate Submission Contract

Every submission attempt saves a new `BrokerOrderRequest` before duplicate
handling.

After saving the request, the service checks whether the same
`order_intent_id` already has a successful receipt. A successful receipt means
`accepted=true` with status `ACCEPTED`, `FILLED`, or `PARTIALLY_FILLED`.

When a successful receipt already exists:

- do not call `MockBrokerAdapter.submit_order`
- do not create another fill
- save a new `BrokerOrderReceipt`
- set `status=REJECTED`
- set `accepted=false`
- set message to `duplicate broker submission`
- return the rejected request/receipt as a normal outcome

Existing requests and receipts are never overwritten. Rejected receipts do
not themselves prevent a later first successful submission.

For a non-duplicate valid submission, the service calls the mock adapter and
saves its receipt.

## Persistence

Add append-only audit tables:

- `broker_order_requests`
- `broker_order_receipts`
- `broker_adapter_health_checks`

No unique constraint prevents multiple requests per intent because every
attempt must be audited.

Repository APIs:

- save/get/list broker order requests
- save/get/list broker order receipts
- save/list broker health checks
- get latest receipt for a broker order request
- list receipts for an order intent
- detect a successful receipt for an order intent

Existing SQLite databases receive the tables through idempotent schema
creation.

## CLI

Add:

- `broker-adapter-health`
- `broker-submit-mock-order`
- `broker-order-requests-list`
- `broker-order-receipts-list`

`broker-adapter-health` accepts broker/environment values but returns a
JSON-safe rejected/disabled result for any non-MOCK or non-LOCAL_MOCK
selection.

`broker-submit-mock-order` accepts an approved intent ID and optional positive
`--mock-fill-price`. Duplicate submissions return a saved REJECTED receipt
whose message contains `duplicate broker submission`.

List commands support the requested filters. All commands return JSON and
normal blocked/rejected outcomes produce no traceback.

## Safety Boundaries

- no real broker API or SDK
- no Kiwoom REST or OpenAPI+/OCX/pykiwoom
- no Alpaca, KIS, IBKR, or Polygon SDK
- no account, balance, or position API
- no external network calls
- no secret or credential reads
- no live execution
- no strategy access to adapters
- only MOCK + LOCAL_MOCK submission
- approved v2.9 ExecutionGate decision required
- v2.9 PaperExecutor remains intact
- every request, receipt, and health check is auditable

System smoke must remain `COMPLETED` with `external_network_calls=false`.

## Documentation And Future Path

README and WORK_SUMMARY will distinguish:

- v2.9 `PaperExecutor`: direct deterministic paper lifecycle
- v2.10 `MockBrokerAdapter`: broker-neutral interface-boundary proof
- future Kiwoom adapters: separate read-only, sandbox/mock, and live stages

Future path:

- v2.11 Kiwoom REST Read-only Adapter
- v2.12 Kiwoom Sandbox/Mock Execution Adapter
- v2.13 Kiwoom Live Execution Adapter with explicit kill switch

## Verification

Tests cover models, protocol conformance, mock capabilities and fills,
rejections, approval requirements, non-MOCK/environment blocks, append-only
audits, duplicate attempt auditing, CLI JSON behavior, existing v2.9/v2.8 and
provider-pack regressions, and absence of broker SDK/network/secret access.

Final verification:

```powershell
pytest -q
python -m compileall -q src
git diff --check
python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs
git status --short
```
