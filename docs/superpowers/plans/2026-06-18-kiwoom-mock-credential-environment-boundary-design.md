# Kiwoom Mock Credential And Environment Boundary Design

> **For agentic workers:** v6.4 is design-only. Do not implement credential loading, token issuance, token revoke, API execution, WebSocket transport, order execution, account mutation, or live trading from this plan.

**Goal:** Define the credential, environment, domain, and explicit opt-in safety boundary that must exist before any future Kiwoom mock REST execution can be considered, while keeping v6.4 strictly design-only, mock-only, disabled-by-default, non-executable, and free of any credential or network runtime path.

**Authority:** Use only the local evidence pack and capability matrix:

- `docs/superpowers/specs/2026-06-18-kiwoom-rest-api-official-evidence-pack.md`
- `docs/superpowers/specs/2026-06-18-kiwoom-rest-api-capability-matrix.json`

**Core rule:** v6.4 does not execute OAuth, does not load credentials, does not call `https://mockapi.kiwoom.com`, does not call `https://api.kiwoom.com`, does not connect WebSocket, and does not create any order path. It only designs the boundary required before a future opt-in mock executor could exist.

**Safety flags planned for every v6.4 boundary artifact:**

- `mock_only=true`
- `credential_boundary_only=true`
- `disabled_by_default=true`
- `explicit_opt_in_required=true`
- `no_credentials_loaded=true`
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

---

## 1. Why Credential / Environment Boundary Is Required Before Mockapi Execution

The local v6.3 draft layer proves schema mapping only. It intentionally avoids the dangerous parts:

- deciding which domain is safe to call
- deciding when credential material may be referenced
- deciding when OAuth surfaces are even eligible
- deciding whether an operator explicitly opted into mock-only execution
- preventing production-domain drift

Without a dedicated boundary, future mock execution work would risk mixing:

- production and mock domains
- credential references and loaded secrets
- dry-run draft mapping and executable request intent
- mock-safe order flow and real broker semantics

The boundary therefore has to exist before any execution implementation so the repo can fail closed on environment, credentials, domains, and opt-in state rather than relying on later executor behavior.

## 2. Production Vs Mock Domain Separation

The evidence pack documents:

- production REST domain: `https://api.kiwoom.com`
- mock REST domain: `https://mockapi.kiwoom.com`
- production WebSocket domain: `wss://api.kiwoom.com:10000`
- mock WebSocket domain: `wss://mockapi.kiwoom.com:10000`
- mock is KRX-only

Planned rule set:

- production and mock domains must be represented as separate policy objects, not string literals scattered across code
- production domain execution remains blocked in all v6.x planning stages unless an explicitly separate production design exists
- v6.4 boundary artifacts may reference documented domains as evidence metadata only
- any future executable path must fail closed if the selected domain is not exactly the allowed mock domain for the chosen execution mode

Planned conceptual object:

- `KiwoomMockDomainPolicy`

Required fields:

- policy id
- allowed mock REST domain
- forbidden production REST domain
- allowed mock WebSocket domain as future-only metadata
- forbidden production WebSocket domain
- KRX-only marker
- disabled-by-default marker

## 3. OAuth Token Issue / Revoke Boundary

The evidence pack shows `/oauth2/token` and `/oauth2/revoke` as documented surfaces, and the capability matrix marks them as not allowed in the current stage.

v6.4 must keep OAuth at the boundary-design level only:

- token issue and revoke are represented as forbidden runtime actions in this stage
- future execution planning must separate “credential reference exists” from “token request is permitted”
- token issuance eligibility must require explicit mock-only opt-in and must still remain disabled until a later implementation milestone

Planned conceptual object:

- `KiwoomMockTokenBoundary`

Required fields:

- token boundary id
- documented issue endpoint path
- documented revoke endpoint path
- issue allowed now flag: false
- revoke allowed now flag: false
- execution mode requirement
- explicit opt-in requirement
- no-token-issued marker
- no-token-revoked marker

## 4. Credential Source Boundary

Future execution may need to know where credentials would come from, but v6.4 must not load them.

Planned source categories:

- environment-variable reference only
- local encrypted secret store reference only
- local manual operator input reference only
- disabled / absent

