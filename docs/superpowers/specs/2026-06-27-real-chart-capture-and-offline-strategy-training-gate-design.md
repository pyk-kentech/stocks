## v15.0 Real Chart Capture And Offline Strategy Training Gate Design

### Milestone

- Version: `v15.0`
- Final tag: `v15.0.0-real-chart-capture-and-offline-strategy-training-gate`
- Version discipline: do not create `v14.1`, `v14.2`, `v15.1`, `v15.2`, or any extra milestone

### Starting Point

Current confirmed state before v15:

- v14.0 is complete
- Commit: `777fb19e16b9b37f6ccd908d88679b19b8414928`
- Tag: `v14.0.0-historical-market-data-capture-raw-data-lake-pipeline`
- Full pytest: `2852 passed, 1 warning`
- Working tree: clean

Important correction:

- v14 created the `historical_market_data_*` layer, manual/mocked chart import, raw lake, normalized OHLCV rows for `KA10080` and `KA10081`, coverage/manifest, v8/v10/v11 integration reports, and strategy-research-readiness report
- v14 did not create a real Kiwoom historical chart network capture runner
- therefore v15 must first add a strictly read-only, opt-in, bounded real chart capture runner to `historical_market_data_*`
- then v15 must add a new independent `offline_strategy_*` layer

### Goal

After v15 the user should be able to:

1. Run an explicit local opt-in Kiwoom read-only historical chart capture outside pytest
2. Capture only historical chart data through Kiwoom chart APIs
3. Store redacted raw chart responses in the historical raw lake
4. Normalize `KA10080` and `KA10081` into canonical OHLCV
5. Generate `HistoricalOhlcvDatasetManifest`
6. Feed that manifest into an offline strategy training and validation layer
7. Run offline strategy template evaluation, bounded parameter search, walk-forward validation, conservative backtest, metrics, and promotion gate
8. Produce offline-only promoted strategy candidates
9. Never produce executable orders, live trading actions, account reads, or broker route output

### Hard Safety Boundary

The whole v15 milestone is fail-closed around the following rules:

- no live trading
- no real order execution
- no account read
- no account mutation
- no account/order API
- no executable order output
- no broker route
- no production paper trading
- no automatic buy/sell advisory
- no real provider/network call in pytest
- no API key/token/credential read in pytest
- no raw API key/token/header printing
- no raw API key/token/header storage
- no background polling
- no unbounded data capture
- no unbounded parameter search
- no default full-intraday all-symbol capture

### API Key Scope

API key use is allowed only for the corrective real chart capture runner in `historical_market_data_*`.

Allowed:

- only outside pytest
- only under explicit local opt-in
- only through credential reference paths
- only for Kiwoom historical chart APIs `KA10080` and `KA10081`
- only for bounded read-only historical chart capture

Forbidden:

- any account/order API use
- any API key use inside `offline_strategy_*`
- any provider/network call inside `offline_strategy_*`
- any provider connectivity check inside `offline_strategy_*`
- any raw token/key/header output or storage

`offline_strategy_*` remains fully offline and manifest-only:

- consumes `HistoricalOhlcvDatasetManifest`
- may consume direct normalized OHLCV rows in tests and smoke
- does not read API keys
- does not call Kiwoom
- does not call network
- does not touch account/order/broker APIs
- does not output executable orders

### Architecture

v15 is split into two independent layers.

#### 1. Corrective `historical_market_data_*` real capture layer

Purpose:

- bounded, read-only, explicit opt-in Kiwoom historical chart capture only

Responsibilities:

- preflight guard
- credential-ref validation
- request preview
- bounded chart execution
- continuation/page loop with caps
- redacted raw lake persistence
- normalization into canonical OHLCV
- coverage/completeness/freshness update
- manifest generation
- audit/report output

This layer is the only place where credential refs may be read, and only after all guards pass.

#### 2. New `offline_strategy_*` offline research layer

Purpose:

- strategy template evaluation, bounded parameter search, walk-forward validation, conservative backtest, metric computation, and promotion gate

Responsibilities:

- dataset compatibility checks
- indicator calculation
- signal generation
- bounded grid search
- anchored and rolling chronological walk-forward
- conservative next-bar fill simulation
- metric computation
- stability-first promotion gate
- artifact manifest and integration reports

This layer is fully offline and does not know about Kiwoom credentials, provider connectivity, account data, or broker routing.

### Part A: Corrective Real Read-Only Historical Chart Capture

Create or modify:

- `src/stock_risk_mcp/historical_market_data_real_capture.py`
- `src/stock_risk_mcp/historical_market_data_transport.py`
- `src/stock_risk_mcp/historical_market_data_credential_ref.py`
- `src/stock_risk_mcp/historical_market_data_capture_runner.py`
- `src/stock_risk_mcp/historical_market_data_models.py`
- `src/stock_risk_mcp/historical_market_data_guard.py`
- `src/stock_risk_mcp/historical_market_data_capture_plan_engine.py`
- `src/stock_risk_mcp/historical_market_data_raw_lake.py`
- `src/stock_risk_mcp/historical_market_data_normalizer.py`
- `src/stock_risk_mcp/historical_market_data_manifest_engine.py`
- `src/stock_risk_mcp/historical_market_data_integration_engine.py`
- `src/stock_risk_mcp/cli.py`
- `src/stock_risk_mcp/system_smoke.py`

Add tests:

- `tests/test_historical_market_data_real_capture.py`
- `tests/test_historical_market_data_transport.py`
- `tests/test_historical_market_data_credential_ref.py`
- `tests/test_historical_market_data_capture_runner.py`
- update existing v14 tests as needed
- update `tests/test_system_smoke.py`

#### A1. Real capture API scope

Allow real network capture only for schema-ready chart APIs:

- `KA10081` daily chart
- `KA10080` minute chart

Continue treating the following as non-ready unless exact local schema evidence later exists:

- `KA10079`
- `KA10082`
- `KA10083`
- `KA10094`

Known current request/transport evidence:

- method: `POST`
- path: `/api/dostk/chart`
- headers:
  - `api-id`
  - `authorization: Bearer <TOKEN_REF_ONLY>`
  - `cont-yn`
  - `next-key`
- continuation:
  - `cont-yn`
  - `next-key`
- `KA10081` request body:
  - `stk_cd`
  - `base_dt`
  - `upd_stkpc_tp`
- `KA10080` request body:
  - `stk_cd`
  - `tic_scope`
  - `upd_stkpc_tp`
  - `base_dt`

If exact casing or enum naming differs in repo-local evidence, follow existing repo code.

#### A2. Credential policy

Implement credential references rather than raw credential storage.

Allowed:

- CLI accepts credential-ref path only in explicit local opt-in mode
- key files may be read only outside pytest
- reports may include redacted metadata only:
  - `credential_ref_present: true`
  - `credential_policy: KEY_REF_ONLY`
  - `redaction_status: PASSED`
  - `auth_header_present: true/false`

Forbidden:

- reading credential files in pytest
- reading environment variables in pytest
- printing tokens, app keys, secret keys, or auth headers
- storing auth headers in raw lake, manifest, audit, or logs
- storing account numbers or order IDs
- using credentials for non-chart endpoints

#### A3. Explicit opt-in requirements

Real chart capture is blocked unless all are true:

- `allow_real_chart_capture = true`
- `acknowledge_readonly_only = true`
- `acknowledge_no_orders = true`
- `acknowledge_user_initiated = true`
- `acknowledge_rate_limit_and_capacity = true`
- `acknowledge_credential_redaction = true`
- `credential_ref` is provided
- runtime is not pytest
- API ID is allowlisted and schema-ready
- symbols are bounded
- date range is bounded
- interval/profile is bounded
- max request count is bounded
- max continuation pages is bounded
- output root is safe
- raw lake redaction policy passes
- no account/order markers are detected
- no executable output is produced

If any condition fails:

- no network call
- no credential read
- blocked decision only
- exact blocked reasons in output

#### A4. Capture profiles

Support:

- `SMOKE_PROFILE`
- `DAILY_RESEARCH_PROFILE`
- `INTRADAY_CANDIDATE_PROFILE`
- `FULL_INTRADAY_DISABLED`

