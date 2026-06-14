# v2.11 Kiwoom REST Read-only Adapter Design

## Goal

Add a Kiwoom-shaped read-only adapter foundation using only fake tokens,
deterministic local responses, and fake transport. v2.11 performs no real
Kiwoom authentication, network request, account read, or order operation.

## Endpoint Contract

v2.11 uses only these internal deterministic endpoints:

```text
RO_STOCK_INFO       /readonly/stock-info
RO_QUOTE            /readonly/quote
RO_RANKING          /readonly/ranking
RO_FLOW             /readonly/flow
RO_CHART            /readonly/chart
RO_CONDITION_LIST   /readonly/condition/list
RO_CONDITION_RUN    /readonly/condition/run
```

These endpoint IDs and paths exist only for:

- fake transport
- deterministic local fixtures
- allowlist tests
- CLI/read-only adapter contract validation

They are not official Kiwoom endpoint IDs or paths.

**Internal deterministic endpoint only; official Kiwoom endpoint mapping
deferred.**

Official production/mock base URLs and OAuth/header concepts may be described
as future integration assumptions, but v2.11 does not use them.

## Architecture

```text
KiwoomRestReadOnlyAdapter
-> KiwoomRestClient
-> KiwoomReadOnlyAllowlist
-> KiwoomTransport Protocol
-> FakeKiwoomTransport by default
-> normalized read-only models
-> optional SQLite request/response audit
```

Files and responsibilities:

- `kiwoom_readonly_models.py`: enums, endpoint, token, normalized outputs,
  audit models
- `kiwoom_readonly_allowlist.py`: fixed internal read-only endpoints and
  conservative forbidden-term validation
- `kiwoom_transport.py`: transport protocol, fake transport, disabled real
  transport stub
- `kiwoom_rest_client.py`: allowlist validation, fake bearer header
  construction, continuation handling, JSON-safe response envelope
- `kiwoom_readonly_adapter.py`: normalized read-only methods
- `repository.py`: append-only sanitized request/response audits
- `cli.py`: nine read-only JSON commands

Strategies, OrderIntent, ExecutionGate, BrokerAdapterService, and broker order
submission do not import or call this adapter.

## Secret Safety Boundary

The user has a local secret directory outside the repository. v2.11 treats all
external secret locations as inaccessible.

The implementation and tests:

- do not inspect external secret directories
- do not enumerate secret filenames
- do not read app keys, secret keys, tokens, account numbers, certificates, or
  credential files
- do not dump environment variables
- do not include real credentials in fixtures, logs, README, or WORK_SUMMARY
- do not copy secret files into the repository

Existing `.gitignore` local broker/API secret patterns remain in force.

All tests and CLI use a constant fake token whose value is never persisted,
returned, or logged.

## Models

### Enums

- `KiwoomEnvironment`: `MOCK`, `PROD_DISABLED`
- `KiwoomEndpointCategory`: `OAUTH`, `STOCK_INFO`, `QUOTE`, `RANKING`, `FLOW`,
  `CHART`, `CONDITION_SEARCH`, `REALTIME_METADATA`

### Endpoint And Token

`KiwoomReadOnlyEndpoint` stores `api_id`, `path`, category, description,
`read_only`, and `enabled`.

`KiwoomToken` stores access token, type, issue/expiry timestamps, environment,
and metadata. It is an in-memory client input only. Repositories and audit
models never accept a token or authorization header.

Real token issuance is absent.

### Normalized Outputs

Add:

- `KiwoomStockInfo`
- `KiwoomQuote`
- `KiwoomRankItem`
- `KiwoomFlowItem`
- `KiwoomChartBar`
- `KiwoomConditionSearchItem`

Each model preserves deterministic fake raw data in `raw_json`, normalizes
ticker text, and carries observation time where requested.

### Audit Models

`KiwoomReadOnlyRequestAudit` stores request ID, endpoint identity/category,
safe selector fields, status, error, observed time, and sanitized metadata.

`KiwoomReadOnlyResponseAudit` stores response ID, request ID, status, error,
observed time, and sanitized response metadata.

Neither model has authorization, token, secret, account, balance, position, or
raw credential fields.

## Strict Allowlist

The allowlist contains exactly the seven internal deterministic endpoints.

An endpoint is accepted only when:

- both `api_id` and `path` exactly match one enabled allowlisted definition
- `read_only=true`
- no forbidden term appears in API ID, path, category, or description

Forbidden terms:

```text
order buy sell cancel account balance position holding fill execution
cash margin credit
```

Unknown/mismatched/disabled/non-read-only endpoints are rejected.