Boundary rules:

- the system may carry a credential reference object, not raw secret material
- no credential file parsing in v6.4
- no environment variable reading in v6.4
- no secret manager client in v6.4
- no fallback probing of multiple sources

Planned conceptual object:

- `KiwoomMockCredentialRef`

Required fields:

- credential ref id
- source type enum
- source label
- environment name or file label as metadata only
- mock-only allowed flag
- loaded flag: false
- secret material present flag: false

## 5. Environment Variable Naming Policy

The plan should reserve a future naming policy without reading any variable now.

Policy principles:

- mock-only names must be distinct from future production names
- names must clearly include `KIWOOM_MOCK`
- no aliasing from generic `APP_KEY`, `SECRET`, or ambiguous broker-wide names
- variable names for references and variable names for loaded values must be conceptually separate

Recommended future shape:

- `KIWOOM_MOCK_APP_KEY_REF`
- `KIWOOM_MOCK_SECRET_KEY_REF`
- `KIWOOM_MOCK_ACCOUNT_REF`
- `KIWOOM_MOCK_ENVIRONMENT`
- `KIWOOM_MOCK_EXPLICIT_OPT_IN`

Forbidden future naming patterns:

- `KIWOOM_APP_KEY`
- `BROKER_APP_KEY`
- `API_TOKEN`
- `SECRET_KEY`
- any name shared between mock and production modes

## 6. Secret Redaction Rules

All v6.4 boundary artifacts must assume that future logging and report surfaces are hostile unless explicitly redacted.

Mandatory redaction policy:

- never serialize raw app key
- never serialize raw secret key
- never serialize OAuth access token
- never serialize authorization header
- never serialize full account number
- never serialize future refresh token if such a thing exists later

Allowed representations:

- masked last-4 or prefix-only fingerprints
- stable non-reversible hash or digest label
- redaction reason code
- source reference id

Planned reports must state whether redaction occurred and why, without carrying the sensitive value itself.

## 7. Explicit Opt-In Gate

The key transition between dry-run design and any future mock execution is not credentials; it is explicit operator intent.

Planned conceptual object:

- `KiwoomMockOptInGate`

Required gate conditions:

- mock-only environment selected
- operator explicitly requested mock execution mode
- domain policy resolved to mock domain only
- credential boundary policy present
- token boundary policy present
- account identifier policy validated
- dry-run and executable modes distinguished

Default gate state:

- denied

Planned gate outputs:

- `BLOCKED_DEFAULT`
- `BLOCKED_NO_EXPLICIT_OPT_IN`
- `BLOCKED_DOMAIN_POLICY`
- `BLOCKED_CREDENTIAL_POLICY`
- `BLOCKED_TOKEN_POLICY`
- `BLOCKED_ACCOUNT_POLICY`
- `FUTURE_ELIGIBLE_BUT_DISABLED`

## 8. Mock-Only Execution Gate

This is separate from the generic opt-in gate. Even if a user explicitly opts in, the future path must still prove it is mock-only.

Required checks:

- selected environment is mock
- selected REST domain equals `https://mockapi.kiwoom.com`
- no production domain fallback exists
- no live/prod marker is set
- future WebSocket path remains disabled unless separately approved
- KRX-only constraint is satisfied

Planned conceptual object:

- `KiwoomMockExecutionMode`

Allowed future enum concepts:

- `KIWOOM_MOCK_DRY_RUN`
- `KIWOOM_MOCK_OPT_IN_EXECUTION_FUTURE`
- `KIWOOM_MOCK_DISABLED`

v6.4 rule:

- all modes remain non-executable in practice

## 9. KRX-Only Constraint Handling

The evidence pack states mock is KRX-only. That constraint must be promoted from comment-level metadata into a hard policy rule.

Policy:

- any non-KRX market selection is blocked before any credential or token concern
- KRX-only must be checked at config validation time and at future execution gate time
- symbol, market profile, and strategy track must all remain consistent with domestic KRX usage

Planned gap behavior:

- explicit blocking gap for non-KRX usage
- explicit report-only warning if the market is ambiguous rather than silently coerced

## 10. Account Identifier Handling Policy

