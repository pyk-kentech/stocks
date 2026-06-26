# v11.0 Real-Data Paper Trading Evaluation Pipeline Design

## Goal

Build a local/offline real-data paper trading evaluation pipeline on top of the v10 feature-store and training-dataset surfaces.

v11 evaluates strategy behavior on local historical data and local manifests only. It does not perform live trading, broker paper trading, account access, provider fetches, model training, or autonomous execution.

This milestone stays within a single `v11.0` scope. Do not split into `v11.1` or `v11.2`.

## Scope Boundary

### In scope

- Consume v10 `FeatureStoreTrainingDatasetManifest`
- Consume v10 `FeatureStoreFeatureRow`
- Consume v10 `FeatureStoreTrainingRow`
- Consume v10 walk-forward and leakage reports
- Replay deterministic paper signals
- Simulate deterministic local fills
- Simulate local paper ledger and portfolio accounting
- Compute report-only metrics by trade, split, regime, and event window
- Emit integration, safety, and gap reports

### Out of scope

- Live trading
- Broker connection
- Broker paper trading API
- Account read
- Account mutation
- Account reconciliation
- Order submission
- Executable order output
- Provider/network calls
- Env/credential/API-key/token reads
- Model training
- Strategy optimization on test data
- Buy/sell recommendation output

## Public v11 Surface

The public v11 contract is a new `paper_evaluation_*` layer.

Required public models:

- `PaperEvaluationPlan`
- `PaperEvaluationSignal`
- `PaperEvaluationIntent`
- `PaperEvaluationFill`
- `PaperEvaluationLedgerEntry`
- `PaperEvaluationPosition`
- `PaperEvaluationPortfolioSnapshot`
- `PaperEvaluationTrade`
- `PaperEvaluationEquityCurve`
- `PaperEvaluationMetricsReport`
- `PaperEvaluationRiskReport`
- `PaperEvaluationSplitReport`
- `PaperEvaluationRegimeReport`
- `PaperEvaluationEventWindowReport`
- `PaperEvaluationSafetyReport`
- `PaperEvaluationGapReport`
- `PaperEvaluationPipelineResult`

`PaperEvaluationIntent` is non-executable by definition. It must not contain account ids, broker order ids, real routes, auth headers, or raw API payloads.

## Architecture

v11 is a new independent evaluation layer over v10 datasets. It does not extend `historical_paper_trading_*` as the v11 public contract and does not use `risk_adjusted_paper_eval_*` as the primary surface.

Execution stages:

`dataset gating -> signal replay -> fill simulation -> ledger simulation -> portfolio accounting -> metrics/reporting -> integration/safety/gap assembly`

Module boundaries:

- `paper_evaluation_models.py`
  - Canonical models, enums, statuses, safety flags
- `paper_evaluation_guard.py`
  - Metadata safety checks, marker blocking, path validation, dataset gate helpers
- `paper_evaluation_fixture.py`
  - Local JSON-only fixture loading
- `paper_evaluation_signal_engine.py`
  - Built-in simple signal replay and fixture override support
- `paper_evaluation_fill_engine.py`
  - Deterministic local fill simulation
- `paper_evaluation_ledger_engine.py`
  - Cash, position, fill, and trade state transitions
- `paper_evaluation_portfolio_engine.py`
  - Equity curve, exposure, drawdown, split-end liquidation handling
- `paper_evaluation_metrics_engine.py`
  - Trade, split, regime, event-window, and risk metrics
- `paper_evaluation_integration_engine.py`
  - Orchestration only
  - Calls stage engines in order
  - Assembles integration, safety, gap, and final pipeline outputs

`paper_evaluation_integration_engine.py` must not contain primary signal, fill, ledger, portfolio, or metrics calculation logic.

## Inputs

### Allowed inputs

