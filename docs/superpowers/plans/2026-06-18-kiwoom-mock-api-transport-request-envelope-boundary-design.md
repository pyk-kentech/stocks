# Kiwoom Mock API Transport / Request Envelope Boundary Design

> **For agentic workers:** v6.6 is design-only. Do not implement a Kiwoom mockapi caller, HTTP client, request execution, token usage, authorization header generation, account reads, order execution, WebSocket transport, or any network runtime path from this plan.

**Goal:** Define the local, non-executable transport and request-envelope boundary that must exist before any future Kiwoom mockapi request implementation can be considered, while keeping v6.6 strictly mock-only, transport-boundary-only, request-envelope-only, credential-ref-only, token-ref-only, disabled-by-default, offline-only, and free of any executable HTTP or network path.

**Authority:** Use only these local artifacts:

- `docs/superpowers/specs/2026-06-18-kiwoom-rest-api-official-evidence-pack.md`
- `docs/superpowers/specs/2026-06-18-kiwoom-rest-api-capability-matrix.json`
- `docs/superpowers/plans/2026-06-18-kiwoom-mock-credential-environment-boundary-design.md`
- `docs/superpowers/plans/2026-06-18-kiwoom-mock-oauth-token-draft-boundary-design.md`
- existing v6.3 Kiwoom mock adapter draft mapping files
- existing v6.4 credential boundary files
- existing v6.5 OAuth/token draft boundary files

**Core rule:** v6.6 does not create an HTTP client, does not create an HTTP session, does not execute requests, does not use OAuth tokens, does not generate authorization headers, does not call `https://mockapi.kiwoom.com`, does not call `https://api.kiwoom.com`, does not connect WebSocket, and does not create any live account or order path. It only designs the request-envelope and transport boundary required before a future mock-only executor could exist.

**Evidence anchors from local artifacts:**

- production REST domain: `https://api.kiwoom.com`
- mock REST domain: `https://mockapi.kiwoom.com`
- production WebSocket domain: `wss://api.kiwoom.com:10000`
- mock WebSocket domain: `wss://mockapi.kiwoom.com:10000`
- OAuth issue path: `/oauth2/token`
- OAuth revoke path: `/oauth2/revoke`
- mock remains KRX-only
- capability matrix still classifies executable OAuth and broker activity as not allowed now

**Safety flags planned for every v6.6 artifact:**

- `kiwoom_mock_api_transport_draft_only=true`
- `mock_only=true`
- `transport_boundary_only=true`
- `request_envelope_only=true`
- `credential_ref_only=true`
- `token_ref_only=true`
- `disabled_by_default=true`
- `explicit_opt_in_required=true`
- `local_file_only=true`
- `offline_only=true`
- `non_executable=true`
- `no_environment_read=true`
- `no_credential_file_read=true`
- `no_credentials_loaded=true`
- `no_raw_secret_values=true`
- `no_authorization_header_generated=true`
- `no_token_loaded=true`
- `no_token_used=true`
- `no_token_refreshed=true`
- `no_http_client_created=true`
- `no_http_session_created=true`
- `no_api_call=true`
- `no_mockapi_call=true`
- `no_websocket_connection=true`
- `no_network_call=true`
- `no_real_order=true`
- `no_live_trading=true`
- `no_live_prod=true`
- `no_account_read=true`
- `no_account_mutation=true`
- `no_production_domain_execution=true`
- `no_cloud_llm=true`
- `no_local_llm_runtime=true`

## 1. Why Transport / Request-Envelope Boundary Is Required Before Mockapi Execution

v6.3 established draft mapping from internal paper objects to Kiwoom mock-facing draft structures. v6.4 established credential and environment boundaries. v6.5 established OAuth/token request drafts. None of those layers yet answers the next dangerous question: what is the safe shape of a mockapi request envelope before transport exists.

Without a dedicated v6.6 boundary, future work would risk mixing:

- safe documented endpoint metadata with executable request envelopes
- token references with usable token values
- header drafts with real authorization headers
- envelope assembly with HTTP client creation
- mock-only request shape with production-domain drift

