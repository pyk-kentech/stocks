# v8.7 Kiwoom Manual Response Import Smoke Harness

## Scope
- Add an offline-only manual response import harness for user-saved Kiwoom REST JSON files.
- Route imported files through the existing v8.1-v8.6 read-only chart, rank, quote, flow, sector, and snapshot adapters.
- Fail closed for network paths, credential-like paths, unsupported formats, sensitive content, and blocked account or order APIs.

## Implementation
- Add manual import request, classification, sensitive scan, routing, canonical output, snapshot, safety, gap, and audit models.
- Add local-only metadata and fixture guards.
- Add a harness engine that safely loads JSON, scans content, classifies each API, routes supported responses into existing adapters, and optionally composes a v8.6 snapshot.
- Add CLI report commands for readiness, classification, scan, routing, canonical output, snapshot composition, safety, and gaps.
- Extend system smoke with a deterministic local manual-import run.

## Verification
- `pytest -q tests/test_kiwoom_manual_response_import_models.py tests/test_kiwoom_manual_response_import_engine.py tests/test_kiwoom_manual_response_import_cli.py`
- `pytest -q tests/test_system_smoke.py`
- `pytest -q`