Account identifiers are sensitive even if they are not secrets in the same way as keys.

Rules:

- no real account identifier loading in v6.4
- no real account existence check
- no account query
- no account mutation
- if account identifiers are referenced, they must be carried only as masked references or fingerprints
- no draft, report, or audit artifact may store a full raw account number

Planned policy split:

- account ref presence policy
- account masking policy
- account-usage eligibility policy

## 11. Token Storage Policy

v6.4 does not store tokens because v6.4 does not issue tokens. The plan still needs the future rules.

Future storage rules:

- no token persistence in repo fixtures
- no token persistence in tracked files
- no token persistence in JSON reports
- no token persistence in SQLite unless a later dedicated design explicitly approves encrypted storage
- no token in CLI stdout
- no token in audit records

If a later version needs temporary token state, it should use an isolated runtime-only container with explicit expiry metadata and zero serialization into general reports.

## 12. Token Lifetime / Refresh Policy

Token lifecycle handling must remain blocked until a later implementation stage.

Future design constraints:

- token expiration metadata may be tracked as non-secret boundary metadata
- token refresh should not be assumed to exist unless the official evidence explicitly supports it
- auto-refresh must be disabled by default
- any future refresh path requires its own explicit opt-in and audit

v6.4 design stance:

- no refresh implementation
- no background renewal
- no scheduled token maintenance

## 13. Dry-Run Vs Opt-In Mock Execution Distinction

This distinction is the center of v6.4.

Dry-run:

- local-only
- no credential loading
- no token handling
- no domain execution
- no transport
- safe for fixtures and smoke

Future opt-in mock execution:

- still mock-only
- still blocked in v6.4
- may later allow controlled credential reference resolution and token request logic
- must remain separate from dry-run models and CLI paths

Design rule:

- do not overload the current v6.3 draft CLI or draft models with future executable semantics
- future opt-in mock execution must use distinct config and gate objects

## 14. Safety Guard Design

Planned guard responsibility:

- reject any production domain marker
- reject any live/prod marker
- reject any raw credential material
- reject any token string
- reject any authorization header generation field
- reject any network client or transport object
- reject any WebSocket connection marker
- reject any account mutation marker
- reject any real order marker
- reject any broker live adapter marker
- reject any cloud LLM or local LLM runtime marker
- reject parquet sources or exports

Planned conceptual reports:

- `KiwoomMockCredentialSafetyReport`
- `KiwoomMockCredentialGapReport`
- `KiwoomMockCredentialAuditRecord`

## 15. Gap Taxonomy

Required planned gap categories:

- `KIWOOM_MOCK_CREDENTIAL_BOUNDARY_DEFINED`
- `KIWOOM_MOCK_ENVIRONMENT_UNSPECIFIED`
- `KIWOOM_MOCK_ENVIRONMENT_NOT_MOCK`
- `KIWOOM_MOCK_DOMAIN_POLICY_MISSING`
- `KIWOOM_MOCK_PRODUCTION_DOMAIN_NOT_ALLOWED`
- `KIWOOM_MOCK_KRX_ONLY_REQUIRED`
- `KIWOOM_MOCK_CREDENTIAL_REF_MISSING`
- `KIWOOM_MOCK_RAW_CREDENTIAL_NOT_ALLOWED`
- `KIWOOM_MOCK_TOKEN_BOUNDARY_MISSING`
- `KIWOOM_MOCK_TOKEN_ISSUE_NOT_ALLOWED`
- `KIWOOM_MOCK_TOKEN_REVOKE_NOT_ALLOWED`
- `KIWOOM_MOCK_TOKEN_STORAGE_NOT_ALLOWED`
- `KIWOOM_MOCK_AUTH_HEADER_NOT_ALLOWED`
- `KIWOOM_MOCK_ACCOUNT_IDENTIFIER_POLICY_MISSING`
- `KIWOOM_MOCK_RAW_ACCOUNT_IDENTIFIER_NOT_ALLOWED`
- `KIWOOM_MOCK_EXPLICIT_OPT_IN_MISSING`
- `KIWOOM_MOCK_EXECUTION_MODE_DISABLED`
- `KIWOOM_MOCK_NETWORK_CALL_NOT_ALLOWED`
- `KIWOOM_MOCK_API_CALL_NOT_ALLOWED`
- `KIWOOM_MOCK_MOCKAPI_CALL_NOT_ALLOWED`
- `KIWOOM_MOCK_WEBSOCKET_NOT_ALLOWED`
- `KIWOOM_MOCK_REAL_ORDER_NOT_ALLOWED`
- `KIWOOM_MOCK_LIVE_TRADING_NOT_ALLOWED`
- `KIWOOM_MOCK_LIVE_PROD_NOT_ALLOWED`
- `KIWOOM_MOCK_ACCOUNT_MUTATION_NOT_ALLOWED`
- `KIWOOM_MOCK_CLOUD_LLM_NOT_ALLOWED`
- `KIWOOM_MOCK_LOCAL_LLM_RUNTIME_NOT_ALLOWED`
- `KIWOOM_MOCK_PARQUET_NOT_ALLOWED`

