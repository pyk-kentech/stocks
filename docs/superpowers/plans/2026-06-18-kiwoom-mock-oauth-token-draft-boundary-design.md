# Kiwoom Mock OAuth Token Draft Boundary Design

> **For agentic workers:** v6.5 is design-only. Do not implement credential loading, environment-variable reads, token issuance, token revoke, API execution, mockapi execution, WebSocket transport, order execution, account mutation, or live trading from this plan.

**Goal:** Define the local, non-executable OAuth/token request draft boundary that must exist before any future Kiwoom mock REST token request implementation can be considered, while keeping v6.5 strictly mock-only, draft-only, disabled-by-default, explicit-opt-in, offline-only, and free of any credential or network runtime path.

**Authority:** Use only these local evidence artifacts:

- `docs/superpowers/specs/2026-06-18-kiwoom-rest-api-official-evidence-pack.md`
- `docs/superpowers/specs/2026-06-18-kiwoom-rest-api-capability-matrix.json`
- `docs/superpowers/plans/2026-06-18-kiwoom-mock-credential-environment-boundary-design.md`

**Core rule:** v6.5 does not issue OAuth tokens, does not revoke OAuth tokens, does not load credentials, does not read environment variables, does not call `https://mockapi.kiwoom.com`, does not call `https://api.kiwoom.com`, does not connect WebSocket, and does not create any executable request path. It only designs the draft boundary required before a future opt-in mock-only token executor could exist.

**Evidence anchors from local artifacts:**

- Production REST domain is documented as `https://api.kiwoom.com`.
- Mock REST domain is documented as `https://mockapi.kiwoom.com`.
- OAuth issue endpoint is documented as `POST /oauth2/token`.
- OAuth revoke endpoint is documented as `POST /oauth2/revoke`.
- Mock domain remains KRX-only.
- Current stage classification in the local capability matrix keeps OAuth surfaces not allowed now.

**Safety flags planned for every v6.5 artifact:**

- `mock_only=true`
- `oauth_draft_only=true`
- `credential_boundary_only=true`
- `disabled_by_default=true`
- `explicit_opt_in_required=true`
- `non_executable=true`
- `local_file_only=true`
- `offline_only=true`
- `no_credentials_loaded=true`
- `no_env_read=true`
- `no_token_issued=true`
- `no_token_revoked=true`
- `no_api_call=true`
- `no_mockapi_call=true`
- `no_websocket_connection=true`
- `no_network_call=true`
- `no_real_order=true`
- `no_live_trading=true`
- `no_live_prod=true`
- `no_account_mutation=true`
- `no_production_domain_execution=true`
- `no_cloud_llm=true`
- `no_local_llm_runtime=true`

## 1. Why A Token Draft Boundary Is Required Before Mockapi Token Execution

v6.4 established that credential references, environment separation, and explicit opt-in must be isolated before any mock execution work begins. v6.5 narrows that further around OAuth because the token boundary is the first point where a future implementation could accidentally cross from local planning into executable broker interaction.

Without a dedicated draft boundary, future work would risk mixing:

- documented endpoint metadata with executable HTTP request objects
- credential references with loaded secrets
- mock-only token intent with production-domain drift
- dry-run drafting with token issuance authorization
- report-only boundary checks with runtime transport construction

The token draft layer must therefore exist before any future mock token executor so the repository can fail closed on token shape, domain policy, opt-in state, and secret handling without building a runnable network path.

## 2. Boundary Position Relative To v6.4

v6.4 defined:

- credential reference boundaries
- environment naming policy
- domain separation policy
- explicit opt-in gate
- mock-only execution guardrails

v6.5 should sit directly above that boundary and below any future mock adapter execution work:

1. `KiwoomMockCredentialBoundaryConfig` and related v6.4 objects define whether a mock-only credential reference is even representable.
2. v6.5 draft objects define what a token request or revoke request would look like as non-executable metadata only.
3. A later milestone may decide whether an opt-in mock executor can consume those drafts.

