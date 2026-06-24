# v8.0 Kiwoom-First / LS-Compatible Read-Only Adapter Boundary

## Goal
- Add a local, offline, report-only provider adapter boundary.
- Treat `KIWOOM_REST` as the current primary domestic read-only provider.
- Treat `LS_OPEN_API` as a future migration placeholder only.
- Keep all downstream engines on canonical, provider-independent records.

## Scope
- Provider enum, role enum, readiness enum.
- Canonical read-only records for quote, OHLCV, ranking, flow, sector/theme, realtime event, capability, and audit.
- Kiwoom REST evidence map covering read-only candidates vs blocked account/order APIs.
- LS placeholder compatibility report with explicit evidence gap.
- Canonical contract report, capability matrix report, blocked account/order API report, migration readiness report, gap report.
- CLI and system smoke for local fixture-only verification.

## Hard Boundary
- No real Kiwoom or LS call.
- No provider or network call.
- No credential, env var, API key, or token read.
- No authorization header generation.
- No account/order/trading execution path.
- No WebSocket execution path.
- Parquet unsupported.

## Output Contract
- All outputs remain `read_only`, `report_only`, `non_executable`, `local_file_only`, `offline_only`.
- Canonical records carry provider metadata, redacted raw payload, stale/gap flags, and source refs.
- Account/order APIs stay explicitly blocked even when present in Kiwoom evidence.

## Verification
- Focused model/engine/CLI tests for capability classification, blocked APIs, canonical independence, and boundary enforcement.
- `system_smoke` verifies local/offline/report-only operation and absence of provider/network/account/order execution.
