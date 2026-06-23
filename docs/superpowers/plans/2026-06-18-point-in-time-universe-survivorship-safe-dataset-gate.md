## v7.1 Point-in-Time Universe / Survivorship-Safe Dataset Gate

Scope:
- local JSON fixture only
- offline only
- report only
- non-executable
- no broker, account, order, live, prod, autonomous, network, or LLM path

Core rules:
- `CURRENT_SURVIVORS_ONLY` datasets are never training-grade
- `POINT_IN_TIME_UNIVERSE` datasets need lifecycle, tradability, index membership, and `available_at` evidence before becoming `TRAINING_READY`
- `MIXED_OR_UNKNOWN` stays `GAP` or `RESEARCH_ONLY`
- future index membership, future delisting knowledge, and missing `available_at` are fail-closed conditions

Outputs:
- point-in-time universe report
- survivorship bias dataset report
- security lifecycle coverage report
- dataset leakage report
- dataset promotion readiness report
- gap report
- redacted audit report

Non-goals:
- no live trading
- no real order execution
- no account mutation
- no autonomous trading
- no profitability claim
- no real broker/API/WebSocket path
