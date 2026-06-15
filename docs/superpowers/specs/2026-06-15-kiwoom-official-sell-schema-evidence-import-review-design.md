# v2.23 Kiwoom Official SELL Schema Evidence Import And Review Design

## Scope

v2.23 adds an offline, manual workflow for importing, validating, reviewing,
and auditing official Kiwoom SELL schema evidence. It does not enable actual
sandbox SELL, SELL dry-run approval, PROD, LIVE, credentials, tokens, account
reads, strategy broker access, or network calls.

Evidence verification and execution permission are separate boundaries.
Complete reviewed official evidence may allow the v2.22 schema verifier to
report `VERIFIED`, but v2.23 SELL dry-run remains blocked with
`SELL_DRY_RUN_APPROVAL_DISABLED_IN_V2_23`. Actual sandbox SELL remains blocked
with `SELL_SANDBOX_ORDER_SCHEMA_NOT_VERIFIED`.

## Evidence Source Policy

Allowed evidence is an explicitly selected local JSON or YAML file describing
official Kiwoom documentation. The service reads only that exact path. It does
not search directories, discover files, scrape the web, read credentials,
request tokens, or call a network.

`source_kind` must be `OFFICIAL_KIWOOM_DOCUMENTATION`. Endpoint identity,
path, method, and classification must match the committed v2.13 manifest.
Unofficial sources, inferred fields, guessed values, and ambiguous mappings
are rejected or require review.

## Evidence Model

`OfficialSellSchemaEvidence` contains safe normalized metadata:

- evidence ID, source kind/title/URL metadata, captured time, checksum
- endpoint ID/path/method/classification and environment support
- explicit side field, documented BUY and SELL values
- explicit order-type field and documented LIMIT value
- explicit symbol, quantity, limit-price, and account-handling fields
- idempotency notes, redaction policy, and sanitized notes

`OfficialSellSchemaEvidenceField` stores one normalized required mapping.
`OfficialSellSchemaEvidenceValidationResult` records valid, missing,
ambiguous, and rejected reasons. `OfficialSellSchemaEvidenceImportReport`
records import outcome without retaining raw file content.

Review statuses are:

- `IMPORTED`
- `VALIDATED`
- `REJECTED`
- `NEEDS_MANUAL_REVIEW`
- `SUPERSEDED`

Review decisions are append-only. Existing evidence and prior decisions are
not overwritten.

## Validation And Redaction

The validator:

- validates strict file structure
- verifies the endpoint exists and is an `ORDER` endpoint
- requires exact manifest path and method
- requires explicit BUY, SELL, LIMIT, symbol, quantity, limit-price, account
  handling, idempotency, and redaction metadata
- calculates SHA-256 checksum from the selected file bytes
- rejects unofficial source kind and guessed/ambiguous values
- rejects sensitive patterns such as app keys, secret keys, bearer tokens,
  authorization headers, raw credential content, and account-number-like
  values

The raw file and raw payload are never persisted. SQLite and CLI expose only
safe normalized metadata, checksum, validation results, and append-only review
records. Source URL is metadata only and is never fetched.

## Service And CLI

`KiwoomOfficialSellSchemaEvidenceService` provides:

- offline validate without persistence
- validate-then-import with safe normalized persistence
- list/show safe evidence
- append-only review

CLI commands:

- `kiwoom-official-sell-schema-evidence-validate`
- `kiwoom-official-sell-schema-evidence-import`
- `kiwoom-official-sell-schema-evidence-list`
- `kiwoom-official-sell-schema-evidence-show`
- `kiwoom-official-sell-schema-evidence-review`

Missing or invalid files return JSON-safe errors without traceback.

## SQLite Audit

Add:

- `kiwoom_official_sell_schema_evidence`
- `kiwoom_official_sell_schema_evidence_fields`
- `kiwoom_official_sell_schema_evidence_imports`
- `kiwoom_official_sell_schema_evidence_reviews`

Evidence import stores safe normalized metadata only. Field rows contain safe
field names and documented values only after sensitive-pattern validation.
Import and review rows are append-only.

## v2.22 Verifier Integration

When a repository is supplied, `KiwoomSandboxSellSchemaVerifier` checks the
latest eligible imported evidence:

- absent evidence: `UNVERIFIED`
- imported but unreviewed evidence: `UNVERIFIED`
- rejected or superseded evidence: `UNVERIFIED`
- complete validated evidence with latest `VALIDATED` review: `VERIFIED`

The verifier reports evidence availability and source references without
exposing raw file content. Imported evidence never changes the official
endpoint runtime allowlist.

## Execution Boundary

v2.23 never permits SELL dry-run approval. The dry-run service always adds
`SELL_DRY_RUN_APPROVAL_DISABLED_IN_V2_23`, even if schema verification is
`VERIFIED` and all v2.21 gates pass.

Actual `KiwoomSandboxOrderService.submit()` remains unchanged and continues to
block SELL. Evidence import, validation, review, and verifier execution never
submit orders or create transports.

## Safety And Compatibility

- PROD and LIVE remain blocked.
- MARKET, margin, short, credit, leverage, options, futures, and fractional
  shares remain blocked.
- Account-read and reconciliation cannot trigger orders.
- Direct strategy broker/API access remains blocked.
- BUY sandbox behavior is unchanged.
- Tests and system smoke use only explicit temporary files and local/fake data.
- `external_network_calls=false` remains required.

## Future Boundary

v2.24 may separately consider MOCK sandbox SELL dry-run approval after reviewed
official evidence produces `VERIFIED`. Actual MOCK sandbox SELL submission,
PROD, and LIVE each require later independent releases.
