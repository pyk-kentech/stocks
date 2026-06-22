# Internal Paper Trading Simulator Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Design a strictly internal, local-only, offline, deterministic paper trading simulator that consumes v5.9 `HistoricalSignalCandidate` outputs and emits paper-only decisions, paper-only order intents, simulated fills, ledger/position updates, risk-limit enforcement, performance reports, safety reports, gap reports, and audit records without creating any real order, broker, account, Kiwoom, LS, provider, network, live, or production path.

**Architecture:** Add a dedicated `PaperTrading*` module family that reads only local fixture-derived signal candidate inputs, applies an internal paper policy, creates a separate `PaperOrderIntent` surface that is explicitly not compatible with any real `OrderIntent`, simulates deterministic fills using only local replay/price fixtures, maintains a separate `PaperLedger`, tracks positions and paper-only risk state, and generates report-only performance and safety artifacts. Every boundary remains fail-closed and non-executable.

**Tech Stack:** Python 3.11, Pydantic v2, existing strict model patterns, pure-Python deterministic simulation, local fixture loaders, existing CLI patterns, pytest, system smoke

---

## 1. Input / Output Boundaries

### Allowed inputs

v5.10 may consume only local fixture-derived artifacts:

- `HistoricalSignalCandidateInput`
- `HistoricalSignalCandidateBatch`
- `HistoricalSignalCandidateReport`
- `HistoricalSignalCandidateSafetyReport`
- `HistoricalSignalCandidateGapReport`
- local replay-time or historical price-path fixtures required for deterministic fill simulation
- local replay session / calendar context fixtures if needed for holding-period progression

Each input must remain:

- local fixture only
- offline only
- non-executable
- no-network
- no-provider-api
- no-broker-api
- no-account-api
- no-order-api
- no-cloud-LLM
- no-local-LLM-runtime

### Required outputs

Planned first-class outputs:

- `PaperTradingConfig`
- `PaperTradingInput`
- `PaperPolicy`
- `PaperDecision`
- `PaperOrderIntent`
- `PaperFill`
- `PaperLedger`
- `PaperPosition`
- `PaperTrade`
- `PaperRiskLimit`
- `PaperPerformanceReport`
- `PaperTradingSafetyReport`
- `PaperTradingGapReport`
- `PaperTradingAuditRecord`

### Hard separation

- `PaperOrderIntent` must be internal-only and incompatible with any real `OrderIntent`.
- `PaperLedger` must be separate from any real account, custody, balance, or broker ledger model.
- `InternalPaperBroker` is only a deterministic simulator concept, not a broker adapter.
- No Kiwoom mock API, LS mock API, or generic broker mock API is part of v5.10.

## 2. Paper Policy Rules

`PaperPolicy` should express deterministic paper-only decision rules from neutral candidates.

Allowed policy inputs:

- candidate score
- score bucket
- confidence bucket
- predicted outcome label
- risk review blocked/warning state
- promotion block state
- per-day candidate budget
- max positions
- max gross exposure
- max per-symbol exposure
- max daily loss
- max drawdown
- holding period
- stop simulation rule
- take-profit simulation rule

Forbidden policy inputs:

- real account balances
- real broker state
- real order state
- live quotes
- live inference
- real-time market data
- network/API/provider responses

Policy outcomes must stay neutral and internal:

- `ALLOW_PAPER`
- `BLOCK_PAPER`
- `SKIP_PAPER`
- `HOLD_PAPER`
- `EXIT_PAPER`

These are simulator actions only, not real trading actions.

## 3. Paper Order Intent Schema

`PaperOrderIntent` should be the internal bridge between paper decisions and deterministic fill simulation.

Required fields:

- paper order intent id
- source candidate id
- source candidate batch id
- decision id
- symbol
- side
- simulated order type
- paper quantity or notional
- decision timestamp
- intended entry session
- intended exit rule metadata
- holding-period rule
- score / confidence snapshot
- risk-limit snapshot
- report-only safety flags

Required exclusions:

- no real broker order id
- no real account id
- no broker routing metadata
- no Kiwoom / LS metadata
- no provider API metadata
- no execution approval field
- no real exchange state

`PaperOrderIntent` should deliberately use names distinct from production order APIs where ambiguity is possible.

## 4. Fill Simulator Design

The fill simulator should be deterministic and local.

Planned rules:

- default fill mode: deterministic next-bar fill
- optional configurable slippage parameter
- optional configurable fee parameter
- explicit fill rejection if required price/volume assumptions are missing
- explicit fill rejection if session progression is missing
- no partial real-world microstructure modeling in v5.10 beyond deterministic documented rules

Planned simulator components:

- `InternalPaperBroker`
- fill assumption validator
- next-bar price selector
- optional slippage/fee adjuster
- fill rejection reporter

Non-goals for fill logic:

- no exchange connectivity
- no market depth modeling
- no smart routing
- no broker callbacks
- no asynchronous execution state machine

## 5. Paper Ledger Design

`PaperLedger` should be a standalone internal accounting surface.

Ledger responsibilities:

- starting cash
- reserved cash
- realized P/L
- unrealized P/L
- fees accrued
- slippage cost accrued
- open positions
- closed trades
- daily equity curve
- drawdown state
- exposure totals

Ledger update sources:

- paper fills
- position mark updates from local fixture price-path data
- paper exits generated by simulator rules

Ledger must never:

- read a real account
- sync to a broker
- import custody balances
- share schema with real account APIs

## 6. Position / Risk Manager Design

Position and risk management should be deterministic, local, and fail-closed.

Planned concepts:

- `PaperPosition`
- `PaperRiskLimit`
- risk state snapshot per session
- exposure monitor
- loss-limit monitor
- drawdown monitor
- holding-period exit monitor

Required controls:

- max simultaneous positions
- max exposure
- max per-symbol exposure
- max daily loss
- max drawdown
- stop simulation rule
- take-profit simulation rule
- stale candidate rejection
- missing fill-data rejection

If any risk input is missing or inconsistent:

- block new paper intents
- emit explicit gaps
- preserve open-state reporting without inventing missing fills or prices

## 7. Performance Report Design

`PaperPerformanceReport` should stay report-only and summarize internal simulator outcomes.

Required metrics:

- total return
- realized P/L
- unrealized P/L
- max drawdown
- win rate
- profit factor
- average win
- average loss
- turnover
- exposure time
- fees
- slippage cost
- number of trades

Recommended supporting summaries:

- per-symbol trade count
- per-symbol realized P/L
- entry / exit reason distributions
- blocked decision counts
- fill rejection counts
- holding-period distributions

The report must not imply production readiness or real execution quality.

## 8. Safety Guard Design

The v5.10 guard should be fail-closed and enforce:

- `paper_only=true`
- `simulated_only=true`
- `non_executable=true`
- `local_file_only=true`
- `offline_only=true`
- `no_network=true`
- `no_provider_api=true`
- `no_real_order=true`
- `no_broker_api=true`
- `no_account_api=true`
- `no_order_api=true`
- `no_kiwoom_api=true`
- `no_ls_api=true`
- `no_live_prod=true`
- `no_cloud_llm=true`
- `no_local_llm_runtime=true`

The guard must reject:

- real order ids or real `OrderIntent` references
- broker/account/order/execution metadata
- Kiwoom markers
- LS markers
- network/provider/API paths
- LIVE/PROD markers
- credentials/tokens/secrets
- cloud/local LLM markers
- advisory buy/sell recommendation wording where it implies real execution
- parquet input/output markers

## 9. Gap Taxonomy

Initial planned gap categories should include:

- `PAPER_TRADING_REPORT_GENERATED`
- `PAPER_TRADING_PAPER_ONLY`
- `PAPER_TRADING_SIMULATED_ONLY`
- `PAPER_TRADING_NON_EXECUTABLE`
- `PAPER_TRADING_LOCAL_ONLY`
- `PAPER_TRADING_OFFLINE_ONLY`
- `PAPER_TRADING_MISSING_INPUT`
- `PAPER_TRADING_MISSING_SIGNAL_CANDIDATE`
- `PAPER_TRADING_MISSING_PRICE_PATH`
- `PAPER_TRADING_MISSING_SESSION_CONTEXT`
- `PAPER_TRADING_MISSING_RISK_LIMIT`
- `PAPER_TRADING_MISSING_POLICY`
- `PAPER_TRADING_MISSING_LEDGER_STATE`
- `PAPER_TRADING_MISSING_FILL_ASSUMPTION`
- `PAPER_TRADING_FILL_REJECTED`
- `PAPER_TRADING_INSUFFICIENT_VOLUME_ASSUMPTION`
- `PAPER_TRADING_INSUFFICIENT_PRICE_ASSUMPTION`
- `PAPER_TRADING_MAX_POSITION_LIMIT_BLOCKED`
- `PAPER_TRADING_MAX_EXPOSURE_LIMIT_BLOCKED`
- `PAPER_TRADING_MAX_SYMBOL_EXPOSURE_LIMIT_BLOCKED`
- `PAPER_TRADING_MAX_DAILY_LOSS_LIMIT_BLOCKED`
- `PAPER_TRADING_MAX_DRAWDOWN_LIMIT_BLOCKED`
- `PAPER_TRADING_RUNTIME_SIGNAL_NOT_ALLOWED`
- `PAPER_TRADING_REAL_ORDER_NOT_ALLOWED`
- `PAPER_TRADING_BROKER_API_NOT_ALLOWED`
- `PAPER_TRADING_ACCOUNT_API_NOT_ALLOWED`
- `PAPER_TRADING_ORDER_API_NOT_ALLOWED`
- `PAPER_TRADING_KIWOOM_API_NOT_ALLOWED`
- `PAPER_TRADING_LS_API_NOT_ALLOWED`
- `PAPER_TRADING_NETWORK_NOT_ALLOWED`
- `PAPER_TRADING_PROVIDER_API_NOT_ALLOWED`
- `PAPER_TRADING_LIVE_PROD_NOT_ALLOWED`
- `PAPER_TRADING_CLOUD_LLM_NOT_ALLOWED`
- `PAPER_TRADING_LOCAL_LLM_RUNTIME_NOT_ALLOWED`
- `PAPER_TRADING_CREDENTIALS_NOT_ALLOWED`
- `PAPER_TRADING_PARQUET_NOT_ALLOWED`