## 16. Future CLI Shape

v6.4 adds no CLI implementation. Future command shapes should remain split between dry-run-safe reporting and later opt-in execution gating.

Recommended future report-only commands:

- `kiwoom-mock-credential-boundary-report --fixture-file ...`
- `kiwoom-mock-environment-policy-report --fixture-file ...`
- `kiwoom-mock-opt-in-gate-report --fixture-file ...`
- `kiwoom-mock-credential-safety-report --fixture-file ...`
- `kiwoom-mock-credential-gap-report --fixture-file ...`

Future execution-adjacent commands, deferred beyond v6.4:

- `kiwoom-mock-token-plan`
- `kiwoom-mock-execution-plan`

Deferred rule:

- any future command that sounds executable must still be planning/report-only until a later milestone explicitly authorizes implementation

## 17. system_smoke Design

v6.4 design does not change runtime smoke now, but the future smoke target should validate:

- boundary fixture parsed locally
- mock environment policy generated
- credential ref remains unloaded
- token boundary remains non-executed
- explicit opt-in gate defaults to blocked
- production domain remains rejected
- KRX-only rule enforced
- no token issued
- no token revoked
- no API call
- no mockapi call
- no WebSocket connection
- no network runtime path
- no real order
- no live/prod
- parquet unsupported

## 18. Tests

Future implementation-phase tests should cover:

- mock vs production domain separation
- raw credential rejection
- token string rejection
- authorization header field rejection
- account identifier masking enforcement
- opt-in gate blocked by default
- KRX-only mismatch rejection
- environment variable naming validation
- dry-run vs future execution mode separation
- smoke proof that no network/API/WebSocket paths are exercised

## 19. Non-Goals

- no Kiwoom API implementation
- no Kiwoom mockapi implementation
- no OAuth token request execution
- no credential file parsing
- no environment variable reading
- no order placement
- no account query
- no WebSocket connection
- no live adapter
- no production broker path

## 20. Task-By-Task Execution Order

Recommended future execution order:

1. Add `KiwoomMockCredentialBoundaryConfig`, `KiwoomMockEnvironment`, `KiwoomMockCredentialRef`, `KiwoomMockTokenBoundary`, `KiwoomMockDomainPolicy`, `KiwoomMockOptInGate`, `KiwoomMockExecutionMode`, and report/gap/audit models.
2. Add fixture-only loader and static validation for environment/domain/credential reference metadata.
3. Add safety guard and complete gap taxonomy.
4. Add boundary engine that evaluates environment/domain/opt-in state without reading secrets or issuing tokens.
5. Add report-only CLI commands for credential/environment/opt-in boundary inspection.
6. Add `system_smoke` coverage proving blocked-by-default behavior and zero network activity.
7. Only after that, create a later design milestone for token planning and an even later one for any opt-in mock execution implementation.

## Scope Summary

v6.4 is the policy wall between v6.3 draft mapping and any later mock execution work. It must preserve:

- strict separation between mock and production domains
- strict separation between credential references and loaded secret material
- strict separation between dry-run mapping and executable behavior
- strict blocked-by-default posture for OAuth, mockapi, WebSocket, and account-sensitive paths
