# Kiwoom Sandbox/Mock Execution Adapter Design

## Purpose

v2.12 proves a Kiwoom-shaped execution boundary using local deterministic
fixtures only. It consumes execution-approved order intents through a dedicated
service and persists both generic broker audits and Kiwoom mock-specific audits.

It does not use official Kiwoom API IDs or paths, OAuth, credentials, account
data, real network calls, or live orders.

## Architecture

```text
OrderIntent
-> RiskGate
-> ExecutionGate
-> KiwoomMockExecutionService
-> KiwoomMockExecutionAdapter
-> FakeKiwoomExecutionTransport
-> SQLite audit records
```

`KiwoomMockExecutionService` is the only entry point for submission. It builds a
generic `BrokerOrderRequest` from an approved intent, persists every attempt,
checks duplicate submissions, and invokes the adapter only when all gates pass.
Strategies never receive the adapter directly.

## Internal Endpoint Contract

Only these local deterministic pairs exist:

```text
KIWOOM_MOCK_ORDER_SUBMIT /kiwoom-mock/order/submit
KIWOOM_MOCK_ORDER_CANCEL /kiwoom-mock/order/cancel
KIWOOM_MOCK_ORDER_STATUS /kiwoom-mock/order/status
```

They are fixture identifiers, not official Kiwoom endpoint mappings. Official
endpoint verification is deferred to v2.13.

## Models And Persistence

Existing `BrokerOrderRequest`, `BrokerOrderReceipt`, and broker health records
remain the generic audit contract. New `KiwoomMockOrderRequest` and
`KiwoomMockOrderReceipt` rows preserve Kiwoom mock request/receipt linkage and
deterministic mock order identifiers.

New append-only tables:

- `kiwoom_mock_order_requests`
- `kiwoom_mock_order_receipts`

## Execution Behavior

- Only `BrokerId.KIWOOM` in `BrokerEnvironment.LOCAL_MOCK` is supported.
- Only KR-region intents are supported.
- LIMIT and STOP_LIMIT fill at explicit positive `mock_fill_price` when given,
  otherwise at `limit_price`.
- STOP_LIMIT does not simulate a stop trigger.
- MARKET requires an explicit positive `mock_fill_price`.
- Invalid ticker, quantity, price, region, expired intent, or missing gate
  approval produces a persisted rejection.
- Duplicate submission persists a new generic and Kiwoom mock request plus a
  rejected receipt, and does not call the adapter fill path.
- Cancel and status lookup are deterministic local operations.

## Safety Boundary

The adapter and transport import no HTTP/Kiwoom/Windows SDK, read no secrets or
environment variables, and expose no account, balance, position, holdings,
cash, fill-query, or live-order capability. `external_network_calls=false`
remains mandatory.

## CLI

Add:

- `kiwoom-mock-execution-health`
- `kiwoom-mock-submit-order`
- `kiwoom-mock-cancel-order`
- `kiwoom-mock-order-status`
- `kiwoom-mock-order-requests-list`
- `kiwoom-mock-order-receipts-list`

Normal rejections return JSON without traceback.

## Future Work

- v2.13: official Kiwoom endpoint verification
- v2.14: real-network sandbox adapter, explicitly opt-in
- v2.15: live adapter with explicit kill switch and default-off execution
