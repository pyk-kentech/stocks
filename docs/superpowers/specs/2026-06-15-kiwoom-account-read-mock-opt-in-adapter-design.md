# v2.19 Kiwoom Account-Read MOCK Opt-in Adapter Design

## Scope

v2.19 adds a separate, default-disabled MOCK-only account-read boundary. It
uses only the v2.13 manifest `ACCOUNT_READ` endpoints `kt00001`, `kt00018`,
and `kt00007` at the exact `https://mockapi.kiwoom.com` base URL.

PROD, LIVE, ORDER, READ_ONLY market data, WebSocket, unknown endpoints,
strategy access, automatic sizing, and automatic order submission remain
blocked.

## Components

- `kiwoom_account_read_models.py`: config, run, request, response, preview,
  status, and sanitization
- `kiwoom_account_read_gate.py`: endpoint selection and fail-closed activation
  gate
- `kiwoom_account_read_transport.py`: fake-testable MOCK ACCOUNT_READ
  transport with strict manifest allowlist
- `kiwoom_account_read_service.py`: offline health/plan, dry-run/run,
  redacted persistence, reports/show, and reconciliation preview

## Activation And Kill Switch

Run requires explicit real-network and account-read enablement, MOCK, exact
base URL, ENV or FILE_EXPLICIT credentials, auth-token opt-in, account
confirmation, account fingerprint confirmation, and acknowledgement.

The v2.19 kill-switch input is explicit and fail-closed. An active or unknown
switch blocks before credential loading, token provider creation, transport,
account request, persistence of account results, or reconciliation output.
No kill-switch file or environment variable is auto-discovered.

## Privacy And Persistence

Raw request and response bodies are used only inside the injected transport
boundary and are discarded immediately after normalization. SQLite stores only
redacted run/request/response/preview models. Default output excludes account
number, cash, balance, exact holdings, credentials, tokens, authorization, and
raw bodies.

The normalized summary contains status, counts, and bounded safe metadata.
Reconciliation preview is count-only in v2.19 and never submits orders.

## CLI

Add separate JSON commands:

- `kiwoom-account-read-health`
- `kiwoom-account-read-plan`
- `kiwoom-account-read-run`
- `kiwoom-account-read-reports`
- `kiwoom-account-read-show`
- `kiwoom-account-read-reconcile-preview`

Health and plan are offline. Dry-run validates gates without credentials,
token, or network. Run defaults to one endpoint and has a hard maximum of two.

## Testing

All executable tests inject fake credentials, fake token providers, and fake
HTTP clients. Pytest and system-smoke perform no real network calls. Existing
LIVE, sandbox-order, and read-only boundaries remain unchanged.
