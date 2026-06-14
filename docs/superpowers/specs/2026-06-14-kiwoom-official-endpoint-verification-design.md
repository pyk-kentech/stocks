# Kiwoom Official Endpoint Verification Design

## Purpose

v2.13 adds a curated manifest of representative endpoints verified from the
official Kiwoom REST API guide. It verifies endpoint classification and runtime
safety policy. It is not a complete Kiwoom API catalog and does not call any
official endpoint.

## Source And Scope

The only endpoint source is the official `openapi.kiwoom.com` API guide. Each
manifest entry records the official API ID, path, method, name, category,
source URL, and verification date. Entries whose ID/path/method cannot be
directly confirmed are excluded.

The curated manifest contains 12-20 representative endpoints:

- AUTH: token issuance and revocation
- READ_ONLY: stock info, quote/market condition, chart, ranking, investor flow,
  and condition search
- ORDER: stock order submission and cancellation
- ACCOUNT_READ: representative cash, balance/holdings, or order-history reads

Full official endpoint coverage is intentionally deferred.

## Architecture

```text
configs/kiwoom_official_endpoint_manifest.json
-> manifest loader
-> schema and safety validator
-> read-only list/show/validate CLI
```

The manifest is file-based and deterministic. SQLite persistence is excluded
because v2.13 is a documentation and verification layer, not a runtime
integration layer.

## Classification And Runtime Policy

Classes:

- `READ_ONLY`
- `ORDER`
- `ACCOUNT_READ`
- `AUTH`
- `UNKNOWN_REVIEW_REQUIRED`

All official manifest entries have
`runtime_allowed_in_current_version=false`, including READ_ONLY endpoints.
The manifest is never passed to a transport or adapter.

Dangerous-keyword endpoints must be disabled. AUTH, ORDER, ACCOUNT_READ, and
UNKNOWN_REVIEW_REQUIRED entries must be disabled regardless of path.

## Isolation From Existing Runtime Endpoints

- v2.11 internal deterministic `/readonly/*` remains the only Kiwoom-shaped
  read-only runtime used in tests and CLI.
- v2.12 local `/kiwoom-mock/*` remains the only Kiwoom-shaped execution runtime
  used in tests and CLI.
- Official manifest paths are data only and are never added to either runtime
  allowlist.

## Validation

The validator checks:

- manifest schema and required fields
- unique `api_id + path`
- valid category and class
- source presence and official source host
- forbidden classes are runtime disabled
- every dangerous-keyword path is runtime disabled
- no official manifest path appears in v2.11 or v2.12 runtime allowlists

Validation output includes class counts, disabled dangerous endpoint count,
duplicate count, errors, and overall validity.

## CLI

- `kiwoom-official-endpoints-list`
- `kiwoom-official-endpoints-validate`
- `kiwoom-official-endpoint-show`

Commands read only the committed JSON manifest and return JSON. They expose no
network, token, credential, account, or execution options.

## Safety

v2.13 performs no real Kiwoom network call, OAuth request, secret read, account
runtime access, or order execution. It adds no HTTP/Kiwoom/Windows SDK and does
not inspect local credential directories.

## Future Work

- v2.14: explicitly opt-in real-network read-only adapter
- v2.15: explicitly opt-in sandbox order adapter
- v2.16: default-off live execution adapter with explicit kill switch