- v10 training dataset manifest
- v10 feature rows
- v10 training rows
- v10 split plan
- v10 leakage report
- Local materialized v10 dataset files when available
- Local test or smoke fixtures shaped to the canonical v10 inputs
- Already-canonical v8/v9/v7 contexts carried through v10 rows

### Forbidden inputs

- Live provider data
- Real broker APIs
- Real account data
- Env vars
- Credentials
- API keys
- Tokens
- Network calls
- WebSocket streams
- Raw Kiwoom or LS account/order payloads
- Raw provider payloads unless already canonicalized into v8/v10-compatible local inputs

## Data Flow

### Entry paths

Two entry paths are allowed:

1. `v10 manifest-first path`
   - Source of truth is the v10 manifest, rows, split plan, and leakage report.
2. `local fixture fallback path`
   - Local JSON-only fixtures for smoke tests or bounded offline replay.

### Stage outputs

1. Dataset gating
   - Output: `PaperEvaluationPlan`
2. Signal replay
   - Output: `PaperEvaluationSignal`, `PaperEvaluationIntent`
3. Fill simulation
   - Output: `PaperEvaluationFill`
4. Ledger simulation
   - Output: `PaperEvaluationLedgerEntry`, `PaperEvaluationPosition`, `PaperEvaluationTrade`
5. Portfolio accounting
   - Output: `PaperEvaluationPortfolioSnapshot`, `PaperEvaluationEquityCurve`
6. Metrics and reports
   - Output: `PaperEvaluationMetricsReport`, `PaperEvaluationRiskReport`, `PaperEvaluationSplitReport`, `PaperEvaluationRegimeReport`, `PaperEvaluationEventWindowReport`, `PaperEvaluationSafetyReport`, `PaperEvaluationGapReport`
7. Final assembly
   - Output: `PaperEvaluationPipelineResult`

## Dataset Gating

Evaluation preconditions:

- v10 manifest exists
- v10 split plan exists
- v10 leakage report exists
- v10 leakage readiness is not `BLOCKED_LEAKAGE`
- Feature rows remain non-executable and report-only
- Labels remain separated from features
- No account/order/provider/auth markers are present
- Dataset profile is allowed

Allowed dataset profiles:

- `SMOKE_PROFILE`
- `DAILY_RESEARCH_PROFILE`
- `INTRADAY_CANDIDATE_PROFILE` only when bounded and partitioned

Blocked by default:

- `FULL_INTRADAY_PROFILE`

If dataset gating fails, v11 must return a blocked or rejected readiness without running promoted evaluation.

## Signal Replay Policy

v11 must not train a model.

Signal generation is hybrid:

- Default: built-in simple rule replay from canonical feature rows
- Optional: fixture-defined deterministic rule override

Built-in replay default side behavior:

- Default mode is long-only
- Allowed default sides: `BUY`, `HOLD`, `WATCH`, `NO_TRADE`
- Optional fixture opt-in may allow symbolic `SELL`
- Symbolic `SELL` is report-only and non-executable

Signal sources may use:

- v8 domestic snapshot features
- v9 macro/regime features
- v7.10 sizing/risk context
- v7.11 event-risk context
- v7.12 outlier/leadership context
- v7.13 controlled mock dry-run context
- deterministic local fixture directives

Signal generation must not use:

- `FeatureStoreTrainingRow.label_values`
- deterministic labels from v10
- future bars
- threshold fitting on validation/test/holdout

Signal statuses:

- `SIGNAL_READY`
- `WATCH_ONLY`
- `NO_TRADE`
- `BLOCKED_EVENT_RISK`
- `BLOCKED_MACRO_RISK`
- `BLOCKED_LIQUIDITY`
- `BLOCKED_LEAKAGE`
- `DATA_GAP`
- `REJECTED`

## Fill Simulation

Fill simulation is deterministic and local only.

Supported policies:

- `NEXT_BAR_OPEN`
- `NEXT_BAR_CLOSE`
- `VWAP_APPROX`
- `LIMIT_TOUCH_SIMULATED`
- `NO_FILL`

