# v6.7 Kiwoom Mock API Execution Readiness / Preflight Gate

## Goal

Design and implement a local, non-executable preflight gate that evaluates whether a Kiwoom mock API request draft is safe enough for future execution consideration.

## Scope

- Local fixture-only config loading
- Dependency references to v6.4 credential boundary, v6.5 OAuth draft boundary, and v6.6 transport draft boundary
- Request category classification:
  - `OAUTH`
  - `QUOTE`
  - `ACCOUNT`
  - `ORDER`
  - `WEBSOCKET`
  - `UNKNOWN`
- Readiness decisions:
  - `BLOCKED`
  - `DRAFT_READY`
  - `GAP`
  - `REJECTED`
- Blocked capability reporting
- Gap reporting
- Redacted audit reporting
- CLI report commands

## Boundary

- Draft-only
- Mock-only
- Preflight-gate-only
- Offline-only
- Local-file-only
- Non-executable
- No env read
- No credential file read
- No credential loading
- No token loading, usage, refresh
- No authorization header generation
- No HTTP client/session/transport creation
- No OAuth/token/API/mockapi/WebSocket/network execution
- No account read or mutation
- No order path
- No live/prod path
- No cloud or local LLM runtime
- Parquet unsupported

## Decision Policy

- OAuth endpoints: always `BLOCKED`
- Account endpoints: always `BLOCKED`
- Order endpoints: always `BLOCKED`
- WebSocket endpoints: always `BLOCKED`
- Production domains: rejected/blocked
- Unknown endpoints: `REJECTED`
- Mock-domain quote/market-data drafts may be `DRAFT_READY` as future execution candidates only
- `DRAFT_READY` must not create any executable transport path

## Outputs

- Readiness report
- Safety report
- Gap report
- Redacted audit record

## Non-Goals

- No execution
- No token usage
- No HTTP transport
- No broker/account/order integration
- No system smoke in this task
- No full pytest in this task
