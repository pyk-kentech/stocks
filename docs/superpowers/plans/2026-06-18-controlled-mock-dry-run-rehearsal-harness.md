## v7.13 Controlled Mock Dry-Run Rehearsal Harness

Goal: add a local/offline/report-only rehearsal harness that consumes the newer v7.9-v7.12 risk layers and rehearses decision-to-mock-order-intent flow without creating any executable order path.

Core design:
- single independent `controlled_mock_dry_run_*` layer following the existing v7.8 / v7.9 / v7.10 / v7.11 / v7.12 pattern
- one input object carrying v7.7 paper pass evidence, v7.8 mock readiness, v7.9 regime, v7.9.1 provider readiness, v7.10 sizing, v7.11 event risk, v7.12 breadth routing, and local dry-run guard refs
- one engine producing:
  - primary dry-run decision
  - non-executable mock order intent preview
  - rehearsal subreports for preflight, provider, regime, sizing, event risk, breadth routing, order gate, risk budget, kill switch, rollback, audit, boundary violations, and gaps

Policy:
- this harness may rehearse the workflow, but it may not place real orders, broker paper orders, Kiwoom orders, or Kiwoom mock orders
- v7.10 and v7.11 hard gates are never overridden
- v7.12 routing may narrow the allowed route or sleeve, but never create normal broad-market permission from outlier-only status
- `MOCK_EXECUTION_REVIEW_READY` means later design/review may proceed, not that execution is enabled

Hard boundaries:
- local fixture only
- offline only
- report only
- non-executable
- no broker / Kiwoom / provider / network / WebSocket path
- no credential / token / secret / raw account output
- no live / prod / autonomous path
- no Kiwoom mock order execution
- parquet unsupported

Implementation scope:
- models, guard, fixture loader, engine
- CLI wiring
- system smoke coverage
- focused tests plus full regression before commit/tag
