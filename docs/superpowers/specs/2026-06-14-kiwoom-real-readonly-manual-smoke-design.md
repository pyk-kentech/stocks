# v2.15 Kiwoom Real-Network Read-only Manual Smoke Design

## Purpose

v2.15 adds a manual, user-invoked smoke harness for the v2.14 Kiwoom
real-network read-only adapter. It helps a user validate authentication and a
small set of official Kiwoom MOCK READ_ONLY endpoints without adding automatic
network calls to pytest or system-smoke.

This release does not add live trading, order submission, order modification,
order cancellation, WebSocket access, PROD access, or account-related reads.

## Architecture

Add a separate `KiwoomRealReadOnlySmokeService` rather than modifying the
v2.11 fake read-only service or mixing smoke orchestration into the v2.14
general read-only service.

The smoke service owns:

- offline plan generation
- preflight validation
- endpoint selection and deduplication
- dry-run behavior
- bounded sequential smoke execution
- redacted run and step audit persistence

For a real manual run, endpoint calls reuse the v2.14
`KiwoomRealReadOnlyService` and transport policy. Tests inject fake transport
and token providers only.

## Endpoint Policy

The smoke allowlist is exactly:

- `ka10001`: stock info
- `ka10004`: quote/orderbook
- `ka10020`: ranking
- `ka10008`: investor flow
- `ka10080`: minute chart
- `ka10081`: daily chart

The `minimal` endpoint set contains only `ka10001`.

Explicit endpoint IDs are deduplicated before execution. A smoke run may
contain at most three distinct endpoint IDs. WebSocket, ORDER, ACCOUNT_READ,
AUTH, UNKNOWN, and unlisted endpoints are blocked before any network call.

## Activation And Credentials

The smoke plan is offline by default. It does not read credentials or use the
network.

A smoke run requires:

- `--enable-real-network`
- `--environment MOCK`
- exact base URL `https://mockapi.kiwoom.com`
- explicit `--credential-source ENV` or `FILE_EXPLICIT`
- exact `--credential-file` when `FILE_EXPLICIT` is selected
- `--allow-auth-token-request`
- explicit endpoint IDs or `--endpoint-set minimal`

`--dry-run` performs all policy validation without reading ENV values or a
credential file and without calling a token provider or HTTP client. It records
validated steps as `DRY_RUN`.

A non-dry manual run reads credentials only after preflight validation. It
never searches for credentials or scans directories.

## Data Model And Persistence

Add:

- `KiwoomRealReadOnlySmokeRun`
- `KiwoomRealReadOnlySmokeStep`
- `KiwoomRealReadOnlySmokeStatus`

Add append-only SQLite tables:

- `kiwoom_real_readonly_smoke_runs`
- `kiwoom_real_readonly_smoke_steps`

Run records contain:

- smoke run ID
- enabled and dry-run flags
- environment
- base URL allowed boolean
- credential source
- endpoint set and endpoint IDs
- status and success/failure counts
- warnings, sanitized errors, and observed timestamps

Step records contain:

- smoke run ID
- endpoint ID, path, and classification
- request status
- response HTTP status when available
- success boolean
- sanitized error
- observed timestamp

Audit JSON never contains request bodies, response bodies, token, appkey,
secretkey, authorization headers, account number, raw credential file content,
or credential file path/name.

## Status And Failure Isolation

Run statuses:

- `PLANNED`: offline plan output
- `DRY_RUN`: all selected endpoints passed preflight without network
- `COMPLETED`: all selected endpoint calls completed
- `PARTIAL`: at least one endpoint completed and at least one failed or blocked
- `FAILED`: preflight failed or no endpoint completed
- `BLOCKED`: activation or safety policy blocked execution

Endpoint calls run sequentially. A failed endpoint does not prevent remaining
validated endpoints from running. The maximum of three endpoints and the
v2.14 per-run request limit remain enforced.

Errors are sanitized before CLI output and persistence. Credential-like values
and sensitive field names are not retained.

## CLI

Add separate commands:

- `kiwoom-real-readonly-smoke-plan`
- `kiwoom-real-readonly-smoke-run`
- `kiwoom-real-readonly-smoke-reports`
- `kiwoom-real-readonly-smoke-show`

`smoke-plan` prints the minimal endpoint set, full allowed endpoint IDs,
required real-run flags, MOCK/exact-base-URL requirements, and safety warnings.

`smoke-run` supports repeated `--endpoint-id`, `--endpoint-set minimal`,
`--dry-run`, the v2.14 activation options, and a maximum endpoint count of
three.

`smoke-reports` and `smoke-show` read only redacted smoke audit records.

## Testing

Use TDD for models, validation, orchestration, persistence, and CLI.

Tests cover:

- offline plan without credential or network access
- every required activation/preflight rejection
- dry-run without credential/token/HTTP access
- minimal set behavior and endpoint deduplication
- WebSocket, ORDER, ACCOUNT_READ, AUTH, and unknown blocking
- hard maximum of three endpoints
- fake-only successful, partial, and failed execution
- redaction of token, authorization, appkey, secretkey, account number,
  request/response bodies, and credential paths
- report list/show CLI
- existing v2.9 through v2.14 and provider-pack regressions
- pytest and system-smoke remaining free of real network calls

## Documentation And Safety Boundary

README and WORK_SUMMARY will document:

- v2.15 is manual-smoke-only
- v2.14 provides the adapter; v2.15 provides bounded manual verification
- dry-run and real MOCK examples using placeholders only
- pytest and system-smoke never perform real network calls
- no live trading, orders, account reads, WebSocket, or PROD
- redaction policy and troubleshooting guidance

The manual smoke harness is never invoked by system-smoke or automated tests
with a real transport.
