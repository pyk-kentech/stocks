## v7.3 Training Pipeline Upgrade / Model Promotion Gate

Scope:
- local JSON fixture only
- offline only
- report only
- non-executable
- no broker, account, order, live, prod, autonomous, network, or LLM path

Core rules:
- v7.1 dataset dependency must be `TRAINING_READY`
- v7.2 validation dependency must be `VALIDATION_READY` or `PAPER_READY`
- v7.0 robustness dependency must not be `BLOCKED` or `REJECTED`
- leakage, snooping, contamination, or reproducibility gaps prevent promotion
- artifacts remain local/offline/non-production even when a candidate reaches `PAPER_CANDIDATE`

Outputs:
- training eligibility report
- model promotion readiness report
- dependency report
- leakage/overfit risk report
- reproducibility report
- model artifact policy report
- redacted audit report

Non-goals:
- no live trading
- no real order execution
- no account mutation
- no autonomous trading
- no profitability claim
- no real broker/API/WebSocket path
