## v7.0 Quant Strategy Robustness / Training Readiness Foundation

Scope:
- local JSON fixture only
- offline only
- report only
- non-executable
- no broker, order, account, live, prod, autonomous, network, or LLM path

Core decisions:
- `RESEARCH_READY` is allowed only for exploratory offline analysis
- `TRAINING_READY` requires point-in-time historical universe evidence, feature `available_at` discipline, walk-forward split discipline, limited tuning pressure, diversification coverage, and regime coverage
- `GAP` means missing robustness evidence
- `BLOCKED` means unsafe or leakage-prone
- `REJECTED` means invalid input or forbidden boundary breach

Policies:
- survivorship bias policy distinguishes current-survivor replay from point-in-time universe replay
- point-in-time policy requires `available_at`, corporate-action handling, and delisting/symbol-change coverage
- walk-forward policy tracks train/validation/test/forward-paper windows and final-test retuning
- data-snooping policy tracks parameter-search count and period stability
- diversification policy tracks alpha family breadth and co-movement/correlation risk
- regime readiness policy tracks regime bucket coverage before promotion-oriented use

Outputs:
- robustness readiness report
- survivorship bias report
- point-in-time leakage report
- walk-forward policy report
- data-snooping report
- strategy diversification report
- regime readiness report
- redacted audit record

Non-goals:
- no live trading
- no real order execution
- no account mutation
- no autonomous trading
- no profitability claim
- no real broker/API/WebSocket path
