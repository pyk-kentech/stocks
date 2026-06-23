## v7.7 Risk-Adjusted Paper Trading Evaluation

### Goal
- Evaluate v7.6 allocation policy candidates in a local, offline, report-only paper-evaluation layer.
- Include simulated portfolio accounting, cost/slippage assumptions, drawdown/exposure checks, and optional regime/CNN fear features.

### Scope
- Local JSON fixture input
- Deterministic virtual portfolio / trade ledger / performance reports
- Paper-pass readiness decision with conservative gating
- CLI report surface
- system_smoke coverage

### Hard boundaries
- No live trading
- No real order or broker path
- No account mutation
- No Kiwoom or other external API call
- No autonomous trading
- No cloud/local LLM runtime
- No parquet support

### Decision semantics
- `BLOCKED`: unsafe or leakage/risk breach
- `RESEARCH_ONLY`: exploratory result only
- `PAPER_EVALUATED`: simulation completed but not pass-ready
- `PAPER_PASS`: local paper pass only for later controlled review
- `GAP`: dependency or evidence missing
- `REJECTED`: invalid input

### Inputs
- Policy candidate and policy promotion refs/decision
- Point-in-time and walk-forward refs
- Ensemble/regime refs
- Optional CNN Fear & Greed ref
- Local market data and cost assumptions refs
- Initial cash, evaluation window, benchmark

### Outputs
- Summary, portfolio, trade ledger, cost/slippage, risk-adjusted performance, drawdown/exposure, regime/fear bucket, readiness, gap, safety, audit

### Non-goals
- No live broker paper trading
- No real order execution
- No heavy model training
- No production execution path