## 10. CLI Design

Planned CLI commands:

- `paper-trading-simulate --fixture-file ... [--output-file ...]`
- `paper-trading-ledger-report --fixture-file ... [--output-file ...]`
- `paper-trading-performance-report --fixture-file ... [--output-file ...]`
- `paper-trading-safety-report --fixture-file ... [--output-file ...]`
- `paper-trading-gap-report --fixture-file ... [--output-file ...]`

CLI requirements:

- local fixture file required
- optional local JSON output only
- report-only outputs only
- no network calls
- no provider calls
- no broker/account/order calls
- no Kiwoom/LS integrations
- no live execution path

## 11. system_smoke Design

Planned `system_smoke` checks:

- `paper_trading_fixture_run=true`
- `paper_trading_decision_report_generated=true`
- `paper_trading_order_intent_generated=true`
- `paper_trading_fill_generated=true`
- `paper_trading_ledger_generated=true`
- `paper_trading_performance_report_generated=true`
- `paper_trading_safety_report_generated=true`
- `paper_trading_gap_report_generated=true`
- `paper_trading_paper_only=true`
- `paper_trading_simulated_only=true`
- `paper_trading_non_executable=true`
- `paper_trading_local_only=true`
- `paper_trading_offline_only=true`
- `paper_trading_no_real_order=true`
- `paper_trading_no_broker_api=true`
- `paper_trading_no_account_api=true`
- `paper_trading_no_order_api=true`
- `paper_trading_no_kiwoom_api=true`
- `paper_trading_no_ls_api=true`
- `paper_trading_no_live_prod=true`
- `paper_trading_no_network=true`
- `paper_trading_no_provider_api=true`
- `paper_trading_parquet_unsupported=true`

## 12. Tests

Planned focused tests:

- model construction and safety-flag enforcement
- `PaperOrderIntent` separation from real `OrderIntent`
- fill simulator deterministic next-bar behavior
- fill rejection on missing price/volume assumptions
- ledger update correctness
- position / risk limit blocking behavior
- performance report metric correctness
- gap taxonomy presence
- CLI success and failure paths
- CLI output-file local JSON behavior
- smoke assertions for v5.10 safety boundary

## 13. Non-Goals

- no Kiwoom mock API
- no LS mock API
- no broker adapter
- no broker mock adapter
- no real account read
- no real order
- no live trading
- no live inference
- no external market data fetch
- no advisory recommendation engine
- no production deployment
- no P/L backtest engine unification
- no portfolio simulator beyond the scoped internal deterministic paper ledger

## 14. Task-By-Task Execution Order

- [ ] Task 1: Define `PaperTrading*` model surface, safety flags, and gap taxonomy.
- [ ] Task 2: Add local JSON fixture loader and fail-closed safety guard.
- [ ] Task 3: Implement paper policy, decision, and `PaperOrderIntent` generation.
- [ ] Task 4: Implement deterministic fill simulator and rejection paths.
- [ ] Task 5: Implement paper ledger, position manager, and risk limit enforcement.
- [ ] Task 6: Implement performance report, safety report, gap report, and audit aggregation.
- [ ] Task 7: Wire CLI commands for simulate / ledger / performance / safety / gap outputs.
- [ ] Task 8: Update `system_smoke`, run targeted tests, run smoke, run full pytest if feasible, then commit/tag only after scope review.

## Scope Summary

v5.10 should introduce only an internal deterministic paper-only simulator layer on top of v5.9 neutral observation candidates. It should remain fully local, offline, networkless, and non-executable, with no relationship to real broker execution, real account state, live market data, or production deployment.
