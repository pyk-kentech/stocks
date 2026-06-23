## v7.6 Offline Allocation Policy Training / Evaluation Sandbox

Scope:
- local JSON fixture only
- offline only
- report only
- non-executable
- deterministic lightweight scoring only
- no broker, account, order, live, prod, autonomous, network, or LLM path

Core rules:
- v7.5 learning dataset must be `TRAINING_READY`
- training/evaluation is lightweight and deterministic, not heavy model fitting
- walk-forward, leakage, turnover, drawdown, and artifact policy gates control promotion
- artifact metadata stays local/offline/non-production
- policy output remains paper-candidate only and never executable

Outputs:
- policy training summary report
- regime action selection report
- walk-forward evaluation report
- risk-adjusted performance report
- turnover/slippage risk report
- drawdown stability report
- policy promotion readiness report
- model artifact policy report
- redacted audit report

Non-goals:
- no live trading
- no real order execution
- no account mutation
- no autonomous trading
- no broker/API/WebSocket path
- no profitability claim
