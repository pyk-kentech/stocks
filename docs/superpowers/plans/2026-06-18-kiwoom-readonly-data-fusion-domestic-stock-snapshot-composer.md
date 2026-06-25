# Kiwoom Read-Only Data Fusion / Domestic Stock Snapshot Composer

## Scope

- Fuse local canonical outputs from v8.1 through v8.5 into a provider-independent `CanonicalDomesticStockSnapshot`.
- Keep the workflow strictly read-only, report-only, offline-only, and local-file-only.
- Emit summary, source coverage, freshness, completeness, conflict, v7 integration, safety, and gap reports.

## Implementation Steps

1. Add snapshot config, safety, report, and canonical snapshot models.
2. Add metadata guard and local JSON fixture loader.
3. Implement the fusion engine with deterministic source precedence and conflict detection.
4. Expose snapshot composer reports through CLI commands.
5. Extend system smoke coverage for snapshot fusion.
6. Add model, engine, and CLI tests, then run focused and full pytest.

## Fusion Rules

- Instrument identity is keyed by `canonical_instrument_key`, with theme membership mapped by `component_stock_code -> <code>_KRX`.
- Reference price prefers quote `last_price`, then falls back to latest daily close.
- Quote-vs-close divergence is reported as a conflict instead of crashing.
- Missing `available_at` or incomplete coverage downgrades readiness to `PARTIAL`.
- Missing instrument keys yields `DATA_GAP`.

## Verification

- `python3.11 -m pytest tests/test_kiwoom_readonly_snapshot_cli.py tests/test_kiwoom_readonly_snapshot_engine.py tests/test_kiwoom_readonly_snapshot_models.py -q`
- `python3.11 -m pytest tests/test_system_smoke.py -q`
- `python3.11 -m pytest -q`