This separation keeps v6.5 local and inert:

- no credential acquisition
- no request signing
- no authorization header generation
- no HTTP client creation
- no token persistence logic

## 3. Planned Conceptual Objects

v6.5 should plan these objects:

- `KiwoomMockOAuthDraftConfig`
- `KiwoomMockOAuthDraftInput`
- `KiwoomMockTokenRequestDraft`
- `KiwoomMockTokenRevokeDraft`
- `KiwoomMockTokenDraftPolicy`
- `KiwoomMockTokenDraftSafetyReport`
- `KiwoomMockTokenDraftGapReport`
- `KiwoomMockTokenDraftAuditRecord`

These are intentionally draft-level objects:

- they may contain documented endpoint paths
- they may contain field names
- they may contain redacted credential references
- they must not contain live token values
- they must not contain raw app key or secret key
- they must not contain executable transport/session objects

## 4. Input / Output Boundaries

### Allowed inputs

Only local, report-only artifacts may be referenced:

- v6.4 credential/environment boundary plan outputs
- local evidence-pack metadata
- local capability matrix metadata
- manually authored local draft fixtures

### Forbidden inputs

- environment variable values
- credential files
- secret stores
- live account data
- real token state
- real HTTP request objects
- real response payloads
- WebSocket handles

### Planned outputs

The draft layer may emit:

- token issue draft report
- token revoke draft report
- token draft safety report
- token draft gap report
- token draft audit record

The draft layer must not emit:

- usable bearer token
- authorization header
- executable request body for transport submission
- network-ready client configuration

## 5. Token Draft Object Model

### `KiwoomMockTokenRequestDraft`

Purpose: represent a non-executable draft for the documented `POST /oauth2/token` mock surface.

Required fields:

- draft id
- draft type: `TOKEN_ISSUE`
- documented method: `POST`
- documented path: `/oauth2/token`
- mock domain reference id
- production domain blocked marker
- mock-only marker
- KRX-only marker
- explicit opt-in required marker
- credential ref ids only
- documented request field names:
  - `grant_type`
  - `appkey`
  - `secretkey`
- documented response field names:
  - `expires_dt`
  - `token_type`
  - `token`
- request field presence policy by name only
- redaction policy id
- non-executable marker

Forbidden fields:

- raw `appkey`
- raw `secretkey`
- token value
- HTTP session/client
- URL string selected for execution
- headers containing secrets or bearer token

### `KiwoomMockTokenRevokeDraft`

Purpose: represent a non-executable draft for the documented `POST /oauth2/revoke` mock surface.

Required fields:

- draft id
- draft type: `TOKEN_REVOKE`
- documented method: `POST`
- documented path: `/oauth2/revoke`
- mock domain reference id
- production domain blocked marker
- explicit opt-in required marker
- credential ref ids only
- token ref policy id
- documented request field names:
  - `appkey`
  - `secretkey`
  - `token`
- response expectation policy
- non-executable marker

Forbidden fields:

- raw credentials
- live token string
- revoke-ready auth header
- executable HTTP request

## 6. OAuth Endpoint Metadata Policy

The evidence pack documents the same path shape on both production and mock domains. The design must prevent this from becoming ambiguous.

Rules:

- endpoint path metadata and domain policy must be separate objects
- draft objects may carry path metadata only
- domain selection must be resolved through the mock-only domain policy, not by free-form string
- production-domain metadata may be present only as blocked evidence for safety checks
- any future executor must fail closed unless the domain is exactly the mock domain and the execution mode is mock-only

This avoids the most dangerous mistake: a future developer reusing a correct path on the wrong domain.

## 7. Credential Reference Boundary For Token Drafts

v6.5 must inherit the v6.4 rule that credentials are referenced, never loaded.

Token draft-specific rules:

- `appkey` and `secretkey` may appear only as documented field names
- credential source is represented by `KiwoomMockCredentialRef` id only
- no raw value interpolation is allowed in draft artifacts
- no file path expansion
- no environment variable evaluation
- no fallback source probing

Allowed draft metadata:

- credential ref id
- source type label
- source alias label
- redaction status

Forbidden draft metadata:

- actual app key
- actual secret key
- raw account number
- token cache file path containing secrets

## 8. Grant Type And Request Field Policy

The evidence pack documents the token issue request fields `grant_type`, `appkey`, and `secretkey`.

v6.5 should plan a strict field policy:

- documented fields may be listed by name only
- unknown token request fields are rejected
- provider-specific custom extensions are rejected
- any order/account/trading field in a token draft is rejected
- any production marker in a token draft is rejected

Planned validation checks:

- required documented field names present in metadata
- no extra unsafe field names
- no secret values
- no broker/account/order payload bleed-through

## 9. Token Revoke Draft Boundary

The evidence pack documents `/oauth2/revoke` with fields `appkey`, `secretkey`, and `token`.

v6.5 must keep revoke drafts even more conservative than issue drafts:

- revoke drafts remain documentation-only
- revoke drafts must not imply a real token exists locally
- token reference must be represented symbolically, never by bearer value
- revoke drafts must be blocked if the input implies real token storage or loaded session state

This prevents v6.5 from becoming a hidden token lifecycle implementation.

## 10. Mock Domain Separation And KRX-Only Constraint

The local evidence states the mock domain is KRX-only. v6.5 should enforce that at the token-draft planning layer.

Rules:

- token drafts must be marked `mock_only=true`
- token drafts must carry `krx_only=true`
- token drafts must not represent overseas, derivatives, or multi-broker token scopes
- production domain execution remains blocked
- mixed-domain draft inputs must fail closed

This keeps a future executor from treating the mock token draft as a generic broker OAuth template.

## 11. Dry-Run Draft Mode Vs Future Executable Opt-In Mode

v6.5 must define a hard distinction between:

- `DRAFT_ONLY`
- `FUTURE_EXECUTABLE_OPT_IN`

### `DRAFT_ONLY`

- default mode
- local-only
- offline-only
- non-executable
- no credential loading
- no token issuance
- no revoke
- no network

### `FUTURE_EXECUTABLE_OPT_IN`

This mode is not implemented in v6.5. It exists only as a future policy target. It would still require:

- explicit operator opt-in
- mock-only environment resolution
- credential boundary passing
- domain policy passing
- safety guard passing
- separate milestone approval

v6.5 must never blur the two.

## 12. Secret Redaction And Draft Serialization Rules

Every v6.5 artifact must be safe to write to local JSON without leaking secrets.

Rules:

- serialize field names, never field values
- redact all credential identifiers beyond safe labels
- redact token references into non-reversible fingerprints if represented at all
- redact account identifiers completely or to policy-approved masked format
- reject drafts containing:
  - `Authorization`
  - `Bearer `
  - `appkey` values
  - `secretkey` values
  - full token strings

Allowed output examples:

- `credential_ref_id`
- `redaction_applied=true`
- `token_ref_present=false`
- `documented_request_fields=["grant_type","appkey","secretkey"]`

## 13. Token Storage And Lifetime Boundary

Even though v6.5 does not issue tokens, the design must define what it refuses to do.

Rules:

- no token storage implementation
- no refresh scheduler
- no token cache file
- no memory-held executable session token object
- no revoke-on-shutdown behavior

If a future milestone adds token execution, token lifetime policy must still be separate from token draft construction.

Planned draft metadata may include:

- documented token response field names
- documented expiration field name
- storage policy required flag

It must not include:

- actual token timestamp
- real expiration value
- refresh timer

## 14. Explicit Opt-In Gate

The token draft layer must depend on the v6.4 opt-in framework but remain denied by default.

Gate conditions for any future executable eligibility:

- mock-only environment selected
- explicit operator opt-in present
- production domain blocked
- credential boundary policy present
- token boundary policy present
- no live/prod markers
- no account/order/broker execution markers

Default outcome:

- `BLOCKED_DEFAULT`

Other planned outcomes:

- `BLOCKED_NO_OPT_IN`
- `BLOCKED_PRODUCTION_DOMAIN`
- `BLOCKED_CREDENTIAL_POLICY_MISSING`
- `BLOCKED_EXECUTABLE_MODE_NOT_ALLOWED_IN_V6_5`
- `DRAFT_ONLY_ALLOWED`

## 15. Safety Guard Design

Planned guard responsibilities:

1. Reject any raw credential material.
2. Reject any token value or authorization header.
3. Reject any environment-variable value ingestion.
4. Reject any file path that implies credential parsing.
5. Reject any executable URL or transport object.
6. Reject any production-domain selection.
7. Reject any WebSocket field.
8. Reject any account/order/broker/provider metadata.
9. Reject any LIVE/PROD marker.
10. Reject any cloud LLM or local LLM runtime field.
11. Reject any network execution marker.
12. Reject parquet source or export.

Unsafe marker examples the future guard should scan for:

- `Authorization`
- `Bearer`
- `access_token`
- `refresh_token`
- `requests.Session`
- `httpx.Client`
- `websocket`
- `api.kiwoom.com` selected as active execution domain
- `live`
- `prod`

## 16. Gap Taxonomy

Planned gap categories:

- `KIWOOM_MOCK_OAUTH_DRAFT_GENERATED`
- `KIWOOM_MOCK_OAUTH_DRAFT_ONLY`
- `KIWOOM_MOCK_OAUTH_LOCAL_ONLY`
- `KIWOOM_MOCK_OAUTH_OFFLINE_ONLY`
- `KIWOOM_MOCK_OAUTH_MISSING_INPUT`
- `KIWOOM_MOCK_OAUTH_MISSING_DOMAIN_POLICY`
- `KIWOOM_MOCK_OAUTH_MISSING_CREDENTIAL_BOUNDARY`
- `KIWOOM_MOCK_OAUTH_MISSING_OPT_IN_POLICY`
- `KIWOOM_MOCK_OAUTH_MISSING_TOKEN_BOUNDARY`
- `KIWOOM_MOCK_OAUTH_UNDOCUMENTED_FIELD_DETECTED`
- `KIWOOM_MOCK_OAUTH_RAW_CREDENTIAL_DETECTED`
- `KIWOOM_MOCK_OAUTH_TOKEN_VALUE_DETECTED`
- `KIWOOM_MOCK_OAUTH_AUTH_HEADER_DETECTED`
- `KIWOOM_MOCK_OAUTH_ENV_VALUE_INGESTION_DETECTED`
- `KIWOOM_MOCK_OAUTH_CREDENTIAL_FILE_REFERENCE_DETECTED`
- `KIWOOM_MOCK_OAUTH_EXECUTABLE_REQUEST_DETECTED`
- `KIWOOM_MOCK_OAUTH_PRODUCTION_DOMAIN_NOT_ALLOWED`
- `KIWOOM_MOCK_OAUTH_MOCK_DOMAIN_POLICY_MISSING`
- `KIWOOM_MOCK_OAUTH_WEBSOCKET_NOT_ALLOWED`
- `KIWOOM_MOCK_OAUTH_NETWORK_CALL_NOT_ALLOWED`
- `KIWOOM_MOCK_OAUTH_BROKER_ACCOUNT_ORDER_METADATA_NOT_ALLOWED`
- `KIWOOM_MOCK_OAUTH_LIVE_PROD_NOT_ALLOWED`
- `KIWOOM_MOCK_OAUTH_CLOUD_LLM_NOT_ALLOWED`
- `KIWOOM_MOCK_OAUTH_LOCAL_LLM_RUNTIME_NOT_ALLOWED`
- `KIWOOM_MOCK_OAUTH_PARQUET_NOT_ALLOWED`

