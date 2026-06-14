# Kiwoom Real-Network Read-only Opt-in Adapter Design

## Purpose

v2.14 adds a separate, explicit opt-in boundary for real-network Kiwoom
read-only calls. Existing v2.11 fake read-only commands and v2.12 mock
execution commands remain unchanged.

v2.14 is not live trading. It does not place or cancel orders and does not
query account, balance, cash, holdings, positions, fills, or order history.

## Activation Contract

A real read-only request is permitted only when all conditions hold:

- `enabled=true` from explicit CLI `--enable-real-network`
- environment is `MOCK`
- base URL is exactly `https://mockapi.kiwoom.com`
- endpoint is one of the approved v2.13 manifest REST READ_ONLY entries
- endpoint API ID is in the v2.14 six-endpoint curated allowlist
- credentials came from explicit ENV opt-in or exact `--credential-file`
- a token provider supplied a token through the controlled token flow
- per-run request limit has not been exceeded

`PROD_READONLY_DISABLED`, websocket endpoints, AUTH through the general
transport, ORDER, ACCOUNT_READ, and UNKNOWN endpoints always block.

## Architecture

```text
Explicit CLI
-> KiwoomRealNetworkConfig
-> explicit credential loader
-> controlled token provider
-> KiwoomRealReadOnlyService
-> RealKiwoomReadOnlyHttpTransport
-> official MOCK host only
-> redacted SQLite audit
```

The real service is separate from v2.11. Tests inject fake token providers and
fake HTTP clients; pytest and system-smoke never perform real network calls.

## Allowed Runtime Endpoints

- `ka10001` stock info
- `ka10004` quote/orderbook
- `ka10020` ranking
- `ka10008` investor flow
- `ka10080` minute chart
- `ka10081` daily chart

The v2.13 manifest remains the source of official ID/path/classification data.
The transport never accepts arbitrary endpoint definitions.

## Credentials And Tokens

Credential sources:

- `NONE`
- `ENV`, only when explicitly selected
- `FILE_EXPLICIT`, only for the exact user-provided file

There is no file discovery or directory scanning. Credentials and tokens use
masked representations and never appear in CLI output or audit metadata.
Account number may be parsed but is unused.

`FakeKiwoomTokenProvider` is deterministic and used by tests/offline paths.
`RealKiwoomTokenProvider` may call only the official AUTH token endpoint when
network, credentials, and `allow_auth_token_request` are all explicitly
enabled.

## Transport And Audit

The stdlib HTTP transport applies the configured timeout and no automatic
retry loop. It validates the exact host and manifest class before each call,
redacts authorization metadata, and enforces a small per-run request limit.

Append-only SQLite tables store real-readonly run, request, and response audit
records. Audits contain status, classification, endpoint identity, errors, and
redacted metadata only.

## CLI

Add separate `kiwoom-real-readonly-*` commands. The health command defaults to
disabled. Selected data commands mirror the six curated endpoints. No command
modifies existing v2.11 fake CLI behavior.

## Future Work

- v2.15 user-run manual real-network read-only smoke
- v2.16 explicitly opt-in Kiwoom sandbox order adapter
- v2.17 default-off live execution adapter with explicit kill switch
