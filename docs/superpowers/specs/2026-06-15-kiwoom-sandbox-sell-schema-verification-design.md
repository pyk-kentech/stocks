# v2.22 Kiwoom Sandbox SELL Schema Verification And Dry-Run Gate Design

## Scope

v2.22 adds an offline verifier for Kiwoom MOCK sandbox SELL request schemas
and a fail-closed SELL dry-run gate. It does not enable actual sandbox SELL,
PROD, LIVE, account-read-driven orders, strategy broker access, credentials,
tokens, or network calls.

The current curated official manifest verifies `kt10000` as the stock BUY
ORDER endpoint and `kt10003` as cancellation. It does not contain an explicit
SELL submit endpoint, an official SELL side value, or official request field
mapping. Therefore the v2.22 repository-local verification result is
`UNVERIFIED`, and both actual sandbox SELL and SELL dry-run approval remain
blocked with `SELL_SANDBOX_ORDER_SCHEMA_NOT_VERIFIED`.

## Evidence Policy

The verifier accepts only committed, project-local official evidence:

- `configs/kiwoom_official_endpoint_manifest.json`
- committed official schema metadata added in a future release
- committed design documentation that cites official source metadata

Internal `OrderIntent`, `KiwoomSandboxOrderRequest`, adapter body keys, and
test fixtures are implementation models. They are not proof of official
Kiwoom request field names or values.

The verifier never scrapes the web, reads credentials, requests tokens, calls
HTTP, scans local secret paths, or infers Korean field names, endpoint IDs,
side codes, account fields, or order-type codes.

## Verification Model

`SandboxSellSchemaVerificationStatus` supports:

- `VERIFIED`
- `UNVERIFIED`
- `AMBIGUOUS`
- `MISSING_REQUIRED_FIELD`
- `BLOCKED_UNOFFICIAL_ASSUMPTION`

`SandboxSellSchemaVerificationReport` records the endpoint ID, endpoint class,
overall status, verified fields, missing fields, ambiguous fields, blocked
reason, safe source references, and redacted metadata.

Required official evidence:

- ORDER endpoint ID, exact path, and POST method
- MOCK-only policy
- explicit request-side field
- explicit documented BUY and SELL values
- explicit LIMIT order-type field and value
- explicit symbol, integer quantity, and limit-price fields
- explicit account-field handling with redaction policy
- safe client-order-id/idempotency and duplicate-prevention handling

If any required official mapping is absent, the report cannot be `VERIFIED`.
Unofficial or inferred mapping evidence produces
`BLOCKED_UNOFFICIAL_ASSUMPTION`.

## Verifier

`KiwoomSandboxSellSchemaVerifier` is a pure offline service. By default it
loads the current curated manifest and evaluates `kt10000`. It confirms only
evidence actually present in committed sources and persists a safe report.

With the current repository evidence:

- endpoint ID, path, method, and ORDER classification are verified
- SELL endpoint semantics and required request field/value mappings are
  missing
- result is `UNVERIFIED`

The verifier stores no raw request body, raw response body, account number,
balance, holdings, credentials, token, authorization header, or secret path.

## SELL Dry-Run Gate

`KiwoomSandboxSellDryRunService` creates a sanitized audit result without
credentials, token requests, transport construction, or order submission.

An `APPROVED_FOR_DRY_RUN` result requires all of:

- SELL `OrderIntent`
- KR equity LIMIT order with positive integer quantity and positive limit
  price
- approved matching `SellSafetyDecision`
- approved matching `RiskGateDecision`
- approved matching `ExecutionMode.SANDBOX` decision
- current local-ledger quantity remains sufficient
- latest schema verification report is `VERIFIED`
- MOCK environment
- PROD and LIVE disabled

Any failure produces a blocked dry-run with explicit reasons. Schema states
other than `VERIFIED` always include
`SELL_SANDBOX_ORDER_SCHEMA_NOT_VERIFIED`.

Reconciliation, account-read, strategy, and dry-run results never trigger an
order. Actual `KiwoomSandboxOrderService.submit()` keeps its existing SELL
block in v2.22, even if a future test fixture can construct a `VERIFIED`
report. Actual MOCK SELL submission requires a separate future release.

## CLI And Audit

Add offline JSON commands:

- `kiwoom-sandbox-sell-schema-verify`
- `kiwoom-sandbox-sell-schema-reports`
- `kiwoom-sandbox-sell-schema-show`
- `kiwoom-sandbox-sell-dry-run`

Add append-only SQLite tables:

- `kiwoom_sandbox_sell_schema_reports`
- `kiwoom_sandbox_sell_schema_fields`
- `kiwoom_sandbox_sell_dry_runs`

Schema field rows store only field name, verification state, safe source
reference, and redacted notes. Dry-run rows store sanitized planned metadata
and blocked reasons. No table stores raw broker/account payloads or secrets.

## Safety And Compatibility

- PROD and LIVE remain blocked.
- MARKET, margin, short, credit, leverage, options, futures, and fractional
  shares remain blocked.
- Existing BUY sandbox behavior is unchanged.
- Existing SELL submit remains blocked.
- Existing v2.13 through v2.21 behavior remains compatible.
- Pytest and system smoke use local/fake data only and keep
  `external_network_calls=false`.

## Testing

Tests cover offline verifier behavior, missing and unofficial evidence,
endpoint classification rejection, all SELL dry-run gates, safe audit
persistence, CLI output redaction, unchanged BUY behavior, continued actual
SELL blocking, and full regression validation.

## Future Boundary

If official SELL schema evidence remains unavailable, v2.23 may add a
reviewed official SELL schema documentation/import step. If that evidence is
added and verified, a later v2.23 release may add MOCK sandbox SELL submission
behind every existing gate. PROD and LIVE remain separate future boundaries.
