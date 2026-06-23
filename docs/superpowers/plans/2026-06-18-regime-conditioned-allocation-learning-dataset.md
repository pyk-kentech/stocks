## v7.5 Regime-Conditioned Allocation Learning Dataset

Scope:
- local JSON fixture only
- offline only
- report only
- non-executable
- no broker, account, order, live, prod, autonomous, network, or LLM path

Core rules:
- risk-off regime does not automatically imply block or inverse execution
- regime/action/outcome tuples are learning records only
- inverse or hedge actions remain report-only candidates with explicit eligibility evidence
- missing point-in-time `available_at`, future regime leakage, or future outcome leakage prevents training readiness
- current-survivors-only dependencies remain blocked from training-ready

Outputs:
- regime feature report
- action candidate report
- hedge/inverse eligibility report
- forward outcome label report
- reward scoring report
- leakage report
- learning dataset readiness report
- redacted audit report

Non-goals:
- no live trading
- no real order execution
- no account mutation
- no autonomous trading
- no inverse or hedge order placement
- no real broker/API/WebSocket path
