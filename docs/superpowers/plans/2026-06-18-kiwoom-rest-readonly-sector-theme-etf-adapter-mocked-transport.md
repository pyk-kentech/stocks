# v8.5 Kiwoom REST Read-Only Sector / Theme / ETF Adapter / Mocked Transport

## Scope

- Kiwoom REST domestic read-only theme group, theme component, and ETF trend adapter.
- Exact request builders: `ka90001`, `ka90002`, `ka40003`.
- Capability evidence classification for sector and ETF APIs without exact request schema.
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
- Canonical theme leadership report.
- Canonical theme membership report.
- Canonical ETF trend report.
- Sector/ETF capability matrix report.
- Continuation report.
- Read-only safety report.
- v7 integration compatibility report.
- Gap report.

## Verification Target

- Focused pytest for sector models, engine, and CLI.
- `system_smoke` confirms mocked/read-only/report-only boundary.
