# v6.8 Kiwoom Mock OAuth Execution Adapter

## Goal

Implement the first tightly scoped executable boundary for Kiwoom mock OAuth token issue and revoke.

## Scope

- Mock domain only: `https://mockapi.kiwoom.com`
- OAuth token request execution
- OAuth token revoke execution
- Explicit CLI opt-in only
- Redacted output only
- In-memory token handling only
- Mocked transport in tests and smoke

## Still Blocked

- Production domain
- Account, order, quote, and websocket APIs
- LIVE/PROD
- Token refresh
- Token persistence
- Raw secret/token/account logging
- Non-OAuth authorization header reuse
- Cloud or local LLM runtime
- Parquet

## Credential Policy

- Environment variable reads are allowed only in explicit execution mode
- Only `KIWOOM_MOCK_APP_KEY` and `KIWOOM_MOCK_SECRET_KEY` are accepted
- Production credential names remain blocked
- Missing credentials fail closed with redacted errors

## Execution Policy

- Execution commands require `--mock-domain`, `--execute`, and `--acknowledge-mock-oauth-execution`
- Default mode remains disabled
- HTTP transport is injectable for tests and smoke
- Real network execution is never used in tests or smoke

## Output Policy

- Token results are redacted
- Tokens are in-memory only
- No token persistence
- Audit records stay redacted