That gap is exactly where “draft-only” systems accidentally become transport implementations. v6.6 has to close that gap by making request envelope structure explicit while still blocking every step that would turn structure into execution.

## 2. Relationship To v6.3 Kiwoom Mock Adapter Draft Mapping

v6.3 draft mapping is the upstream domain-specific layer. It converts broker-mock-aligned paper objects into Kiwoom-oriented request/response draft structures, but it intentionally stops at Kiwoom draft semantics.

v6.6 should sit below v6.3:

- v6.3 decides which endpoint evidence ref a draft maps to
- v6.3 decides which documented request fields matter for a given mock draft
- v6.6 decides how those documented pieces may be arranged into a non-executable request envelope draft

Separation rule:

- v6.3 remains business mapping
- v6.6 remains transport-envelope design
- neither layer may execute requests

This allows future work to change transport internals without changing v6.3 draft semantics, and to change mapping logic without changing v6.6 envelope safety rules.

## 3. Relationship To v6.4 Credential / Environment Boundary

v6.4 defines where credential references come from, how mock vs production environments differ, and how explicit opt-in remains blocked by default.

v6.6 must inherit these rules without re-implementing them:

- credentials remain references only
- environment selection remains symbolic only
- production domain remains blocked
- explicit opt-in remains required for any future executable path

Transport-envelope artifacts may carry:

- credential reference ids
- environment policy ids
- domain policy ids

They must not carry:

- loaded credential values
- environment variable values
- credential file contents

## 4. Relationship To v6.5 OAuth / Token Draft Boundary

v6.5 defines non-executable drafts for OAuth issue/revoke metadata and token lifecycle policy. v6.6 must not bypass that boundary.

v6.6 inherits:

- token-reference-only policy
- no authorization header generation
- no token loading
- no token refresh
- no token storage

v6.6 adds one lower-level distinction:

- token draft metadata may exist
- request envelope may contain a symbolic token reference slot
- no resolved bearer token may ever appear

This keeps token semantics and transport semantics separate.

## 5. Mock-Domain-Only Request Envelope Policy

Every request envelope draft must be pinned to the documented mock REST domain only:

- allowed domain: `https://mockapi.kiwoom.com`
- production domain remains blocked evidence metadata only
- no free-form domain override
- no environment-driven domain selection in v6.6

Planned object:

- `KiwoomMockApiTransportPolicy`

Required fields:

- transport policy id
- allowed mock REST domain
- forbidden production REST domain
- KRX-only marker
- disabled-by-default marker
- explicit-opt-in-required marker

## 6. Production-Domain Execution Block

v6.6 must explicitly preserve the rule that even a perfectly correct path and method become unsafe when paired with `https://api.kiwoom.com`.

Planned rule set:

- production REST domain may appear only as blocked evidence
- production domain may never become an active request envelope target
- any envelope draft that resolves to production must fail closed
- any mixed mock/prod domain metadata in the same envelope draft must fail closed

The transport boundary must make this impossible to “accidentally” opt into.

## 7. Endpoint Evidence Reference Policy

The request envelope layer must not invent endpoints. It should reference documented endpoints from the evidence pack and capability matrix.

Planned object:

- `KiwoomMockApiEndpointEvidenceRef`

Required fields:

- endpoint evidence ref id
- source evidence document id
- documented API id if available
- documented path
- documented category
- documented mock support marker
- documented KRX-only note
- evidence-only marker

Rules:

- endpoint refs are references, not executable routes
- endpoint refs must be matched against documented mock-supported entries only
- undocumented endpoints are rejected

## 8. HTTP Method Reference Policy

The method must remain documented metadata, not a transport capability.

Rules:

- method is represented as an allowed documented verb string only
- no transport object may be derived from method alone
- method and endpoint path must remain paired through evidence ref validation
- unsupported or undocumented methods are rejected

This keeps `POST` as evidence metadata, not as the first step toward a live request.

## 9. Header Draft Policy

Planned object:

- `KiwoomMockApiHeaderDraft`

Allowed header draft content:

