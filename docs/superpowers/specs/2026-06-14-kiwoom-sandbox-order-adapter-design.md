# v2.16 Kiwoom Sandbox Order Adapter Design

## Scope

v2.16 adds a separate MOCK-only Kiwoom sandbox order boundary behind the
existing OrderIntent, RiskGateDecision, and ExecutionGateDecision chain.
It does not add PROD, live trading, account reads, direct strategy broker
access, or automatic network calls in pytest/system-smoke.

## Execution Gate

Add `ExecutionMode.SANDBOX`. PAPER behavior remains unchanged. SANDBOX approval
requires an approved matching RiskGate decision, explicit
`enable_sandbox_order=True`, a KR equity LIMIT intent, positive integer
quantity, positive limit price, no margin/short/options/futures/leverage, and a
BUY stop-loss. LIVE remains blocked in every v2.16 configuration.

## Official Endpoint Boundary

The v2.13 curated manifest is the only endpoint source of truth.

- `kt10000` is the only allowed submit endpoint.
- `kt10003` is the only allowed cancel endpoint.
- Both must remain classified `ORDER`.
- READ_ONLY, ACCOUNT_READ, AUTH outside the token provider, UNKNOWN,
  WebSocket, non-exact base URLs, and PROD are blocked.

The curated manifest has no verified SELL-submit or independent order-status
endpoint. v2.16 therefore permits only BUY LIMIT real MOCK submission. SELL is
blocked with a traceable reason even if local holdings are sufficient. Status
is local audit lookup only and makes no network/account-history request.

## Components

- `kiwoom_sandbox_order_models.py`: config, run, request, receipt, status
- `kiwoom_sandbox_order_transport.py`: strict ORDER allowlist, fake transport,
  bounded real MOCK HTTP transport
- `kiwoom_sandbox_order_adapter.py`: request mapping and transport boundary
- `kiwoom_sandbox_order_service.py`: gate validation, duplicate protection,
  dry-run, submit/cancel/local status, redacted persistence

Credentials load only from explicit ENV or exact FILE_EXPLICIT after all
preflight and gate checks. Dry-run never reads credentials, requests a token,
or calls transport.

## Audit And Idempotency

Add append-only tables:

- `kiwoom_sandbox_order_runs`
- `kiwoom_sandbox_order_requests`
- `kiwoom_sandbox_order_receipts`
- `kiwoom_sandbox_order_status_checks`

Every submit derives `client_order_id` from the approved intent unless
explicitly supplied. A duplicate is rejected and audited before transport.
Submit never retries. Cancel is limited to three known sandbox order IDs per
run and does not retry. Status is limited to three known IDs and reads local
audits only.

Audits store only redacted metadata and `account_loaded: true/false`. They
never store credentials, account number, authorization, token, raw request
body, raw response body, or credential path.

## CLI

Add separate commands:

- `kiwoom-sandbox-order-health`
- `kiwoom-sandbox-order-plan`
- `kiwoom-sandbox-order-submit`
- `kiwoom-sandbox-order-cancel`
- `kiwoom-sandbox-order-status`
- `kiwoom-sandbox-order-requests`
- `kiwoom-sandbox-order-receipts`
- `kiwoom-sandbox-order-show`

Health and plan are offline. Submit/cancel require explicit real-network,
sandbox-order, MOCK, exact URL, explicit credentials, and auth-token flags.
Submit accepts only an existing approved OrderIntent ID; no ad-hoc order CLI
exists.

## Testing

All network-capable behavior is tested through injected fake token/HTTP
transports. Tests cover PAPER regression, SANDBOX opt-in approval, LIVE
blocking, safety validation, duplicate pre-network rejection, bounded
cancel/status, redaction, CLI JSON safety, and existing v2.9-v2.15 regressions.
