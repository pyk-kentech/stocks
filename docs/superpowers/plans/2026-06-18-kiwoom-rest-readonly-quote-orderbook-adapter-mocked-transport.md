# v8.3 Kiwoom REST Read-Only Quote / Orderbook / Execution Info Adapter / Mocked Transport

## Scope

- Kiwoom REST domestic read-only quote, orderbook, execution-info, and basic-info adapter.
- Supported request builders: `ka10004`, `ka10003`, `ka10001`.
- Mocked transport only.
- Token-ref-only authorization boundary.
- Canonical quote, orderbook, liquidity hint, and basic instrument info conversion.

## Safety Boundary

- No real Kiwoom, LS, broker, or provider network call.
- No account, order, live, prod, or autonomous path.
- No credential, env var, token file, or raw authorization header generation.
- No WebSocket, cloud LLM, local runtime, or parquet path.

## Output Surface

- Summary report.
- Request report.
- Mocked response report.
- Canonical quote report.
- Canonical orderbook report.
- Liquidity hint report.
- Basic instrument info report.
- Continuation report.
- Read-only safety report.
- v7 integration compatibility report.
- Gap report.

## Verification Target

- Focused pytest for quote models, engine, and CLI.
- `system_smoke` confirms mocked/read-only/report-only boundary.