Rules:

- `SMOKE_PROFILE`: tests only, mocked/local only, no real network
- `DAILY_RESEARCH_PROFILE`: bounded daily bars, allowed for real opt-in local capture
- `INTRADAY_CANDIDATE_PROFILE`: bounded candidate symbols only, bounded minute bars, explicit capacity acknowledgment required
- `FULL_INTRADAY_DISABLED`: always blocked by default, never allowed in tests

#### A5. Transport model

Implement:

- `HistoricalMarketDataTransport`
- `MockHistoricalMarketDataTransport`
- `RealKiwoomChartTransport`

Rules:

- mock transport is used in tests
- real transport is unavailable in pytest
- real transport is constructed only after opt-in guard passes
- real transport supports only chart endpoint and schema-ready API IDs
- bounded timeout and retry policy
- no infinite retry
- no websocket
- no streaming
- no account/order endpoint
- no background scheduler

#### A6. Real capture runner responsibilities

Implement:

- capture plan validation
- opt-in validation
- credential-ref validation
- bounded task execution
- continuation/page loop with max page cap
- response redaction scan
- raw lake write
- normalization
- coverage update
- manifest generation
- audit record generation
- final capture result

Runner outputs:

- `HistoricalChartCaptureRunResult`
- `HistoricalChartCaptureRunAudit`
- `HistoricalOhlcvDatasetManifest`
- coverage report
- safety report
- gap report

Rules:

- do not store raw auth headers
- do not store raw tokens
- do not store account/order data
- do not crash whole run because one symbol fails
- do not retry indefinitely

#### A7. Real capture CLI

Add:

- `historical-market-data-real-capture-preflight-report`
- `historical-market-data-real-capture-plan-report`
- `historical-market-data-real-capture-run`
- `historical-market-data-real-capture-audit-report`

CLI rules:

- preflight and plan commands are report-only
- run command requires explicit opt-in flags
- run command requires credential-ref
- run command requires bounded symbol/date/interval/profile
- run command refuses pytest runtime
- run command refuses account/order API IDs
- output is redacted JSON
- prints manifest path and summary only
- never prints token/header/key values
- never prints executable order output

### Part B: Offline Strategy Training / Parameter Search / Promotion Gate

Create:

- `src/stock_risk_mcp/offline_strategy_models.py`
- `src/stock_risk_mcp/offline_strategy_guard.py`
- `src/stock_risk_mcp/offline_strategy_fixture.py`
- `src/stock_risk_mcp/offline_strategy_template_catalog.py`
- `src/stock_risk_mcp/offline_strategy_indicator_engine.py`
- `src/stock_risk_mcp/offline_strategy_signal_engine.py`
- `src/stock_risk_mcp/offline_strategy_parameter_space.py`
- `src/stock_risk_mcp/offline_strategy_dataset_compatibility_engine.py`
- `src/stock_risk_mcp/offline_strategy_walk_forward_engine.py`
- `src/stock_risk_mcp/offline_strategy_backtest_engine.py`
- `src/stock_risk_mcp/offline_strategy_metric_engine.py`
- `src/stock_risk_mcp/offline_strategy_promotion_gate.py`
- `src/stock_risk_mcp/offline_strategy_training_plan_engine.py`
- `src/stock_risk_mcp/offline_strategy_artifact_manifest.py`
- `src/stock_risk_mcp/offline_strategy_integration_engine.py`

Modify:

- `src/stock_risk_mcp/cli.py`
- `src/stock_risk_mcp/system_smoke.py`

Add tests:

- `tests/test_offline_strategy_models.py`
- `tests/test_offline_strategy_guard.py`
- `tests/test_offline_strategy_template_catalog.py`
- `tests/test_offline_strategy_indicator_engine.py`
- `tests/test_offline_strategy_signal_engine.py`
- `tests/test_offline_strategy_parameter_space.py`
- `tests/test_offline_strategy_dataset_compatibility_engine.py`
- `tests/test_offline_strategy_walk_forward_engine.py`
- `tests/test_offline_strategy_backtest_engine.py`
- `tests/test_offline_strategy_metric_engine.py`
- `tests/test_offline_strategy_promotion_gate.py`
- `tests/test_offline_strategy_training_plan_engine.py`
- `tests/test_offline_strategy_integration_cli.py`
- update `tests/test_system_smoke.py`