`OAUTH` and `REALTIME_METADATA` categories exist as future model boundaries but
have no enabled endpoint in the v2.11 allowlist.

## Transport Boundary

```python
class KiwoomTransport(Protocol):
    def post(self, path: str, headers: dict, body: dict) -> dict: ...
```

### FakeKiwoomTransport

- deterministic fixture mapping keyed by path
- no file reads
- no network
- no secrets
- records only sanitized call metadata
- returns deterministic body and optional `cont-yn` / `next-key`
- can return configured error code/message

Default fixtures are in Python constants and contain no real credentials.

### RealKiwoomHttpTransport

This is a disabled stub only. `post()` always raises
`DisabledNetworkError("real Kiwoom network transport disabled in v2.11")`.
There is no opt-in flag in v2.11, no HTTP library use, and no credential read.

## KiwoomRestClient

`request_readonly(api_id, path, body)`:

1. verifies exact allowlist match
2. builds an in-memory header with fake bearer token, API ID, and optional
   continuation values
3. calls the injected transport
4. returns a JSON-safe response envelope with body, sanitized continuation
   metadata, status, and error
5. never returns or stores headers or token values

Continuation is deterministic. When a response has `cont-yn=Y` and
`next-key`, the client may request subsequent pages up to a configured bounded
maximum and merge list records. No future or infinite continuation is
possible.

Transport and validation errors become failed response envelopes without
tracebacks for normal CLI paths.

## Read-only Adapter

`KiwoomRestReadOnlyAdapter` defaults to `KiwoomEnvironment.MOCK`,
`FakeKiwoomTransport`, internal allowlist, and a constant fake token.

Methods:

- `health_check()`
- `list_readonly_endpoints()`
- `get_stock_info(ticker)`
- `get_quote(ticker)`
- `get_rankings(rank_type, market)`
- `get_flow(ticker=None, market=None)`
- `get_chart_bars(ticker, interval, count)`
- `list_condition_searches()`
- `run_condition_search(condition_id)`

The adapter normalizes fake response records to internal models. Invalid or
error responses produce JSON-safe result dictionaries with errors.

`PROD_DISABLED` health and requests are disabled. There is no production
network path.

## Persistence

Add append-only tables:

- `kiwoom_readonly_requests`
- `kiwoom_readonly_responses`

Every CLI adapter request saves a sanitized request audit and sanitized
response audit. Health and endpoint-list commands do not need request/response
audits because they perform no transport request.

Repository methods:

- save/list Kiwoom read-only request audits
- save/list Kiwoom read-only response audits

No authorization header, token, raw secret, or environment dump is persisted.

## CLI

Add:

- `kiwoom-readonly-health`
- `kiwoom-readonly-endpoints`
- `kiwoom-readonly-stock-info`
- `kiwoom-readonly-quote`
- `kiwoom-readonly-rankings`
- `kiwoom-readonly-flow`
- `kiwoom-readonly-chart`
- `kiwoom-readonly-condition-list`
- `kiwoom-readonly-condition-run`

All commands default to `MOCK`. `PROD_DISABLED` returns a normal JSON disabled
result. No network-enable, OAuth, token, credential, account, or order option
is added.

CLI output contains normalized data, request/response audit IDs where
applicable, continuation metadata, status, and errors. It contains no token,
authorization header, secret, account number, or environment-variable dump.

## Safety Boundaries

- no order/cancel/replace endpoint
- no account/balance/position/holding/fill/execution endpoint
- no OAuth request
- no official Kiwoom endpoint mapping
- no real Kiwoom network call
- no websocket
- no Kiwoom OpenAPI+/OCX/pykiwoom
- no Windows-only dependency
- no secret directory access
- no credential/environment dumping
- no strategy or execution integration
- fake transport by default and in all tests/smoke

System smoke remains unchanged and must report `COMPLETED` with
`external_network_calls=false`.

## Documentation And Future Path

README and WORK_SUMMARY will state:

- official Kiwoom REST is the preferred future Korean broker path
- OpenAPI+/pykiwoom is legacy reference only and not imported
- v2.11 is fake-transport read-only foundation
- internal endpoints are not official Kiwoom mappings
- no orders, account reads, credentials, or real network
- future v2.12 sandbox/mock execution and v2.13 live execution with explicit
  kill switch

## Verification

Tests cover endpoint exact matching, forbidden terms, fake deterministic
outputs, continuation, normalized errors, disabled real transport, sanitized
audits/CLI output, absence of secret/path/network/order/account integration,
and all existing regression suites.

Final verification:

```powershell
pytest -q
python -m compileall -q src
git diff --check
python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs
git status --short
```