## 17. Future CLI Shape

No CLI is implemented in v6.5, but future shape should stay narrow and report-only:

- `kiwoom-mock-oauth-token-draft-build --fixture-file ... [--output-file ...]`
- `kiwoom-mock-oauth-token-revoke-draft-report --fixture-file ... [--output-file ...]`
- `kiwoom-mock-oauth-token-safety-report --fixture-file ... [--output-file ...]`
- `kiwoom-mock-oauth-token-gap-report --fixture-file ... [--output-file ...]`

CLI rules for future implementation:

- local fixture files only
- draft-only output
- JSON output only
- no environment reads
- no credential loads
- no token issue/revoke execution
- no network transport creation

## 18. system_smoke Design

When implementation eventually exists, system smoke should confirm:

- `kiwoom_mock_oauth_draft_fixture_run=true`
- `kiwoom_mock_oauth_token_request_draft_generated=true`
- `kiwoom_mock_oauth_token_revoke_draft_generated=true`
- `kiwoom_mock_oauth_safety_report_generated=true`
- `kiwoom_mock_oauth_gap_report_generated=true`
- `kiwoom_mock_oauth_mock_only=true`
- `kiwoom_mock_oauth_draft_only=true`
- `kiwoom_mock_oauth_disabled_by_default=true`
- `kiwoom_mock_oauth_explicit_opt_in_required=true`
- `kiwoom_mock_oauth_no_credentials_loaded=true`
- `kiwoom_mock_oauth_no_env_read=true`
- `kiwoom_mock_oauth_no_token_issued=true`
- `kiwoom_mock_oauth_no_token_revoked=true`
- `kiwoom_mock_oauth_no_api_call=true`
- `kiwoom_mock_oauth_no_mockapi_call=true`
- `kiwoom_mock_oauth_no_websocket_connection=true`
- `kiwoom_mock_oauth_no_network_call=true`
- `kiwoom_mock_oauth_no_live_prod=true`
- `kiwoom_mock_oauth_parquet_unsupported=true`

## 19. Tests

Future implementation tests should cover:

- valid draft-only token request metadata
- valid draft-only revoke metadata
- production domain rejected
- raw credential material rejected
- token value rejected
- auth header rejected
- environment value ingestion rejected
- credential file reference rejected
- executable transport object rejected
- WebSocket marker rejected
- account/order/broker metadata rejected
- LIVE/PROD marker rejected
- parquet rejected
- KRX-only constraint preserved
- explicit opt-in still blocked by default

## 20. Non-Goals

- no Kiwoom API implementation
- no Kiwoom mockapi implementation
- no OAuth token request execution
- no OAuth token revoke execution
- no credential loading
- no environment variable reading
- no credential file parsing
- no authorization header generation
- no HTTP client creation
- no WebSocket connection
- no account query
- no order placement
- no live adapter
- no production broker path

## 21. Task-By-Task Execution Order

Recommended future execution order:

1. Define draft-only token boundary models and safety flags.
2. Define token draft guard and gap taxonomy.
3. Add local fixture loader for token draft fixtures.
4. Implement draft builder that emits non-executable issue/revoke draft reports only.
5. Add focused tests for raw-secret, token, domain, and execution-marker rejection.
6. Add CLI wiring for draft-only local reports.
7. Add system smoke coverage.
8. Only after all of the above, consider a separate design review for future executable mock-only opt-in work.

## 22. Success Criteria For v6.5 Design

v6.5 design is complete when:

- the repository has a clear non-executable plan for token issue/revoke drafts
- production and mock domains are explicitly separated
- credential references remain unloaded
- token values remain unrepresentable in draft artifacts
- explicit opt-in remains future-only and blocked by default
- no runtime network, OAuth, credential, broker, order, or live-trading path is introduced