Default policy:

- `NEXT_BAR_OPEN`, unless a fixture explicitly selects another safe local policy

Rules:

- Fill price must come from local future path strictly after signal time
- Fill availability timestamp must be recorded
- If no safe future bar exists, emit `FILL_GAP`
- Same-bar post-decision price use is blocked as leakage unless explicitly safe and available
- Slippage, fee, tax, spread, and FX assumptions must be recorded
- No real broker order id or fill id

## Cost Model

v11 uses a local configurable cost model.

Supported cost components:

- commission
- tax
- slippage
- spread penalty
- FX cost when relevant

Default domestic KR behavior:

- Use fixture/default local assumptions
- Record assumptions on the fill, ledger, or metrics lineage
- If safe assumptions are unavailable, emit `COST_MODEL_GAP`

Outputs:

- gross PnL
- net PnL
- fees
- taxes
- slippage estimate
- realized return
- risk-adjusted return when enough local inputs exist

## Ledger and Portfolio Simulation

The ledger is fully simulated.

Tracked state:

- starting cash
- simulated cash
- simulated positions
- fills
- realized PnL
- unrealized PnL
- equity curve
- exposure
- drawdown
- turnover

Rules:

- No real account
- No reconciliation to external balance
- No broker position source
- No margin unless explicitly supported by local fixture
- Insufficient simulated cash blocks simulated buy
- Duplicate open-position behavior must be explicit
- Forced close behavior must be explicit
- Open positions at split end use `force_close_at_next_available_bar`

The split-end liquidation default is fixed:

- `force_close_at_next_available_bar`

This prevents carry across walk-forward boundaries and preserves split isolation.

## Unlabeled Dataset Policy

If a dataset is unlabeled:

- Allow signal replay
- Allow fill simulation
- Allow ledger simulation
- Allow portfolio accounting
- Block or downgrade realized-return-dependent metrics

Default readiness impact:

- `LABEL_GAP`
- or `RESEARCH_ONLY` when the rest of the pipeline is still usable for offline sanity checks

This keeps execution-path and accounting-path validation available without overstating realized performance.

## Metrics

Report-only metrics:

- trade count
- win rate
- average return
- median return
- gross return
- net return
- max drawdown
- volatility
- Sharpe-like ratio when enough samples exist
- profit factor
- average holding period
- exposure time
- turnover
- fill rate
- blocked signal count
- gap count

Split-level metrics:

- `TRAIN`
- `VALIDATION`
- `TEST`
- `PAPER_FORWARD`
- `HOLDOUT`

Regime and event metrics:

- by macro regime
- by VIX state
- by USD/KRW pressure
- by event-window status
- by outlier sleeve vs non-outlier route
- by liquidity bucket

No metric may be framed as a live trading guarantee.

## Walk-Forward and Anti-Overfit Guard

v11 uses the v10 split plan as-is.

Rules:

- Preserve chronological splits
- No random shuffle
- No fitting on validation/test/holdout
- No threshold optimization on test data
- Repeated test tuning warning must surface
- Evaluation on test/holdout remains report-only
- If split metadata is missing or inconsistent, emit `DATA_SNOOPING_GAP`

## Safety Guard

The guard layer must detect and block:

- provider/network markers
- env reads
- credential/API-key/token markers
- authorization headers
- account numbers
- broker order ids
- executable order objects
- real broker route markers
- Kiwoom or LS account/order API markers
- live/prod trading markers
- WebSocket markers
- unsafe file paths
- datasets with `BLOCKED_LEAKAGE`
- current-survivor-only promoted evaluation
- test split optimization
- label-derived signal fields
- future data in signal generation

Hard blocks:

- `LEAKAGE_BLOCKED`
- `BLOCKED_PROVIDER_CALL`
- `BLOCKED_ACCOUNT_OR_ORDER`
- `BLOCKED_EXECUTABLE_OUTPUT`
- `REJECTED`

