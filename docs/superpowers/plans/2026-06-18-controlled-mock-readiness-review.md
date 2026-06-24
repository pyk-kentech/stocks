## v7.8 Controlled Mock Readiness Review

### Goal
- Review whether a v7.7 paper-evaluated candidate is eligible for controlled mock execution review.
- Keep the layer local, offline, report-only, and non-executable.

### Scope
- Local JSON fixture input
- Dependency review, safety policy review, boundary violation review
- Controlled mock readiness decision and reports
- CLI surface and system_smoke coverage

### Decision semantics
- `BLOCKED`: unsafe path or failed prerequisite
- `RESEARCH_ONLY`: evidence exists but not sufficient for mock review
- `MOCK_REVIEW_READY`: candidate can move to human mock review
- `MOCK_DRY_RUN_READY`: candidate can later be passed to a dry-run mock layer
- `GAP`: required evidence missing
- `REJECTED`: invalid input

### Hard boundaries
- No live trading
- No real or mock order execution
- No account mutation
- No autonomous trading
- No broker/Kiwoom/network/WebSocket path
- No cloud/local LLM runtime
- No parquet support

### Non-goals
- No real broker integration
- No Kiwoom call
- No mock order placement
- No production execution path
