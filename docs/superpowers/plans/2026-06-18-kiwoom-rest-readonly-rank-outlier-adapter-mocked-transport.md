# v8.2 Kiwoom REST Read-Only Rank / Outlier Adapter / Mocked Transport

## Scope

- Kiwoom REST domestic read-only ranking/outlier adapter.
- Supported request builders: `ka00198`, `ka10023`, `ka10030`, `ka10032`.
- Future-supported evidence only: `ka10019`, `ka10027`, `ka10098`.
- Mocked transport only.
- Token-ref-only authorization boundary.
- Canonical rank and outlier momentum signal conversion.

## Safety Boundary

- No real Kiwoom, LS, broker, or provider network call.
- No account/order/live/prod path.
- No credential, env var, token file, or raw authorization header generation.
- No WebSocket, cloud LLM, local runtime, or parquet path.

## Output Surface

- Summary report.
- Request report.
- Mocked response report.
- Canonical rank signal report.
- Canonical outlier momentum signal report.
- Continuation report.
- Read-only safety report.
- v7 integration compatibility report.
- Gap report.

## Verification Target

- Focused pytest for rank models/engine/CLI.
- `system_smoke` confirms mocked/read-only/report-only boundary.