Downgraded or reportable states:

- `LABEL_GAP`
- `FILL_GAP`
- `COST_MODEL_GAP`
- `DATA_GAP`
- `DATA_SNOOPING_GAP`
- `RESEARCH_ONLY`

## Status Enums

Required readiness statuses:

- `PAPER_EVALUATION_READY`
- `PLAN_READY`
- `SIGNAL_REPLAY_READY`
- `FILL_SIMULATION_READY`
- `LEDGER_READY`
- `PORTFOLIO_READY`
- `METRICS_READY`
- `RISK_REPORT_READY`
- `SPLIT_REPORT_READY`
- `REGIME_REPORT_READY`
- `EVENT_WINDOW_REPORT_READY`
- `INTEGRATION_READY`
- `LABEL_GAP`
- `FILL_GAP`
- `COST_MODEL_GAP`
- `DATA_GAP`
- `LEAKAGE_BLOCKED`
- `DATA_SNOOPING_GAP`
- `BLOCKED_PROVIDER_CALL`
- `BLOCKED_ACCOUNT_OR_ORDER`
- `BLOCKED_EXECUTABLE_OUTPUT`
- `RESEARCH_ONLY`
- `REJECTED`

## Integration Reports

### v10 integration

- Dataset manifest consumption readiness
- Walk-forward plan consumption readiness
- Leakage report consumption readiness
- Local materialization/backend capability propagation

### v9 integration

- Performance by macro regime
- Performance by event windows
- Macro provider-gap propagation into evaluation context

### v8 integration

- Domestic stock snapshot feature consumption readiness
- Liquidity and outlier context usage
- Local chart-path compatibility for fills and marks

### v7.10 integration

- Position sizing context usage as report-only input
- No executable sizing output

### v7.11 integration

- Event-risk block/reduce behavior

### v7.12 integration

- Outlier and leadership sleeve behavior

### v7.13 integration

- Controlled mock dry-run compatibility check
- No live execution path

## CLI Surface

Add:

- `paper-evaluation-plan-report`
- `paper-evaluation-signal-replay-report`
- `paper-evaluation-fill-simulation-report`
- `paper-evaluation-ledger-report`
- `paper-evaluation-portfolio-report`
- `paper-evaluation-metrics-report`
- `paper-evaluation-risk-report`
- `paper-evaluation-split-report`
- `paper-evaluation-regime-report`
- `paper-evaluation-event-window-report`
- `paper-evaluation-integration-report`
- `paper-evaluation-safety-report`
- `paper-evaluation-gap-report`

CLI behavior:

- report-only by default
- local fixture or local manifest input only
- no provider fetch
- no env read
- no credential read
- no broker/account/order API
- no executable order output
- no model training
- no strategy optimization
- output redacted JSON

## System Smoke

Extend `system_smoke.py` with a local v11 fixture path that validates:

- v10 manifest-style input loading
- signal replay
- fill simulation
- ledger simulation
- metrics report generation
- integration report generation
- safety report generation
- no provider/network/account/order/env/training/broker-paper actions
- no executable output

## Files

Create or modify:

- `docs/superpowers/plans/2026-06-18-v11-real-data-paper-trading-evaluation-pipeline.md`
- `src/stock_risk_mcp/paper_evaluation_models.py`
- `src/stock_risk_mcp/paper_evaluation_guard.py`
- `src/stock_risk_mcp/paper_evaluation_fixture.py`
- `src/stock_risk_mcp/paper_evaluation_signal_engine.py`
- `src/stock_risk_mcp/paper_evaluation_fill_engine.py`
- `src/stock_risk_mcp/paper_evaluation_ledger_engine.py`
- `src/stock_risk_mcp/paper_evaluation_portfolio_engine.py`
- `src/stock_risk_mcp/paper_evaluation_metrics_engine.py`
- `src/stock_risk_mcp/paper_evaluation_integration_engine.py`
- `src/stock_risk_mcp/cli.py`
- `src/stock_risk_mcp/system_smoke.py`
- `tests/test_paper_evaluation_models.py`
- `tests/test_paper_evaluation_guard.py`
- `tests/test_paper_evaluation_signal_engine.py`
- `tests/test_paper_evaluation_fill_engine.py`
- `tests/test_paper_evaluation_ledger_engine.py`
- `tests/test_paper_evaluation_metrics_engine.py`
- `tests/test_paper_evaluation_integration_cli.py`
- `tests/test_system_smoke.py`

