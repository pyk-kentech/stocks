# Stock Risk MCP Handoff

## Repository State

- GitHub target: `https://github.com/pyk-kentech/stocks`
- Current branch: `master`
- Local branch status: ahead of `origin/master` by local release/design commits
- Current completed release line: `v3.4 LLM Feature Store And LLM Signal Evaluation`
- Current implementation commit: `107228f Add LLM feature store signal evaluation`
- Current design commit: `a9db5f3 Document LLM feature store signal evaluation`
- Working tree before this handoff update: clean

Observed v3 release tags:

- `v3.0.0-strategy-core-local-llm-safety-boundary` -> `c1e64aa`
- `v3.1.0-strategy-fixture-backtest-harness` -> `90355fb`
- `v3.2.0-technical-setup-evidence-pack` -> `547953b`
- `v3.3.0-market-universe-volume-spike-discovery` -> `941e36d`
- `v3.4.0-llm-feature-store-signal-evaluation` is present locally

## Current Capability

The project is a local-first, risk-capped trading research and execution
platform foundation. It now includes the v3 offline research stack:

- v3.0 strategy core and local LLM safety boundary
- v3.1 explicit-fixture strategy backtest harness
- v3.2 technical setup evidence pack
- v3.3 market universe and volume-spike discovery layer
- v3.4 LLM feature store and signal evaluation layer

The v3 line is advisory and deterministic by default. It is not live trading,
does not enable PROD, and does not submit orders.

## v3.4 Summary

v3.4 validates already-created LLM signal fixtures and evaluates them against
explicit local future-outcome fixtures. It does not call any LLM.

Added core files:

- `src/stock_risk_mcp/llm_feature_models.py`
- `src/stock_risk_mcp/llm_feature_fixture.py`
- `src/stock_risk_mcp/llm_signal_evaluation.py`
- `src/stock_risk_mcp/llm_feature_service.py`

Added tests:

- `tests/test_llm_feature_fixture.py`
- `tests/test_llm_signal_evaluation.py`
- `tests/test_llm_feature_safety.py`
- `tests/test_llm_feature_service.py`
- `tests/test_llm_feature_cli.py`

Added docs:

- `docs/superpowers/specs/2026-06-16-llm-feature-store-signal-evaluation-design.md`
- `docs/superpowers/plans/2026-06-16-llm-feature-store-signal-evaluation.md`

Added CLI:

```bash
python3.11 -m stock_risk_mcp.cli llm-feature-store-run --signal-fixture-file data/llm_signals.json
python3.11 -m stock_risk_mcp.cli llm-signal-evaluate --signal-fixture-file data/llm_signals.json --outcome-fixture-file data/llm_outcomes.json
python3.11 -m stock_risk_mcp.cli llm-signal-evaluation-show --output-file outputs/llm_signal_evaluation.json
```

Default v3.4 execution is DB-free JSON output only. Supplying `--db` enables
only append-only service-layer audit storage.

## v3.4 Safety Boundary

v3.4:

- consumes explicit local JSON signal fixtures only
- consumes explicit local JSON outcome fixtures only
- does not call local or cloud LLMs
- does not use external network
- does not read credentials or tokens
- does not call broker, Kiwoom, account-read, order, RiskGate, or ExecutionGate
- does not create `StrategyDecision`
- does not create `OrderIntent`
- does not create order drafts
- does not approve execution
- does not change strategy weights automatically
- keeps core modules free of SQLite/repository/provider/realtime/broker/Kiwoom/account/order/network imports

Optional SQLite audit is service-layer only and append-only.

## Verification Baseline

The v3.4 implementation was validated with:

```bash
python3.11 -m pytest -q
python3.11 -m compileall -q src
git diff --check
python3.11 -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs
```

Expected v3.4 baseline:

- `pytest -q`: `648 passed`
- compileall: passed
- `git diff --check`: passed
- system-smoke: `COMPLETED`
- `llm_feature_store_fixture_run=true`
- `llm_signal_evaluation_fixture_run=true`
- `llm_called=false`
- `external_network_calls=false`

The project requires Python `>=3.11`; use `python3.11` for validation.

## Important Documents

- `README.md`: usage and release behavior
- `WORK_SUMMARY.md`: cumulative implementation history
- `docs/superpowers/specs/`: approved release designs
- `docs/superpowers/plans/`: implementation plans

Recent design documents:

- `docs/superpowers/specs/2026-06-15-strategy-core-local-llm-safety-boundary-design.md`
- `docs/superpowers/specs/2026-06-15-strategy-fixture-backtest-harness-design.md`
- `docs/superpowers/specs/2026-06-15-technical-setup-evidence-pack-design.md`
- `docs/superpowers/specs/2026-06-15-market-universe-volume-spike-discovery-layer-design.md`
- `docs/superpowers/specs/2026-06-16-llm-feature-store-signal-evaluation-design.md`

## Safety Invariants

- No live trading.
- No PROD order execution.
- No strategy, LLM, scanner, or evidence path may bypass RiskGate or ExecutionGate.
- No broker/Kiwoom/account-read/order path may be reached by v3 advisory cores.
- No credential/token/network access in pytest or system-smoke.
- MARKET, margin, short, credit, leverage, options, futures, and unsafe order paths remain blocked in protected execution boundaries.
- Local secret directories must remain ignored and must not be read, listed, scanned, printed, moved, or committed.
- `api_key/` is intentionally ignored; do not inspect its contents.

## Recommended Next Step

If continuing the v3 line, start with a design document first. Candidate next
release options:

1. `v3.5 LLM Signal Report Comparison`
   - Compare multiple v3.4 evaluation reports.
   - Do not auto-promote prompts/models.
   - Keep common-outcome and sample-adequacy rules explicit.

2. `v3.5 Strategy Feature Snapshot Builder`
   - Build `StrategyFeatureSnapshot` from explicit local technical/discovery/LLM result files.
   - Keep strategy core dependent only on snapshots.
   - Do not add live/provider/realtime reads.

3. `v3.5 Research Dashboard For v3 Evidence`
   - Local report/dashboard only.
   - No strategy decisions, orders, or execution approvals.

## Release Workflow

1. Write and approve a design document.
2. Write an implementation plan.
3. Implement with focused tests first.
4. Run the full verification baseline.
5. Commit implementation.
6. Create a release tag only after explicit approval.