- documented header names only
- required/optional classification
- value source classification:
  - literal-safe
  - credential-ref
  - token-ref
  - future-generated-but-blocked

Forbidden header draft content:

- authorization header value
- bearer token
- raw app key
- raw secret key
- cookies
- session-bound transport metadata

## 10. Authorization Header Non-Generation Policy

This is a hard boundary, not a best effort.

Rules:

- `Authorization` may be represented only as a blocked header concept
- no bearer value may be formed
- no “preview” authorization header may be produced
- no signing function may exist in v6.6
- no request serializer may inject a secret-derived header

The future executor, if it ever exists, must be built in a later milestone under a distinct design.

## 11. Token-Reference-Only Policy

Planned rule:

- transport-envelope artifacts may carry a token reference id only
- token reference id must be symbolic and redacted
- no token string may appear in serialized drafts
- no token resolution may occur in v6.6

This keeps v6.6 dependent on v6.5 policy without consuming or materializing tokens.

## 12. Credential-Reference-Only Policy

The same rule applies to app key and secret key semantics.

Allowed:

- credential ref ids
- source class labels
- redaction status

Forbidden:

- raw app key
- raw secret key
- any field that implies credentials were loaded
- any fallback probing of local credential sources

## 13. Request Body Draft Policy

Planned object:

- `KiwoomMockApiBodyDraft`

Rules:

- request body fields are represented by documented field names and safe draft values only
- safe values may include:
  - literal-safe strings
  - numbers
  - booleans
  - symbolic refs
  - placeholder policy markers
- unsafe values are rejected:
  - raw secrets
  - tokens
  - account numbers
  - transport handles

The body draft should remain serializable as a local report, not as a network-ready payload.

## 14. Query / Path Parameter Draft Policy

Planned objects:

- `KiwoomMockApiQueryParamDraft`
- `KiwoomMockApiPathParamDraft`

Rules:

- path and query parameters may exist only when documented in evidence
- params may use only safe literal or symbolic reference values
- params must not carry account identifiers, secret values, or runtime transport metadata
- path template substitution must remain conceptual only

## 15. Redaction Policy

Every transport-envelope artifact must assume logs and JSON outputs are visible.

Mandatory rules:

- redact all credential-derived slots
- redact all token-derived slots
- redact account identifiers
- never serialize full header values for blocked secret-bearing headers
- preserve only fingerprints, ref ids, or safe markers

Allowed output examples:

- `header_name="authorization"`
- `value_source="TOKEN_REF_BLOCKED"`
- `redaction_applied=true`

## 16. Raw Secret / Token / Account / Auth Marker Rejection Policy

The safety guard must reject both field names and string values that imply unsafe execution.

Reject at minimum:

- `appkey` value content
- `secretkey` value content
- `access_token`
- `refresh_token`
- `Authorization`
- `Bearer`
- full account number fields
- cookies
- session ids

This rejection must apply recursively through dict keys, dict values, list contents, and free text metadata.

## 17. Network Transport Non-Goal

v6.6 must not create:

- TCP transport
- HTTP transport
- retrying sender
- socket layer
- DNS resolution path

Representation of transport policy is allowed. Transport implementation is not.

## 18. HTTP Client / Session Non-Goal

v6.6 must not create:

- `requests.Session`
- `httpx.Client`
- `aiohttp` session
- pooled transport
- persistent connection manager

It may only describe future requirements for those objects as blocked capabilities.

## 19. Retry / Timeout / Rate-Limit Representation-Only Policy

Planned object:

- `KiwoomMockApiRetryTimeoutPolicy`

Allowed:

- timeout class metadata
- retry class metadata
- official rate-limit note references
- fail-closed markers

Forbidden:

- timers
- retry loops
- sleeping/backoff code
- live rate-limit counters

This policy should remain advisory metadata only.

## 20. Error Response Draft Policy

Planned object:

- `KiwoomMockApiErrorResponseDraft`

Purpose:

- represent documented error response shape
- preserve error-code evidence mapping
- support report-only review of blocked or unresolved outcomes

Rules:

- no live response capture
- no transport exception wrapping
- no retry-trigger integration
- no credential leakage in error drafts