## Testing

Use only local fixtures and local v10-style manifests.

Focused tests must cover:

- plan, signal, intent, fill, ledger, portfolio, metrics, status models
- guard marker blocking
- label-derived signal blocking
- unsafe path blocking
- next-bar fill simulation
- fill gap on missing future bar
- same-bar leakage block
- cash and position transitions
- insufficient simulated cash block
- duplicate position policy
- forced close policy
- equity curve generation
- split/regime/event-window metrics
- v10 manifest integration
- CLI report output
- system smoke offline v11 coverage

## Verification

Run:

```bash
python3.11 -m pytest \
  tests/test_paper_evaluation_models.py \
  tests/test_paper_evaluation_guard.py \
  tests/test_paper_evaluation_signal_engine.py \
  tests/test_paper_evaluation_fill_engine.py \
  tests/test_paper_evaluation_ledger_engine.py \
  tests/test_paper_evaluation_metrics_engine.py \
  tests/test_paper_evaluation_integration_cli.py \
  tests/test_system_smoke.py \
  -q

python3.11 -m pytest tests/test_system_smoke.py -q

python3.11 -m pytest -q
```

If all pass:

```bash
git add \
  docs/superpowers/plans/2026-06-18-v11-real-data-paper-trading-evaluation-pipeline.md \
  src/stock_risk_mcp/paper_evaluation_models.py \
  src/stock_risk_mcp/paper_evaluation_guard.py \
  src/stock_risk_mcp/paper_evaluation_fixture.py \
  src/stock_risk_mcp/paper_evaluation_signal_engine.py \
  src/stock_risk_mcp/paper_evaluation_fill_engine.py \
  src/stock_risk_mcp/paper_evaluation_ledger_engine.py \
  src/stock_risk_mcp/paper_evaluation_portfolio_engine.py \
  src/stock_risk_mcp/paper_evaluation_metrics_engine.py \
  src/stock_risk_mcp/paper_evaluation_integration_engine.py \
  src/stock_risk_mcp/cli.py \
  src/stock_risk_mcp/system_smoke.py \
  tests/test_paper_evaluation_models.py \
  tests/test_paper_evaluation_guard.py \
  tests/test_paper_evaluation_signal_engine.py \
  tests/test_paper_evaluation_fill_engine.py \
  tests/test_paper_evaluation_ledger_engine.py \
  tests/test_paper_evaluation_metrics_engine.py \
  tests/test_paper_evaluation_integration_cli.py \
  tests/test_system_smoke.py

git commit -m "Implement real-data paper trading evaluation pipeline"
git tag v11.0.0-real-data-paper-trading-evaluation-pipeline
```

## Hard Invariants

- No live trading
- No real order
- No broker paper trading API
- No account read
- No account mutation
- No account reconciliation
- No provider/network call
- No env/credential/API-key/token read
- No raw authorization header
- No WebSocket
- No executable order output
- No buy/sell recommendation output
- No model training
- No strategy optimization on test data
- No future data leakage
- No label-derived signal
- No current-survivor-only promoted evaluation
- No unsafe path writes

## Implementation Notes

- Reuse existing paper-eval or historical-paper-trading code only as internal reference.
- Keep v11 public models, reports, CLI commands, and safety contracts under `paper_evaluation_*`.
- The milestone ends at local/offline evaluation reports over real/captured/local historical data.
