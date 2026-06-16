# Stock Risk MCP Handoff

## Repository State

- GitHub target: `https://github.com/pyk-kentech/stocks`
- Current branch: `master`
- Local branch status: ahead of `origin/master` by local release/design commits
- Current completed release line: `v3.10 Local Model Backend Selection Benchmark`
- Current implementation/tag commit: `d40c38e Add local model backend selection benchmark`
- Current design commit: `7470a88 Document local model backend selection benchmark`
- Working tree before this handoff update: clean

Observed v3 release tags:

- `v3.0.0-strategy-core-local-llm-safety-boundary` -> `c1e64aa`
- `v3.1.0-strategy-fixture-backtest-harness` -> `90355fb`
- `v3.2.0-technical-setup-evidence-pack` -> `547953b`
- `v3.3.0-market-universe-volume-spike-discovery` -> `941e36d`
- `v3.4.0-llm-feature-store-signal-evaluation` -> `107228f`
- `v3.5.0-trade-plan-basket-risk-engine` -> `aa51005`
- `v3.6.0-paper-trading-strategy-evaluation` -> `214d976`
- `v3.7.0-walk-forward-replay-policy-optimizer` -> `b86f5bc`
- `v3.8.0-local-llm-advisory-adapter-hardening` -> `cb2b11e`
- `v3.9.0-local-model-runtime-adapter-contract` -> `5b39cda`
- `v3.10.0-local-model-backend-selection-benchmark` -> `d40c38e`

## Current Capability

The project is a local-first, risk-capped trading research and execution
platform foundation. It now includes the v3 offline research stack through
v3.10:

- v3.0 strategy core and local LLM safety boundary
- v3.1 explicit-fixture strategy backtest harness
- v3.2 technical setup evidence pack
- v3.3 market universe and volume-spike discovery layer
- v3.4 LLM feature store and signal evaluation layer
- v3.5 trade plan and basket risk engine
- v3.6 paper trading strategy evaluation
- v3.7 walk-forward / replay policy optimizer
- v3.8 local LLM advisory adapter hardening
- v3.9 local model runtime adapter contract
- v3.10 local model backend selection benchmark

The v3 line is advisory and deterministic by default. It is not live trading,
does not enable LIVE or PROD, and does not submit orders.

## v3.6 Summary

v3.6 evaluates advisory strategy and trade-plan outputs with deterministic
paper-only simulation over explicit local JSON fixtures. It simulates entry,
stop, target, forced end-of-fixture close, paper P/L, equity curve, and
drawdown without creating or submitting any real orders.

## v3.7 Summary

v3.7 reruns baseline and candidate policies against the same explicit local
replay fixtures by deterministic walk-forward window. It produces advisory
promotion or demotion recommendations only and does not change production
strategy behavior automatically.

## v3.8 Summary

v3.8 hardens a local LLM advisory adapter around explicit local JSON fixtures.
The backend defaults to `DISABLED`. `LOCAL_MODEL` is representable only through
explicit local fixture/config metadata, and unsafe output is rejected or
converted into a safe refusal. The adapter remains advisory-only and does not
create `StrategyDecision`, `OrderIntent`, order drafts, or execution approvals.

## v3.9 Summary

v3.9 adds a contract-first mock local model runtime layer around explicit local
JSON fixtures. The runtime contract remains fixture-first and advisory-only.
`DISABLED` remains the default backend. `MOCK_LOCAL_RUNTIME` is the only
execution-capable backend in v3.9, and it returns deterministic fixture-derived
responses only. `OLLAMA_LOCAL`, `LLAMACPP_LOCAL`, and
`PYTHON_LOCAL_WRAPPER` are schema-declared future backends that are rejected at
runtime in v3.9.

## v3.10 Summary

v3.10 adds an offline local model backend benchmark layer. It evaluates
fixture-provided candidate outputs only, using evaluator/ranker logic with
two-stage benchmark adjudication: absolute scorecard first, hard fail gates
second, and eligibility before ranking. Only `ELIGIBLE` candidates may be
ranked. The benchmark does not call any real model or backend runtime.

Added recent design docs:

- `docs/superpowers/specs/2026-06-16-paper-trading-strategy-evaluation-design.md`
- `docs/superpowers/specs/2026-06-17-walk-forward-replay-policy-optimizer-design.md`
- `docs/superpowers/specs/2026-06-17-local-llm-advisory-adapter-hardening-design.md`
- `docs/superpowers/specs/2026-06-17-local-model-runtime-adapter-selection-design.md`
- `docs/superpowers/specs/2026-06-17-local-model-backend-selection-benchmark-design.md`

Added recent CLI:

```bash
python3.11 -m stock_risk_mcp.cli paper-eval-run --fixture-file data/paper_eval_fixture.json --output-file outputs/paper_eval.json
python3.11 -m stock_risk_mcp.cli policy-replay-run --fixture-file data/policy_replay_fixture.json --output-file outputs/policy_replay.json
python3.11 -m stock_risk_mcp.cli local-llm-advisory-run --fixture-file data/local_llm_advisory_fixture.json --output-file outputs/local_llm_advisory.json
python3.11 -m stock_risk_mcp.cli local-model-runtime-check --fixture-file data/local_model_runtime_fixture.json --output-file outputs/local_model_runtime.json
python3.11 -m stock_risk_mcp.cli local-model-advisory-dry-run --fixture-file data/local_model_runtime_fixture.json --output-file outputs/local_model_runtime_dry_run.json
python3.11 -m stock_risk_mcp.cli local-model-benchmark-run --fixture-file data/local_model_benchmark_fixture.json --candidate-output-file data/local_model_candidate_output_fixture.json --output-file outputs/local_model_benchmark_report.json
python3.11 -m stock_risk_mcp.cli local-model-candidates-rank --benchmark-report-file outputs/local_model_benchmark_report.json
```

Default execution remains local JSON fixture driven. Optional SQLite audit, when
present in earlier releases, stays service-layer only.

## Current Safety State

Current enforced safety state through v3.10:

- no LIVE
- no PROD
- no broker/Kiwoom/account-read
- no credential/token/network access
- no real `OrderIntent`, order draft, or order submission
- local LLM remains advisory-only
- contract-first mock adapter for local model runtime
- fixture-first local model runtime contract
- offline benchmark fixture only
- evaluator/ranker only
- two-stage benchmark adjudication
- absolute scorecard first
- hard fail gates second
- eligibility before ranking
- only `ELIGIBLE` candidates may be ranked
- backend default `DISABLED`
- `MOCK_LOCAL_RUNTIME` only for deterministic offline fixture/mock behavior
- `OLLAMA_LOCAL`, `LLAMACPP_LOCAL`, and `PYTHON_LOCAL_WRAPPER` are future-declared only
- no real model call
- no Ollama call
- no llama.cpp call
- no transformers or direct Python inference
- no model download
- no cloud backend
- no external network
- advisory-only and fail-closed behavior preserved
- no strategy, policy, or LLM path may bypass `RiskGate` or `ExecutionGate`
- core modules remain free of DB/repository/provider/realtime/broker/Kiwoom/account/order/network imports

## Verification Baseline

The current release line was validated with:

```bash
python3.11 -m pytest -q
python3.11 -m compileall -q src
git diff --check
python3.11 -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs
```

Expected baseline after v3.10:

- `pytest -q`: `773 passed`
- compileall: passed
- `git diff --check`: passed
- system-smoke: `COMPLETED`
- `llm_feature_store_fixture_run=true`
- `llm_signal_evaluation_fixture_run=true`
- `trade_plan_fixture_run=true`
- `paper_eval_fixture_run=true`
- `policy_replay_fixture_run=true`
- `llm_advisory_fixture_run=true`
- `local_model_runtime_fixture_run=true`
- `local_model_benchmark_fixture_run=true`
- `llm_called=false`
- `real_model_called=false`
- `cloud_backend_used=false`
- `external_network_calls=false`
- `model_downloaded=false`

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
- `docs/superpowers/specs/2026-06-16-trade-plan-basket-risk-engine-design.md`
- `docs/superpowers/specs/2026-06-16-paper-trading-strategy-evaluation-design.md`
- `docs/superpowers/specs/2026-06-17-walk-forward-replay-policy-optimizer-design.md`
- `docs/superpowers/specs/2026-06-17-local-llm-advisory-adapter-hardening-design.md`
- `docs/superpowers/specs/2026-06-17-local-model-runtime-adapter-selection-design.md`
- `docs/superpowers/specs/2026-06-17-local-model-backend-selection-benchmark-design.md`

## Safety Invariants

- No live trading.
- No PROD order execution.
- No strategy, LLM, scanner, or evidence path may bypass RiskGate or ExecutionGate.
- No broker/Kiwoom/account-read/order path may be reached by v3 advisory cores.
- No cloud LLM backend may be reached by v3 advisory cores.
- No real local model runtime may escape fixture-first, advisory-only, fail-closed boundaries.
- No offline benchmark path may trigger real model calls, backend execution, or ranking of failed candidates.
- No credential/token/network access in pytest or system-smoke.
- MARKET, margin, short, credit, leverage, options, futures, and unsafe order paths remain blocked in protected execution boundaries.
- Local secret directories must remain ignored and must not be read, listed, scanned, printed, moved, or committed.
- `api_key/` is intentionally ignored; do not inspect its contents.

## Recommended Next Step

If continuing the v3 line, start with design only for:

1. `v3.9 Local Model Runtime Adapter / Model Selection`
   - completed

2. `v3.10 Local Model Backend Selection / Offline Benchmark Fixture`
   - completed

3. `v3.11 Local Model Backend Decision Report / Benchmark Pack Expansion`
   - design only first
   - expand benchmark packs and decision reporting without real inference
   - preserve advisory-only behavior and fail-closed validation
   - do not add LIVE, PROD, broker, account, credential, token, or network paths

## Release Workflow

1. Write and approve a design document.
2. Write an implementation plan.
3. Implement with focused tests first.
4. Run the full verification baseline.
5. Commit implementation.
6. Create a release tag only after explicit approval.
