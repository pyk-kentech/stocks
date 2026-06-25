# v8.8 Final Kiwoom Read-Only Transport Capture Snapshot Validation

## Scope
- Add a strictly opt-in Kiwoom domestic real read-only transport boundary with preview-first default behavior.
- Reuse the v8.7 manual response import harness for parser routing and the v8.6 snapshot composer for validation.
- Keep tests fully offline and mocked while proving that account, order, token, credential, and unsafe capture paths stay blocked.

## Implementation
- Add final transport models, guard, client, capture helper, engine, and fixture loader.
- Keep default mode blocked or preview-only, with real network execution available only behind explicit user acknowledgements and explicit token provider configuration.
- Add mocked-call and single-call smoke paths that produce redacted request preview, execution decision, capture, parser routing, snapshot validation, readiness, safety, gap, and audit reports.
- Persist captured responses only as redacted local JSON with sanitized filenames and no raw authorization or credential material.
- Extend CLI and `system_smoke` with report-only v8.8 coverage.

## Verification
- `python3.11 -m pytest tests/test_kiwoom_readonly_final_transport_engine.py tests/test_kiwoom_readonly_final_transport_cli.py tests/test_kiwoom_readonly_final_transport_models.py -q`
- `python3.11 -m pytest tests/test_system_smoke.py -q`
- `python3.11 -m pytest -q`