#### B1. Core models

Create:

- `OfflineStrategyStatus`
- `OfflineStrategyFamily`
- `OfflineStrategyTemplateId`
- `OfflineStrategyDataRequirement`
- `OfflineStrategySupportStatus`
- `OfflineStrategyDirection`
- `OfflineStrategySignalAction`
- `OfflineStrategyExitReason`
- `OfflineStrategyRiskModel`
- `OfflineStrategyAssetLiquidityProfile`
- `OfflineStrategyParameter`
- `OfflineStrategyParameterSpace`
- `OfflineStrategyTemplate`
- `OfflineStrategyCandidate`
- `OfflineStrategySignal`
- `OfflineStrategyTradeIntent`
- `OfflineStrategySimulatedTrade`
- `OfflineStrategyBacktestResult`
- `OfflineStrategyMetricSummary`
- `OfflineStrategyWalkForwardSplit`
- `OfflineStrategyWalkForwardResult`
- `OfflineStrategyPromotionGateConfig`
- `OfflineStrategyPromotionDecision`
- `OfflineStrategyDatasetCompatibilityReport`
- `OfflineStrategyTrainingLaunchPlan`
- `OfflineStrategyArtifactManifest`
- `OfflineStrategySafetyReport`
- `OfflineStrategyGapReport`
- `OfflineStrategyPipelineResult`

Hard rule:

`OfflineStrategyTradeIntent` must remain:

- non-executable
- offline-only
- simulated-only
- report-only

It must not contain:

- broker order IDs
- account IDs
- executable order payloads
- raw provider credentials
- live routing fields

#### B2. Strategy families

Implement these public short-term strategy families as parameterized templates:

1. `VOLUME_PULLBACK_LONG`
- volume expansion
- long bullish / strong body candle
- pullback wait
- reclaim or reversal confirmation
- simulated long entry after confirmation
- stop and target simulation

Parameters:

- `volume_lookback`
- `volume_multiplier`
- `body_ratio_threshold`
- `candle_range_threshold`
- `pullback_pct_min`
- `pullback_pct_max`
- `pullback_max_bars`
- `reclaim_threshold`
- `trend_filter_mode`
- `stop_basis`
- `target_r_multiple`
- `max_holding_bars`

2. `UPPER_WICK_REVERSAL`
- prior run-up
- large upper wick
- volume expansion
- weak close location
- in long-only mode emits only:
  - `AVOID_LONG`
  - `RISK_WARNING`
  - `RESEARCH_ONLY`
  - `BLOCKED`

Parameters:

- `prior_runup_lookback`
- `prior_runup_pct`
- `upper_wick_ratio`
- `close_location_threshold`
- `volume_lookback`
- `volume_multiplier`
- `confirmation_bars`
- `stop_above_wick_high_buffer`
- `target_r_multiple`
- `max_holding_bars`

3. `RSI_OVERSOLD_REBOUND`
- RSI oversold
- RSI reclaim or confirmation candle
- optional trend filter
- stop and target simulation

Parameters:

- `rsi_period`
- `oversold_threshold`
- `rebound_threshold`
- `confirmation_mode`
- `trend_filter_mode`
- `stop_basis`
- `target_r_multiple`
- `max_holding_bars`

4. `MACD_RSI_MOMENTUM`
- MACD golden cross
- RSI between 50 and 70
- RSI below 50 delayed entry after RSI 50 reclaim
- optional overbought second-leg variant
- nearest low stop
- reward:risk `1:2`
- partial take-profit option
- exit on MACD dead cross, RSI 50 loss, or breakeven stop

Parameters:

- `macd_fast`
- `macd_slow`
- `macd_signal`
- `rsi_period`
- `rsi_midline`
- `rsi_upper`
- `rsi_lower`
- `allow_overbought_second_leg`
- `partial_take_profit_mode`
- `stop_basis`
- `target_r_multiple`
- `max_holding_bars`