## 21. Audit Record Policy

Planned object:

- `KiwoomMockApiTransportAuditRecord`

Audit records must capture:

- source evidence refs
- envelope draft id
- policy ids consulted
- redaction applied marker
- non-executable marker
- blocked capability markers

Audit records must not capture:

- raw secrets
- token values
- real account identifiers
- client/session objects

## 22. Safety Guard Design

The v6.6 guard should reject:

- production-domain targets
- raw credentials
- raw tokens
- authorization header values
- account identifiers
- HTTP client/session markers
- network transport markers
- API/mockapi/WebSocket execution markers
- LIVE/PROD markers
- broker/account/order execution markers
- cloud LLM / local runtime markers
- parquet source or export markers

It must also validate:

- documented endpoint evidence ref exists
- method/path pairing is documented
- token refs are symbolic only
- credential refs are symbolic only

## 23. Gap Taxonomy

Planned gap categories:

- `KIWOOM_MOCK_API_TRANSPORT_DRAFT_GENERATED`
- `KIWOOM_MOCK_API_TRANSPORT_DRAFT_ONLY`
- `KIWOOM_MOCK_API_TRANSPORT_LOCAL_ONLY`
- `KIWOOM_MOCK_API_TRANSPORT_OFFLINE_ONLY`
- `KIWOOM_MOCK_API_TRANSPORT_DISABLED_BY_DEFAULT`
- `KIWOOM_MOCK_API_TRANSPORT_EXPLICIT_OPT_IN_REQUIRED`
- `KIWOOM_MOCK_API_TRANSPORT_MISSING_INPUT`
- `KIWOOM_MOCK_API_TRANSPORT_MISSING_ENDPOINT_EVIDENCE_REF`
- `KIWOOM_MOCK_API_TRANSPORT_MISSING_TRANSPORT_POLICY`
- `KIWOOM_MOCK_API_TRANSPORT_MISSING_RETRY_TIMEOUT_POLICY`
- `KIWOOM_MOCK_API_TRANSPORT_PRODUCTION_DOMAIN_NOT_ALLOWED`
- `KIWOOM_MOCK_API_TRANSPORT_UNDOCUMENTED_METHOD`
- `KIWOOM_MOCK_API_TRANSPORT_UNDOCUMENTED_PATH`
- `KIWOOM_MOCK_API_TRANSPORT_AUTH_HEADER_NOT_ALLOWED`
- `KIWOOM_MOCK_API_TRANSPORT_RAW_CREDENTIAL_DETECTED`
- `KIWOOM_MOCK_API_TRANSPORT_RAW_TOKEN_DETECTED`
- `KIWOOM_MOCK_API_TRANSPORT_ACCOUNT_IDENTIFIER_NOT_ALLOWED`
- `KIWOOM_MOCK_API_TRANSPORT_HTTP_CLIENT_NOT_ALLOWED`
- `KIWOOM_MOCK_API_TRANSPORT_HTTP_SESSION_NOT_ALLOWED`
- `KIWOOM_MOCK_API_TRANSPORT_API_CALL_NOT_ALLOWED`
- `KIWOOM_MOCK_API_TRANSPORT_MOCKAPI_CALL_NOT_ALLOWED`
- `KIWOOM_MOCK_API_TRANSPORT_WEBSOCKET_NOT_ALLOWED`
- `KIWOOM_MOCK_API_TRANSPORT_NETWORK_CALL_NOT_ALLOWED`
- `KIWOOM_MOCK_API_TRANSPORT_LIVE_PROD_NOT_ALLOWED`
- `KIWOOM_MOCK_API_TRANSPORT_CLOUD_LLM_NOT_ALLOWED`
- `KIWOOM_MOCK_API_TRANSPORT_LOCAL_LLM_RUNTIME_NOT_ALLOWED`
- `KIWOOM_MOCK_API_TRANSPORT_PARQUET_NOT_ALLOWED`

## 24. Future CLI Shape

No CLI is implemented in v6.6, but future commands should remain report-only:

- `kiwoom-mock-api-request-envelope-draft --fixture-file ... [--output-file ...]`
- `kiwoom-mock-api-header-draft-report --fixture-file ... [--output-file ...]`
- `kiwoom-mock-api-body-draft-report --fixture-file ... [--output-file ...]`
- `kiwoom-mock-api-transport-safety-report --fixture-file ... [--output-file ...]`
- `kiwoom-mock-api-transport-gap-report --fixture-file ... [--output-file ...]`

Rules:

- local fixture input only
- JSON output only
- no env reads
- no credential loads
- no token use
- no HTTP client/session creation
- no request execution

## 25. system_smoke Design

Future system smoke should confirm:

- `kiwoom_mock_api_transport_fixture_run=true`
- `kiwoom_mock_api_request_envelope_draft_generated=true`
- `kiwoom_mock_api_header_draft_generated=true`
- `kiwoom_mock_api_body_draft_generated=true`
- `kiwoom_mock_api_transport_policy_generated=true`
- `kiwoom_mock_api_retry_timeout_policy_generated=true`
- `kiwoom_mock_api_error_response_draft_generated=true`
- `kiwoom_mock_api_transport_safety_report_generated=true`
- `kiwoom_mock_api_transport_gap_report_generated=true`
- `kiwoom_mock_api_transport_audit_record_generated=true`
- `kiwoom_mock_api_transport_draft_only=true`
- `kiwoom_mock_api_mock_only=true`
- `kiwoom_mock_api_request_envelope_only=true`
- `kiwoom_mock_api_credential_ref_only=true`
- `kiwoom_mock_api_token_ref_only=true`
- `kiwoom_mock_api_local_only=true`
- `kiwoom_mock_api_offline_only=true`
- `kiwoom_mock_api_non_executable=true`
- `kiwoom_mock_api_no_env_read=true`
- `kiwoom_mock_api_no_credential_file_read=true`
- `kiwoom_mock_api_no_credentials_loaded=true`
- `kiwoom_mock_api_no_raw_secret_values=true`
- `kiwoom_mock_api_no_authorization_header_generated=true`
- `kiwoom_mock_api_no_token_loaded=true`
- `kiwoom_mock_api_no_token_used=true`
- `kiwoom_mock_api_no_token_refreshed=true`
- `kiwoom_mock_api_no_http_client_created=true`
- `kiwoom_mock_api_no_http_session_created=true`
- `kiwoom_mock_api_no_api_call=true`
- `kiwoom_mock_api_no_mockapi_call=true`
- `kiwoom_mock_api_no_websocket_connection=true`
- `kiwoom_mock_api_no_network_call=true`
- `kiwoom_mock_api_no_live_prod=true`
- `kiwoom_mock_api_parquet_unsupported=true`

## 26. Tests

Future implementation tests should cover:

- valid mock-only request envelope draft construction
- documented endpoint evidence ref acceptance
- undocumented endpoint rejection
- production-domain rejection
- raw credential rejection
- raw token rejection
- authorization header rejection
- account identifier rejection
- HTTP client/session marker rejection
- API/mockapi/WebSocket/network marker rejection
- retry/timeout policy remains representation-only
- error response draft remains report-only
- audit record remains redacted
- parquet rejection

## 27. Phased Execution Order

Recommended execution order:

1. Define transport-boundary models and safety flags.
2. Define guard and gap taxonomy for envelope/header/body validation.
3. Add local JSON fixture loader.
4. Implement draft-only envelope builder and transport policy evaluator.
5. Add focused tests for domain, header, token-ref, credential-ref, and HTTP-client rejection.
6. Add CLI wiring for local report-only transport drafts.
7. Add system smoke coverage.
8. Only after all of the above, consider a separate design review for future mock-only request execution.

## Success Criteria For v6.6 Design

v6.6 design is complete when:

- request envelope shape is explicitly defined without becoming executable
- v6.3, v6.4, and v6.5 boundaries remain distinct and composable
- mock-domain-only policy is explicit
- production-domain execution remains impossible
- credential and token references remain unresolved
- no HTTP client, session, transport, API call, mockapi call, or network path is introduced
