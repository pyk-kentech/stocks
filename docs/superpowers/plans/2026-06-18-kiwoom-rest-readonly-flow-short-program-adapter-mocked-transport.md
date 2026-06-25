# v8.4 Kiwoom REST Read-Only Flow / Short / Program Adapter / Mocked Transport

## Scope

- Kiwoom REST domestic read-only investor flow, short-selling, lending, and program-trading adapter.
- Exact request builder: `ka10059`.
- Gap-aware request builder: `ka90003`.
- Capability evidence classification for the remaining flow/short/program APIs.
- Mocked transport only.
- Token-ref-only authorization boundary.

## Safety Boundary

- No real Kiwoom, LS, broker, or provider network call.
- No account, order, live, prod, or autonomous path.
- No credential, env var, token file, or raw authorization header generation.
- No WebSocket, cloud LLM, local runtime, or parquet path.

## Output Surface

- Summary report.
- Request report.
- Mocked response report.
- Canonical investor flow report.
- Canonical program flow report.
- Short/lending capability report.
- Flow capability matrix report.
- Continuation report.
- Read-only safety report.
- v7 integration compatibility report.
- Gap report.

## Verification Target

- Focused pytest for flow models, engine, and CLI.
- `system_smoke` confirms mocked/read-only/report-only boundary.