#### B3. Promotion direction policy

Default promotion target is `LONG_ONLY`.

Rules:

- long-entry strategies may be evaluated by the normal promotion gate
- short/reversal/bearish templates may exist only for research, risk warning, or avoid-long signals
- short-side templates must not be promoted by default
- short-side templates must not emit executable short signals
- do not create borrow, margin, or short execution assumptions
- do not create executable order output
- do not introduce account/order/broker dependencies

#### B4. Indicator and signal layer

Reuse existing repo-local technical evidence where safe:

- MACD from existing MACD calculation logic
- RSI from existing RSI calculation logic
- HMA from existing HMA calculation logic
- divergence from existing divergence logic
- bar geometry, volume expansion, pullback range, reclaim checks, stop/target geometry in new offline indicator and signal engines

Signal rules:

- signal from bar `T` enters on bar `T+1` or later by default
- same-bar perfect fill is forbidden
- signals must remain simulated and advisory only
- bearish templates in long-only mode emit risk-filter style actions rather than short-entry candidates

#### B5. Parameter search policy

Default search mode is small bounded grid search only.

Rules:

- no random search
- no Bayesian search
- no unbounded cartesian expansion
- template-specific max combination caps
- overflow leads to reduced grid, `RESEARCH_ONLY`, or `BLOCKED`

#### B6. Input surface

Default public input:

- `HistoricalOhlcvDatasetManifest`

Also allow:

- direct normalized OHLCV row fixtures for tests and smoke

Rules:

- manifest-first public contract
- direct row input is allowed for local deterministic testing
- if manifest and direct row data conflict, take the more conservative outcome:
  - `CONFLICT`
  - `RESEARCH_ONLY`
  - `BLOCKED`

### Walk-Forward, Backtest, Metrics, And Promotion Gate

#### C1. Walk-forward split policy

Support both:

- `ANCHORED_CHRONOLOGICAL_WALK_FORWARD`
- `ROLLING_CHRONOLOGICAL_WALK_FORWARD`

Default promotion mode:

- anchored chronological walk-forward

Anchored rules:

- used for main promotion gate
- training start date fixed
- training end date expands forward
- validation/test windows move forward chronologically
- embargo must apply between train/validation/test boundaries
- no shuffle split
- no random split
- no future leakage

Rolling rules:

- allowed only as explicit opt-in
- may be covered in tests by fixture-only smoke
- used for sensitivity and regime robustness analysis
- cannot alone promote a strategy
- if anchored fails but rolling passes:
  - `WATCHLIST_ONLY_ROLLING_ONLY`
  - `RESEARCH_ONLY`
  - never `PROMOTED_OFFLINE_CANDIDATE`

If anchored and rolling disagree:

- choose the more conservative decision

Recommended statuses:

- `WALK_FORWARD_ANCHORED_READY`
- `WALK_FORWARD_ROLLING_RESEARCH_ONLY`
- `BLOCKED_NON_CHRONOLOGICAL_SPLIT`
- `BLOCKED_LEAKAGE_RISK`
- `WATCHLIST_ONLY_ROLLING_ONLY`

#### C2. Conservative fill policy

Default fill model is conservative next-bar fill for all assets.

This is an execution-assumption policy, not a universe restriction.

Allowed asset/liquidity profiles:

- `LARGE_CAP`
- `MID_CAP`
- `SMALL_CAP`
- `ETF`
- `HIGH_VOLATILITY_MOMENTUM`
- `LOW_LIQUIDITY_WARNING`

Rules:

- do not restrict strategy universe to ETFs
- do not downgrade strategy only because the asset is volatile
- volatile stocks are allowed
- same-bar perfect fill remains forbidden
- slippage and fees are configurable
- optional higher slippage profile for high-volatility and small-cap symbols
- report liquidity and volatility warnings
- do not automatically exclude individual stocks unless:
  - coverage is insufficient
  - liquidity assumptions are unsupported
  - spread/slippage assumptions are insufficient
  - data quality is insufficient

#### C3. Dataset compatibility checks

Before backtest and promotion:

- no leakage flags
- no unsupported data requirement
- no manifest coverage gap
- no missing required OHLCV fields
- no unsupported interval
- no label-horizon-like hold window gap
- no account/order/live dependency
- no executable output fields

Failing candidates are blocked or downgraded before simulation.

#### C4. Metrics

Compute at minimum:

- trade count
- out-of-sample trade count
- minimum fold count coverage
- cumulative return
- average trade return
- expectancy
- profit factor
- win rate
- max drawdown
- stop-hit rate
- loss clustering warning
- exposure if configured
- turnover if configured
- split-by-split train/validation/test summaries

#### C5. Promotion gate priority

Use stability-first default priority:

1. Safety and data validity
   - no leakage flags
   - no unsupported data requirement
   - no manifest coverage gap
   - no label horizon gap or equivalent hold-window gap
   - no account/order/live dependency
   - no executable output
2. Minimum statistical validity
   - minimum trade count
   - minimum walk-forward folds
   - sufficient out-of-sample samples
   - no single-trade or tiny-sample promotion
3. Walk-forward consistency
   - must not work in only one split
   - require consistent validation/test behavior across folds
   - reject unstable train/test gaps
   - reject strategies that collapse out-of-sample
4. Risk control
   - maximum drawdown cap
   - stop-hit rate and loss clustering warnings
   - exposure and turnover limits if configured
   - reject high drawdown even if total return is high
5. Quality of returns
   - minimum profit factor
   - minimum expectancy
   - minimum average trade return if configured
   - optional minimum win rate, but win rate must not override expectancy and risk
6. Profitability
   - cumulative return checked only after earlier gates
   - high total return alone must never promote a strategy

Possible results:

- `PROMOTED_OFFLINE_CANDIDATE`
- `WATCHLIST_ONLY`
- `WATCHLIST_ONLY_ROLLING_ONLY`
- `RESEARCH_ONLY`
- `BLOCKED`
- `REJECTED`

### CLI Surface

Historical capture corrective CLI:

- `historical-market-data-real-capture-preflight-report`
- `historical-market-data-real-capture-plan-report`
- `historical-market-data-real-capture-run`
- `historical-market-data-real-capture-audit-report`

Offline strategy CLI:

- `offline-strategy-template-catalog-report`
- `offline-strategy-dataset-compatibility-report`
- `offline-strategy-training-plan-report`
- `offline-strategy-walk-forward-report`
- `offline-strategy-backtest-report`
- `offline-strategy-metric-report`
- `offline-strategy-promotion-gate-report`
- `offline-strategy-artifact-manifest-report`
- `offline-strategy-safety-report`
- `offline-strategy-gap-report`

Rules:

- offline strategy commands remain local/offline/report-only
- real capture commands are the only commands that may cross a network boundary
- no CLI command may print raw key/token/header material
- no CLI command may print executable order output

### System Smoke

Add two v15 smoke branches:

1. historical real-capture smoke
- mock transport only
- no real network
- no credential file read
- preflight, plan, run, audit shapes validated

2. offline strategy smoke
- tiny OHLCV fixture or manifest fixture
- template catalog, bounded parameter expansion, anchored walk-forward, conservative backtest, promotion gate, and artifact manifest validated

### Verification Plan

Run:

1. focused unit tests
   - models
   - guards
   - credential-ref redaction
   - transport boundary
   - indicator logic
   - signal rules
   - parameter cap enforcement
   - dataset compatibility
   - anchored and rolling split behavior
   - conservative fill behavior
   - metrics
   - promotion gate decisions
2. focused integration tests
   - historical capture runner with mock transport
   - offline strategy CLI from local fixture
   - manifest-to-strategy pipeline path
3. `system_smoke`
4. full `pytest`

### Expected Outcome

At the end of v15:

- user can explicitly run bounded real read-only Kiwoom historical chart capture outside pytest
- captured responses are redacted and stored safely
- normalized OHLCV manifests are generated for downstream use
- offline strategy evaluation can start immediately from a supplied v14/v15 OHLCV manifest
- strategy promotion remains offline-only, non-executable, long-only by default, and stability-first
