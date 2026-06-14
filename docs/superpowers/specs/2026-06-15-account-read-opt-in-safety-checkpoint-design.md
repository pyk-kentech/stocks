# v2.18 Account-Read Opt-in Safety Checkpoint Design

## Purpose And Scope

v2.18 is a design and approval checkpoint for a future Kiwoom account-read
adapter. It does not implement account, balance, cash, holdings, positions,
fills, or order-history calls. It adds no account-read transport, PROD access,
live trading, credential loading, or automatic real-network tests.

All official `ACCOUNT_READ` endpoints remain runtime-disabled. Existing
READ_ONLY market-data, MOCK sandbox-order, and LIVE-blocking behavior remains
unchanged.

## Future Activation Model

A future account-read request must fail closed unless every gate is satisfied:

- persisted configuration has `account_read_enabled=true`; default is `false`
- CLI includes `--enable-account-read`
- the environment is explicitly selected; future work starts with MOCK
- PROD remains blocked until a separate approval checkpoint
- the base URL exactly matches an officially verified URL for that environment
- credentials come only from explicit ENV names or one exact
  `FILE_EXPLICIT --credential-file <path>`
- an explicit account confirmation flag is present
- the supplied account fingerprint matches the redacted expected fingerprint
- the exact acknowledgement phrase is supplied:
  `I_UNDERSTAND_THIS_CAN_READ_ACCOUNT_DATA`
- endpoint ID and path exactly match an allowlisted v2.13 manifest
  `ACCOUNT_READ` entry
- all kill switches are confirmed inactive
- response redaction and bounded normalized storage are enabled

The acknowledgement phrase is documented only. v2.18 does not add a runtime
flag or CLI command for it. No credential or account path is auto-discovered.

## Scope Separation

The future account-read adapter is a separate boundary from:

- READ_ONLY market-data services
- MOCK sandbox-order services
- future live-order services
- strategy logic and policy optimization
- risk scoring and automatic order sizing

Allowed consumers are limited to local position-ledger reconciliation,
sell-safety validation, exposure/risk dashboards, and explicit manual
audit/report commands. Strategy code must never directly read account data.
Fresh account-read data must not be placed in the same unsafe chain as a live
submit, and automatic sizing must not directly consume broker account balance.

## Endpoint Policy

The v2.13 curated official manifest is the only endpoint source of truth.
Candidate future account-read endpoints currently verified in that manifest
are:

- `kt00001` `/api/dostk/acnt`: deposit details
- `kt00018` `/api/dostk/acnt`: account evaluation balance details
- `kt00007` `/api/dostk/acnt`: account order execution details

These are candidates only and remain runtime-disabled in v2.18. Future
account-read may allow only endpoints classified `ACCOUNT_READ` and explicitly
added to a versioned account-read allowlist. ORDER, READ_ONLY market data,
AUTH outside a restricted token provider, UNKNOWN_REVIEW_REQUIRED, WebSocket,
PROD without separate approval, and every non-allowlisted endpoint remain
blocked.

## Credential And Account-Data Policy

Credential loading must occur only after configuration, endpoint, confirmation,
acknowledgement, and kill-switch checks pass. The future adapter must never
scan local directories, dump environment variables, or print/store app keys,
secret keys, tokens, authorization headers, credential paths, or credential
contents. Real credential fixtures are forbidden.

Raw account numbers, holder information, balance bodies, holdings bodies, fill
bodies, and order-history bodies must never be stored. Allowed normalized
storage is limited to:

- `account_loaded` boolean
- salted or irreversible short account fingerprint
- currency
- coarse total exposure only when explicitly enabled
- symbol-level quantity only for local ledger reconciliation
- redacted broker metadata
- sanitized errors
- `observed_at`

## Kill-Switch Integration

Account-read is blocked if any global, session, broker, or account kill switch
is active. Future sources include an explicitly configured emergency local
file, an environment variable, and SQLite persisted state.

No kill-switch source is auto-discovered. Active, missing, unreadable,
unknown, inconsistent, or unavailable switch state fails closed before any
credential read, token request, network call, or account endpoint call. Every
check and state transition must be auditable.

## Privacy-Safe Output

Default future CLI output may show:

- `account_read_enabled`
- `credential_source`
- `account_loaded`
- `endpoint_id`
- `endpoint_classification`
- `request_status`
- `response_status_code`
- sanitized status summary

Default output must not show account number, cash amount, total balance, exact
holdings, raw fills, raw order history, token, authorization header, app key,
secret key, or raw response body. Any future detailed output requires another
explicit opt-in and remains redacted.

## Fake-Only Test Policy

Future implementation tests must use fake credentials, fake token providers,
fake transports, and deterministic local responses. They must prove default
blocking; missing opt-in, credentials, account confirmation, fingerprint,
acknowledgement, or inactive kill-switch proof; endpoint-class separation;
PROD and WebSocket blocking; dry-run without credential/token/network access;
output and audit redaction; and no effect on LIVE blocking.

`pytest` and `system-smoke` must never perform real network calls. System smoke
must remain `COMPLETED` with `external_network_calls=false`.

## v2.18 Checkpoint Outcome

This checkpoint adds only documentation and regression guards. It confirms all
manifest `ACCOUNT_READ` entries remain runtime-disabled, the existing real
READ_ONLY transport rejects account endpoints before HTTP, and LIVE remains
blocked. A future account-read implementation requires a separate approved
change.
