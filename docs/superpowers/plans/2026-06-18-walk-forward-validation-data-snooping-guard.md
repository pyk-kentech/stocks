## v7.2 Walk-Forward Validation / Data-Snooping Guard

Scope:
- local JSON fixture only
- offline only
- report only
- non-executable
- no broker, account, order, live, prod, autonomous, network, or LLM path

Core rules:
- walk-forward windows must be non-overlapping across train, validation, test, and forward-paper
- repeated final-test tuning and final holdout contamination fail closed
- excessive parameter search and hidden failed trial pressure downgrade or block
- missing experiment lineage prevents promotion-grade decisions
- stable multi-fold validation is required before `PAPER_READY`

Outputs:
- walk-forward split report
- data-snooping report
- experiment lineage report
- parameter-search pressure report
- final-test contamination report
- stability report
- promotion readiness report
- redacted audit report

Non-goals:
- no live trading
- no real order execution
- no account mutation
- no autonomous trading
- no profitability claim
- no real broker/API/WebSocket path
