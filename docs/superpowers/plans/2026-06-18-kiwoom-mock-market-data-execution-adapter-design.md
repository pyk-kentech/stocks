# v6.9 Kiwoom Mock Read-only Market Data Execution Adapter

## Goal

Implement tightly scoped mock-domain read-only market-data execution capability.

## Scope

- Mock domain only: `https://mockapi.kiwoom.com`
- Read-only market-data request capability only
- Quote and market-condition drafts only
- v6.7 preflight `DRAFT_READY` dependency required
- Explicit CLI opt-in only
- Mocked transport in tests and smoke
- Redacted and sanitized output only

## Blocked Paths

- Production domain
- Account read
- Order
- WebSocket
- LIVE/PROD
- Token refresh
- Token persistence
- Raw secret/token/account output
- Autonomous trading
- Cloud and local LLM
- Parquet

## Token Policy

- Token is accepted only as in-memory execution input
- No token persistence
- No token refresh
- No raw token in logs, reports, or audit records

## Output Policy

- Sanitized response object only
- Redacted audit record only
- No authorization header value in output
