# v8.1 Kiwoom REST Read-Only Chart Adapter / Mocked Transport

## Goal
- Implement the first Kiwoom REST read-only domestic chart adapter.
- Support only `ka10081` daily OHLCV and `ka10080` minute OHLCV.
- Keep transport mocked/injected only and block real network by default.

## Scope
- Read-only request/response models, continuation metadata, canonical OHLCV conversion, safety/gap/audit reports.
- Token-ref-only request boundary with no raw token/header generation.
- CLI and system smoke using local JSON fixture payloads only.

## Hard Boundary
- No real Kiwoom call, no LS call, no provider/network/WebSocket call.
- No credential, env var, API key, token file, or raw token read.
- No account/order/trading path.
- No live/prod path.
- Parquet unsupported.

## Output Contract
- Canonical OHLCV records remain provider-independent and read-only.
- All outputs remain local/offline/report-only/non-executable.
- Account/order API ids and realtime account/order streams are blocked.

## Verification
- Focused tests cover request building, mocked response parsing, signed numeric normalization, continuation handling, blocked APIs, and CLI outputs.
- `system_smoke` verifies mocked transport only and zero provider/account/order execution.
