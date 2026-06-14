# Work Summary

This document summarizes the work completed so far, excluding the contents of any installed skills.

## Project

Project path:

```text
D:\KENTECH\stock\stock-risk-mcp
```

The project started as a local MVP for evaluating stock trade proposals. The
current implementation does not execute real orders. Its long-term goal is an
automated-buying and automated-selling, risk-capped trading research and
execution platform. Live execution is deliberately deferred until a separate
stage adds strong risk gates, a kill switch, explicit enablement, and complete
audit logging. A deterministic risk engine remains the final gate.

## Long-Term Execution Roadmap

The project is divided into four stages:

1. **Research / Paper Trading**
   - implemented scan, Provider Pack, paper trading, replay, report, and
     dashboard layers
2. **Realtime Monitoring**
   - shallow whole-universe monitoring, automatic Hot Watchlist updates, and
     intraday candidate signals
   - no real orders in this stage
3. **Execution Intent Layer**
   - strategies create auditable `OrderIntent` records instead of directly
     placing orders
   - every BUY, SELL, STOP, TAKE_PROFIT, or REDUCE intent must pass the risk
     gate
4. **Live Execution Layer**
   - broker integration remains default-off and requires explicit activation
   - paper and sandbox validation must precede live use

Planned implementation order:

```text
v2.8.0 Real-Time Market Data Foundation + Dynamic Watchlist Engine
v2.9.0 Order Intent / Execution Gate Foundation
v3.0.0 Broker Sandbox Execution Adapter
v3.1.0 Live Trading Guardrails
```

The `v2.8.0` scope remains realtime monitoring and dynamic watchlists only. It
does not add order, broker account, balance, or position endpoints.

Execution safety contracts are permanent:

- strategy, agent, and optimizer cannot modify hard-risk rules
- margin, options, and market orders are disabled by default
- stop-loss protection cannot be disabled
- maximum daily loss, maximum single position, and minimum cash are enforced
- a kill switch is mandatory
- every OrderIntent and execution result is stored as a DB audit record
- live trading is default-off
- paper, sandbox, and live modes remain explicitly separated

## Initial MVP

Created the `stock-risk-mcp` Python project with:

- Python package under `src/stock_risk_mcp`
- `pyproject.toml`
- default YAML policy under `policies/default_policy.yaml`
- Pydantic v2 models
- mock adapters
- pure Python service
- CLI entry point
- MCP wrapper with safe fallback when FastMCP is not installed
- pytest test suite

Implemented core models:

- `TradeProposal`
- `MarketSnapshot`
- `CompanyRisk`
- `PortfolioState`
- `TossSignal`
- `RiskPolicy`
- `RiskResult`

Implemented risk behavior:

- hard block rules
- soft scoring
- `ALLOW`, `REVIEW`, `BLOCK` decision logic
- max order sizing
- beginner Korean summary

Verified with pytest.

## Ingestion And Local Storage

Added SQLite-based local persistence.

Added database tables:

- `market_snapshots`
- `company_risks`
- `toss_investor_snapshots`
- `news_events`
- `risk_evaluations`

Added repository and ingestion support:

- `database.py`
- `repository.py`
- `ingestion.py`

Added CSV/JSON file adapters:

- `file_market_data.py`
- `file_company_risk.py`
- `file_toss_signal.py`
- `file_news.py`

Added CLI command:

```powershell
python -m stock_risk_mcp.cli evaluate-and-save --ticker SAFE --side BUY --confidence 0.7 --reason "..."
```

The command evaluates a proposal and saves the input snapshots plus result to SQLite.

## Backtesting And Replay

Added a replay layer to compare stored risk evaluations with later price history.

Added files:

- `price_history.py`
- `performance.py`
- `backtest.py`
- `adapters/file_price_history.py`

Added database tables:

- `price_history`
- `backtest_results`

Added model support:

- `PriceBar`
- `BacktestResult`
- `BacktestOutcome`

Implemented:

- CSV/JSON price history ingest
- entry price selection from evaluation date or next available trading day
- exit price selection at the requested horizon or next available trading day
- return percentage
- max drawdown percentage
- max gain percentage
- `WIN`, `LOSS`, `FLAT`, `NO_DATA` classification

Added CLI commands:

```powershell
python -m stock_risk_mcp.cli ingest-prices --file data/prices.csv --db data/stock_risk_mcp.sqlite3
python -m stock_risk_mcp.cli backtest --db data/stock_risk_mcp.sqlite3 --horizon-days 30
python -m stock_risk_mcp.cli backtest-summary --db data/stock_risk_mcp.sqlite3
```

## Policy Reporting And Tuning

Added reporting to analyze whether risk decisions and policy rules appear useful after backtesting.

Added files:

- `reporting.py`
- `policy_analysis.py`

Implemented:

- decision-level performance
- score bucket performance
- hard block reason performance
- policy recommendation generation
- empty-database safe report output

Score buckets:

- `0_39`
- `40_59`
- `60_79`
- `80_100`

Added CLI command:

```powershell
python -m stock_risk_mcp.cli report --db data/stock_risk_mcp.sqlite3
```

The report is for policy tuning reference only. It is not an automatic trading instruction.

## Evidence And Provenance

Added normalized evidence/provenance tracking so risk decisions can be traced beyond free-text JSON fields.

Added files:

- `evidence.py`
- `reason_codes.py`
- `provenance.py`

Added database tables:

- `evaluation_reasons`
- `data_sources`
- `ingestion_runs`

Added model support:

- `Evidence`
- `EvaluationReason`
- `DataSource`
- `IngestionRun`
- `ReasonType`
- `Severity`
- `SourceType`
- `IngestionStatus`

The risk engine now keeps existing `RiskResult.hard_blocks`, `warnings`, `positive_factors`, and `negative_factors` for compatibility, while also adding:

```text
RiskResult.reason_details
```

`evaluate-and-save` now saves normalized reason details to `evaluation_reasons`.

Reporting now prefers normalized `evaluation_reasons` for hard block analysis. If no normalized rows exist, it falls back to parsing legacy `risk_evaluations.result_json`.

Added CLI commands:

```powershell
python -m stock_risk_mcp.cli reasons --db data/stock_risk_mcp.sqlite3 --evaluation-id 1
python -m stock_risk_mcp.cli sources --db data/stock_risk_mcp.sqlite3
python -m stock_risk_mcp.cli ingestion-runs --db data/stock_risk_mcp.sqlite3
```

Registered mock source names:

- `mock_market_data`
- `mock_company_risk`
- `mock_portfolio`
- `mock_toss_signal`

## Nasdaq Noncompliant File Compliance

Extended the project to ingest and use local Nasdaq Noncompliant Companies CSV files. This remains file-based only:

- no external web requests
- no realtime crawling
- no real order execution

Added files:

- `src/stock_risk_mcp/compliance.py`
- `src/stock_risk_mcp/adapters/nasdaq_noncompliant_file.py`
- `tests/test_nasdaq_noncompliant_file.py`
- `tests/test_compliance.py`

Added model support:

- `ComplianceRecord`
- `ComplianceStatus`
- `CompanyRisk.nasdaq_noncompliance_evidence`

Implemented:

- CSV loading for Nasdaq noncompliant records
- required `ticker` column validation
- ticker normalization to uppercase
- duplicate ticker preservation
- invalid or blank `notice_date` handling as `None`
- `Evidence` generation with `source_name="nasdaq_noncompliant_file"` and `source_type=FILE`
- `FileCompanyRiskWithComplianceAdapter` wrapper that overrides `CompanyRisk.nasdaq_noncompliant` when the CSV contains the ticker
- risk engine behavior that uses CSV compliance evidence for the `NASDAQ_NONCOMPLIANT` hard block when available, otherwise falls back to existing mock company risk evidence

Added database table:

- `compliance_records`

Added repository methods:

- `save_compliance_records(records)`
- `get_compliance_records(ticker)`

Added CLI commands:

```powershell
python -m stock_risk_mcp.cli ingest-nasdaq-noncompliant --file data/nasdaq_noncompliant.csv --db data/stock_risk_mcp.sqlite3
python -m stock_risk_mcp.cli check-compliance --ticker BAD --file data/nasdaq_noncompliant.csv
```

Extended `evaluate-and-save` with:

```powershell
--nasdaq-noncompliant-file data/nasdaq_noncompliant.csv
```

When this option is used and the ticker is present in the CSV, the result contains a `NASDAQ_NONCOMPLIANT` hard block whose reason evidence source is `nasdaq_noncompliant_file`.

README was updated with the CSV format and CLI usage.

## Price History Market Data Adapter

Extended local price history support so stored or file-based `price_history` can calculate `MarketSnapshot` values for risk evaluation. This remains local-data only:

- no external API calls
- no realtime web requests
- no real order execution

Added file:

- `src/stock_risk_mcp/adapters/price_history_market_data.py`
- `tests/test_price_history_market_data.py`

Extended `price_history.py` with:

- `normalize_ticker`
- `sort_price_bars`
- `latest_bar`
- `calculate_return_pct_from_bars`
- `calculate_avg_dollar_volume`
- `calculate_daily_return_volatility`

Implemented `PriceHistoryMarketDataAdapter`:

- file mode through `FilePriceHistoryAdapter`
- DB mode through `RiskRepository.get_all_price_history`
- latest close as `MarketSnapshot.price`
- `avg_dollar_volume_20d`
- `return_5d_pct`
- `return_20d_pct`
- `volatility_20d_pct`
- `ValueError` when no price bars exist for the ticker

Added model support:

- `MarketSnapshot.market_data_evidence`

Market hard block reasons now use price history evidence when available:

- `MISSING_MARKET_CAP`
- `MISSING_DOLLAR_VOLUME`
- `MARKET_CAP_TOO_SMALL`
- `DOLLAR_VOLUME_TOO_LOW`
- `RETURN_5D_TOO_HIGH`

Added repository method:

- `get_all_price_history(ticker)`

Extended CLI:

```powershell
python -m stock_risk_mcp.cli evaluate-and-save --ticker SAFE --side BUY --confidence 0.7 --reason "..." --db data/stock_risk_mcp.sqlite3 --price-history-file data/prices.csv
python -m stock_risk_mcp.cli evaluate-and-save --ticker SAFE --side BUY --confidence 0.7 --reason "..." --db data/stock_risk_mcp.sqlite3 --use-db-price-history
```

When file mode is used, market-related reason evidence can use `source_name="price_history_file"` and `source_type=FILE`.

When DB mode is used, market-related reason evidence can use `source_name="price_history_db"` and `source_type=SYSTEM`.

README was updated with price history CSV usage, DB/file evaluation modes, calculated fields, and the note that insufficient data leaves some fields as `None`.

## Indicator Analysis Layer

Added a price-history-based Indicator Analysis Layer. It is an auxiliary analysis layer only and does not replace existing Risk Engine hard blocks.

Added files:

- `src/stock_risk_mcp/indicators.py`
- `src/stock_risk_mcp/indicator_calculators.py`
- `src/stock_risk_mcp/indicator_interpreter.py`
- `src/stock_risk_mcp/indicator_scoring.py`
- `tests/test_indicators.py`
- `tests/test_indicator_calculators.py`
- `tests/test_indicator_interpreter.py`
- `tests/test_indicator_scoring.py`

Added model support:

- `IndicatorSignal`
- `IndicatorValue`
- `IndicatorSet`
- `IndicatorScore`

Supported indicators:

- returns: 1D, 5D, 20D, 60D
- SMA: 20, 60, 120
- distance from SMA: 20, 60
- average dollar volume and volume/dollar-volume spike ratios
- 20D volatility, ATR 14%, maximum drawdown 60D
- RSI 14 and Bollinger position

Implemented:

- insufficient-data handling with `None` and `UNKNOWN`
- beginner-friendly Korean interpretations
- severity-weighted auxiliary indicator scoring
- price-history evidence using `price_history_file` or `price_history_db`
- local file and DB price-history analysis

Added database table:

- `indicator_values`

Added repository methods:

- `save_indicator_values(values)`
- `get_indicator_values(ticker, latest_only=True)`

Added CLI commands:

```powershell
python -m stock_risk_mcp.cli analyze-indicators --ticker SAFE --price-history-file data/prices.csv
python -m stock_risk_mcp.cli analyze-indicators --ticker SAFE --db data/stock_risk_mcp.sqlite3 --use-db-price-history
python -m stock_risk_mcp.cli analyze-indicators-and-save --ticker SAFE --price-history-file data/prices.csv --db data/stock_risk_mcp.sqlite3
```

README was updated with supported indicators, beginner meanings, CLI usage, and the warning that indicators are not buy recommendations.

## ABC Setup And Trade Plan Layer

Added a LONG-focused ABC Setup and paper TradePlan layer on top of Indicator Analysis. This layer does not execute orders and does not replace the existing Risk Engine.

Added files:

- `src/stock_risk_mcp/setup.py`
- `src/stock_risk_mcp/setup_grading.py`
- `src/stock_risk_mcp/trade_plan.py`
- `src/stock_risk_mcp/trade_sizing.py`
- `src/stock_risk_mcp/risk_reward.py`
- `tests/test_setup.py`
- `tests/test_setup_grading.py`
- `tests/test_trade_plan.py`
- `tests/test_trade_sizing.py`
- `tests/test_risk_reward.py`

Added model support:

- `SetupDirection`
- `SetupGrade`
- `TradeDecision`
- `SetupSignal`
- `TradePlan`
- `TradeSizingPolicy`
- `RiskRewardResult`

Implemented:

- IndicatorSet-based LONG setup scoring and A/B/C/NO_TRADE grading
- latest-close entry price
- conservative LONG stop using the lower of 20-bar swing low and `latest close - 1.5 * ATR`
- grade-based target RR: A=4.0, B=3.0
- minimum RR validation: A=3.0, B=2.5
- maximum-loss-based position sizing
- cash and maximum-position notional caps
- C and NO_TRADE default no-trade behavior

Added database table:

- `trade_plans`

Added repository methods:

- `save_trade_plan(plan)`
- `get_trade_plan(plan_id)`
- `list_trade_plans(ticker=None, limit=50)`

Added CLI commands:

```powershell
python -m stock_risk_mcp.cli analyze-setup --ticker SAFE --price-history-file data/prices.csv
python -m stock_risk_mcp.cli create-trade-plan --ticker SAFE --price-history-file data/prices.csv --account-equity 10000 --cash-available 5000
python -m stock_risk_mcp.cli create-trade-plan-and-save --ticker SAFE --price-history-file data/prices.csv --db data/stock_risk_mcp.sqlite3 --account-equity 10000 --cash-available 5000
```

README explicitly states that TradePlan is a paper trade proposal only and must pass the existing Risk Engine before any real-order proposal.

## Basket Engine

Added a Basket Engine that combines saved TradePlans into a paper trading/proposal basket while managing basket-level portfolio risk. It does not execute orders and does not replace individual Risk Engine checks.

Added files:

- `src/stock_risk_mcp/basket.py`
- `src/stock_risk_mcp/basket_scoring.py`
- `src/stock_risk_mcp/basket_allocator.py`
- `src/stock_risk_mcp/basket_risk.py`
- `src/stock_risk_mcp/basket_builder.py`
- `tests/test_basket.py`
- `tests/test_basket_scoring.py`
- `tests/test_basket_allocator.py`
- `tests/test_basket_risk.py`
- `tests/test_basket_builder.py`

Added model support:

- `BasketMode`
- `BasketCandidate`
- `BasketPolicy`
- `BasketAllocation`
- `BasketRiskSummary`
- `BasketPlan`

Implemented:

- candidate scoring from setup grade, RR, setup score, decision, and sizing validity
- invalid, BLOCK, NO_TRADE, and disabled C candidate filtering
- A/B setup risk-unit proportional loss allocation
- single-candidate and basket-wide loss/notional caps
- cash and remaining basket-notional limits
- sector/theme concentration filtering, with missing values treated as `UNKNOWN`
- PROPOSE, REVIEW, BLOCK, and NO_TRADE basket decisions

Added database tables:

- `basket_plans`
- `basket_allocations`
- `basket_blocked_candidates`

Added repository methods:

- `save_basket_plan(plan)`
- `get_basket_plan(basket_id)`
- `list_basket_plans(limit=50)`
- `get_basket_allocations(basket_id)`

Added CLI commands:

```powershell
python -m stock_risk_mcp.cli build-basket-from-trade-plans --db data/stock_risk_mcp.sqlite3 --account-equity 10000 --cash-available 5000 --max-candidates 10
python -m stock_risk_mcp.cli build-basket-and-save --db data/stock_risk_mcp.sqlite3 --account-equity 10000 --cash-available 5000 --max-candidates 10
python -m stock_risk_mcp.cli show-basket --db data/stock_risk_mcp.sqlite3 --basket-id <basket_id>
```

README states that BasketPlan is a paper trading/proposal object and that every candidate still requires individual Risk Engine and user review before any real-order proposal.

## Paper Trading And Basket Backtest

Added a local price-history paper trading layer for saved BasketPlans. It does not call external APIs and never places real orders.

Added files:

- `src/stock_risk_mcp/paper_trading.py`
- `src/stock_risk_mcp/exits.py`
- `src/stock_risk_mcp/basket_backtest.py`
- `src/stock_risk_mcp/basket_performance.py`
- `tests/test_paper_trading.py`
- `tests/test_exits.py`
- `tests/test_basket_backtest.py`
- `tests/test_basket_performance.py`

Implemented LONG stop-loss, take-profit, time-exit, and no-data outcomes. When one bar touches both stop and target, stop-loss takes priority. Basket results aggregate realized PnL, return, outcome counts, and performance summaries.

Added database tables:

- `paper_trades`
- `basket_backtest_results`

Added CLI commands:

```powershell
python -m stock_risk_mcp.cli paper-trade-basket --db data/stock_risk_mcp.sqlite3 --basket-id <basket_id> --horizon-days 10
python -m stock_risk_mcp.cli paper-trade-basket-from-file --db data/stock_risk_mcp.sqlite3 --basket-id <basket_id> --price-history-file data/prices.csv --horizon-days 10
python -m stock_risk_mcp.cli paper-trades --db data/stock_risk_mcp.sqlite3 --basket-id <basket_id>
python -m stock_risk_mcp.cli basket-performance --db data/stock_risk_mcp.sqlite3
```

README documents the simplified assumptions: no fees, slippage, execution delay, partial fills, or real order execution.

## Adaptive Policy Layer

Added an Adaptive Policy Layer skeleton for validating, storing, proposing, and
evaluating soft strategy policies from Basket Paper Trading outcomes.

Added files:

- `src/stock_risk_mcp/strategy_policy.py`
- `src/stock_risk_mcp/strategy_objective.py`
- `src/stock_risk_mcp/strategy_experiments.py`
- `src/stock_risk_mcp/strategy_optimizer.py`
- `src/stock_risk_mcp/strategy_memory.py`
- `src/stock_risk_mcp/strategy_report.py`
- six matching strategy test files

Implemented:

- default active strategy policy and strict validation
- forbidden hard-risk override rejection
- deterministic normalized `DRAFT` candidate generation
- objective scoring with sample-size and drawdown penalties
- `COMMON_OUTCOME_EVALUATION` experiments using all stored basket backtest results
- strategy memory and limitation report helpers
- SQLite persistence for policies, experiments, and memories

Added CLI commands:

```powershell
python -m stock_risk_mcp.cli strategy-init --db data/stock_risk_mcp.sqlite3
python -m stock_risk_mcp.cli strategy-active --db data/stock_risk_mcp.sqlite3
python -m stock_risk_mcp.cli strategy-propose --db data/stock_risk_mcp.sqlite3 --n 5
python -m stock_risk_mcp.cli strategy-evaluate --db data/stock_risk_mcp.sqlite3 --policy-id default --version v1 --horizon-days 10
python -m stock_risk_mcp.cli strategy-experiments --db data/stock_risk_mcp.sqlite3
python -m stock_risk_mcp.cli strategy-policies --db data/stock_risk_mcp.sqlite3
```

The MVP does not reapply candidate policies to historical features and therefore
does not compare actual candidate policy performance. `FEATURE_RESCORING` is not
implemented. This Adaptive Policy Layer evaluation still does not use the
separate `FULL_POLICY_REPLAY` workflow for its StrategyExperiment records.
Policies with fewer than 30 samples must not be promoted.

## Policy-Aware Scoring Integration

Connected optional StrategyPolicy values to the current Setup, TradePlan,
Basket, Paper Trading, and StrategyMemory pipeline.

Implemented:

- existing `FIXED_RULES` behavior when no policy is selected
- policy-weighted normalized setup indicator components and policy thresholds
- optional policy ID/version and scoring mode metadata propagation
- TradePlan, BasketPlan, PaperTrade, and BasketBacktestResult persistence
- safe nullable-column migration for existing SQLite databases
- policy-aware basket candidate scoring with fixed 0.40 decision weight
- setup/RR redistribution across the remaining 0.60 using StrategyPolicy weights
- pre-score BLOCK/NO_TRADE filtering in policy-aware basket construction
- allowed soft BasketPolicy mapping without changing hard-risk safety fields

Added policy selection flags to setup, trade-plan, and basket CLI flows:

```powershell
--use-active-policy
--policy-id <policy_id> --policy-version <version>
```

This applies a policy only to the current pipeline. It is not
`FULL_POLICY_REPLAY` and does not reconstruct historical features or decisions.

## Replay Snapshot Layer

Added replay run, candidate, TradePlan, basket, and outcome snapshot persistence
as the input storage foundation for the Full Policy Replay Engine.

Implemented:

- snapshot creation from an existing official BasketPlan
- snapshot creation from recent saved TradePlans through the current pipeline
- snapshot-only default for recent TradePlans
- optional official basket persistence only with `--save-basket`
- replay-only basket IDs that may not exist in `basket_plans`
- explicit `saved_to_basket_plans: true/false` notes and CLI output
- optional replay outcome snapshot when usable local DB prices are available
- replay run list and complete dataset inspection commands

`as_of_date` is metadata only in this layer. It does not enforce historical
cutoffs or regenerate indicators, TradePlans, or BasketPlans. A future
`FULL_POLICY_REPLAY` must use the same candidate universe and cutoff-restricted
data to regenerate the pipeline separately for each policy.

Added CLI commands:

```powershell
python -m stock_risk_mcp.cli replay-snapshot-from-basket --db data/stock_risk_mcp.sqlite3 --basket-id <basket_id>
python -m stock_risk_mcp.cli replay-snapshot-from-recent-trade-plans --db data/stock_risk_mcp.sqlite3 --account-equity 10000 --cash-available 5000
python -m stock_risk_mcp.cli replay-runs --db data/stock_risk_mcp.sqlite3
python -m stock_risk_mcp.cli replay-show --db data/stock_risk_mcp.sqlite3 --run-id <run_id>
```

## Full Policy Replay

Implemented policy-specific historical replay from saved ReplayRun candidate
snapshots.

Added:

- strict DB/file as-of price history provider
- historical-only indicator, SetupSignal, TradePlan, and BasketPlan regeneration
- forward-only paper outcome calculation
- final PolicyReplayResult and PolicyComparisonResult persistence
- opt-in regenerated TradePlan and official BasketPlan storage
- minimum candidate count of three for policy comparison
- ACCEPT, REJECT, and NEED_MORE_DATA objective-delta recommendations
- explicit, active, result-list, and comparison CLI commands

Replay does not reuse ReplayTradePlanSnapshot as a policy result. Regenerated
TradePlans are saved only with `--save-intermediate` and have no
`policy_replay_id` linkage in this phase.

## Policy Evaluation Suite And Promotion Gate

Added multi-ReplayRun policy evaluation and explicit promotion controls.

Implemented:

- completed baseline/candidate pair-only performance aggregation
- unavailable pair counts and conservative no-data rate
- minimum ReplayRun, completed-pair, no-data-rate, and candidate-count gates
- ACCEPT, REJECT, and NEED_MORE_DATA suite decisions
- persisted evaluation suites and promotion proposals
- promotion proposal creation without policy status mutation
- explicit policy approval
- approved-only activation with prior ACTIVE policy retirement
- six evaluation and promotion CLI commands

Policy activation is never automatic. The suite remains a local paper replay
evaluation and does not guarantee real investment performance.

## Candidate Scanner And Universe Builder

Added a local, strict as-of candidate universe layer that feeds existing
TradePlan, Basket, Replay Snapshot, and future policy replay workflows.

Implemented:

- DB, price-history-file, and manual ticker universe loading
- strict `date <= as_of_date` price-history use
- existing Indicator, policy-aware Setup, and TradePlan pipeline reuse
- deterministic candidate scoring, hard filters, ranking, and max-candidate limit
- local compliance record exclusion and UNKNOWN-data warnings
- `scan_runs` and `candidate_scan_results` persistence with migration-safe columns
- scan-to-basket output-only default and opt-in official basket persistence
- scan-to-replay candidate snapshot conversion preserving scan metadata
- five scanner CLI commands

The scanner does not call external APIs, use realtime data, calculate future
outcomes, recommend purchases, or execute orders. Scan and basket persistence
remain opt-in so research records do not mix with official proposal records.

## Signal Enrichment Layer

Added local signal normalization and conservative Candidate Scanner
enrichment.

Implemented:

- normalized news, dilution, Toss top-investor portfolio, and flow signals
- strict `observed_at <= as_of_date` handling for DB and file signals
- default DB plus file merge with file-precedence dedupe
- optional `--ignore-db-signals`
- repository-level duplicate storage prevention
- signal count and skipped-duplicate reporting
- candidate score adjustment with 0 through 100 clamp
- CRITICAL negative exclusion and HIGH negative INCLUDE-to-WATCH lowering
- protection against positive-signal promotion of existing EXCLUDE candidates
- Toss signal score clamp from -10 through +10
- `ingest-signals`, `signals`, and signal-aware `scan-candidates` CLI flows

Signal Enrichment is an auxiliary research layer. It does not replace Risk
Engine hard blocks, call external APIs, request realtime data, or execute
orders.

## Operational Pipeline And Watch Loop

Added persisted one-shot and explicit repeated paper-operation workflows that
compose the existing scanner, signal, basket, replay, paper, and policy
evaluation layers.

Implemented:

- persisted PipelineRun lifecycle and PipelineAlert records
- deterministic candidate, critical-signal, basket, paper, policy, and error alerts
- scan-only operational pipeline
- paper basket pipeline with scan, basket, replay snapshot, and optional paper outcome
- memory-only paper result when `save_basket=false`
- official basket and paper persistence only when `save_basket=true`
- explicit paper skip option
- policy evaluation pipeline without automatic promotion proposals
- PARTIAL/FAILED error recording that preserves completed stage IDs
- PipelineSummary generation and operational run/alert inspection commands
- explicit bounded watch loop with independent run records per iteration

The default remains one-shot. The watch loop must be explicitly invoked and
never places orders, calls external APIs, or requests realtime data.

## Test Status

The test suite grew over the work:

- initial MVP tests passed
- ingestion tests passed
- backtesting tests passed
- reporting tests passed
- evidence/provenance tests passed
- Nasdaq noncompliant file compliance tests passed
- price history market data adapter tests passed
- indicator analysis layer tests passed
- ABC setup and trade plan layer tests passed
- Basket Engine tests passed
- paper trading and basket backtest tests passed
- Adaptive Policy Layer tests passed
- Policy-Aware Scoring Integration tests passed
- Candidate Scanner and Universe Builder tests passed
- Signal Enrichment Layer tests passed
- Operational Pipeline and Watch Loop tests passed

Latest verified result before the connector layer:

```text
193 passed
```

## Skill Path Issue

The visible Codex skills initially only showed system skills from:

```text
C:\Users\FX707VU-HX107\.codex\skills\.system
```

The user-installed skills were found under:

```text
C:\Users\FX707VU-HX107\.agents\skills
```

They were copied into the Codex skills directory with:

```powershell
Copy-Item "$HOME\.agents\skills\*" "$HOME\.codex\skills\" -Recurse -Force
```

After copying, the following personal skill directories were present under:

```text
C:\Users\FX707VU-HX107\.codex\skills
```

Detected skill directories:

- `brainstorming`
- `dispatching-parallel-agents`
- `executing-plans`
- `finishing-a-development-branch`
- `karpathy-guidelines`
- `receiving-code-review`
- `requesting-code-review`
- `subagent-driven-development`
- `systematic-debugging`
- `test-driven-development`
- `using-git-worktrees`
- `using-superpowers`
- `verification-before-completion`
- `writing-plans`
- `writing-skills`

The contents of those skills are intentionally not included here.

The current session may still show only skills loaded at session start. A new Codex session may be needed for the copied skills to appear in `/skills`.

## Unified Data Import Pipeline

Added a fault-isolated local CSV/JSON import pipeline for price history,
Nasdaq compliance records, and news/dilution/Toss/flow signals.

Implemented:

- persisted `ImportRun` and per-source `ImportSourceResult` reports
- `COMPLETED`, `PARTIAL`, and `FAILED` aggregate status
- append-only price import with DB and same-file `(ticker, date)` duplicate skips
- compliance and normalized signal dedupe
- optional `as_of_date` cutoff for compliance and signals
- row-level validation errors without aborting other valid rows or sources
- local-file-only `import-data`, `import-runs`, and `import-show` commands

`import-data` never updates existing price rows. The existing standalone
`ingest-prices` UPSERT remains available for deliberate manual correction.

## External Data Connector Interface

Added a network-free connector skeleton that prepares normalized local files
for the Unified Data Import Pipeline.

Implemented:

- connector type, mode, status, output, run, and result models
- persisted `connector_runs`
- deterministic mock market/news/dilution/Toss/flow CSV connectors
- local file registration with optional unchanged copy
- explicit connector registry
- sequential fault-isolated connector execution
- connector output mapping into Unified Data Import
- failed ImportRun creation when no connector output is available
- `connectors`, `run-connectors`, `connector-runs`, `connector-show`, and
  `run-connectors-and-import` CLI commands

This layer does not call real external APIs, scrape websites, bypass
authentication, request realtime data, or execute orders.

Latest verified result after the connector layer:

```text
204 passed
```

## Analysis Report Layer

Added deterministic English/Korean JSON and Markdown reporting over stored
pipeline, scan, basket/replay, paper result, policy suite, and alert evidence.

Implemented:

- persisted `AnalysisReport` records and report inspection
- source-run IDs, generated timestamps, key metrics, warnings, disclaimer, and structured context
- severity-sorted pipeline alerts and linked source summaries
- candidate decision counts, top INCLUDE candidates, warnings, and signal enrichment context
- official and replay-only basket summaries with explicit replay warnings
- stored paper-result inclusion without reconstructing memory-only outcomes
- policy deltas, recommendations, notes, and approval/activation warning
- independent output-file warning and optional DB-save behavior
- `report-pipeline`, `report-scan`, `report-basket`, `report-policy-suite`,
  `reports`, and `report-show` CLI commands

The layer makes no LLM or external API calls and does not provide investment
advice or guarantee performance.

Latest verified result after the Analysis Report Layer:

```text
214 passed
```
## Local LLM Agent Bridge Layer

Added a read-only bridge from stored AnalysisReport and PipelineRun evidence to
deterministic agent context, prompts, briefs, and optional local LLM requests.

Implemented:

- read-only AgentContext generation for reports and pipeline runs
- deterministic prompts and briefs without requiring an LLM
- a read-only MCP lookup facade and tool manifest
- default `DRY_RUN`, plus `OLLAMA_LOCAL`, `OPENAI_COMPAT_LOCAL`, and `DISABLED`
- strict localhost-only endpoint validation for both local HTTP backends
- blocked non-local requests before transport with auditable FAILED responses
- explicit-only persistence of contexts, prompts, briefs, requests, and responses
- CLI commands for generation, local execution, inspection, and tool discovery

The bridge cannot execute trades, approve or activate policies, modify broker
settings, or change hard-risk and safety rules. External cloud endpoints are
blocked so investment reports and context remain local.

Latest verified result after the Local LLM Agent Bridge Layer:

```text
229 passed
```
## Alert Delivery / Notification Layer

Added a local-only notification outbox over PipelineAlert, AnalysisReport,
AgentBrief, and LocalLLMResponse records.

Implemented:

- severity filtering and CRITICAL/HIGH-first ordering
- stored dedupe-key suppression and batch duplicate suppression
- console, Markdown/JSONL local-file, mock, and disabled channels
- fault-isolated COMPLETED/PARTIAL/FAILED/DISABLED/NO_ALERTS delivery runs
- notification run and message persistence with inspection CLI commands
- short LocalLLMResponse previews with blocked endpoint failures marked HIGH
- daily research digests with opt-in failed LocalLLMResponse inclusion
- opt-in `run-paper-pipeline` and `watch-loop` delivery that preserves pipeline status

The layer performs no external network delivery, executes no orders, and
produces paper-trading/research alerts rather than investment advice.

Latest verified result after the Alert Delivery / Notification Layer:

```text
243 passed
```
## Local Static Dashboard Layer

Added self-contained static HTML dashboards over stored pipeline, alert,
notification, report, brief, local LLM, import, connector, and policy evidence.

Implemented:

- persisted DashboardBuildResult audit records
- overview, pipeline, daily, and policy dashboard builders
- escaped HTML, inline CSS, severity ordering, tables, and structured details
- no external scripts, stylesheets, images, CDNs, or network requests
- dashboard CLI build and inspection commands
- opt-in pipeline/watch dashboard generation that preserves pipeline status
- dependency-free optional local preview/smoke script

Dashboards are for paper-trading and research monitoring only and cannot
execute orders, activate policies, or guarantee performance.

Latest verified result after the Local Static Dashboard Layer:

```text
251 passed
```
## End-to-End Demo / Release Hardening Layer

Added a deterministic local orchestration layer that validates the existing
mock connector, import, operational pipeline, report, read-only agent, local
LLM dry-run, notification, and dashboard layers together.

Implemented:

- typed demo runs and per-step completed/skipped/failed results
- core-step failure isolation and non-core partial status aggregation
- deterministic mock connector and imported price-history workflow
- local LLM DRY_RUN with explicit no-network metrics
- generated `demo_summary.json`, `notification.md`, `dashboard.html`, and `report.md`
- lightweight system-smoke checks and non-mutating release checklist
- `run-local-demo`, `system-smoke`, and `release-check` CLI commands

The layer performs no external API calls, scraping, web requests, or real order
execution. Its results are release validation evidence, not investment advice.

Latest verified result after the End-to-End Demo / Release Hardening Layer:

```text
258 passed
```

## Public HTTP Data Connector / Network Safety Layer

Added an explicitly enabled, allowlisted public CSV/JSON download adapter that
feeds the existing connector and Unified Import pipeline.

Implemented:

- default-off networking with explicit `--enable-network`
- exact-host allowlists and optional runtime allowlist intersection
- HTTP/HTTPS-only URL validation, redirect revalidation, and credential blocking
- query/fragment-free URL logging and bounded downloads
- transport-injected stdlib downloader with fake-client tests only
- JSON/YAML provider config loading and provider-level validation CLI
- dynamically registered Public HTTP connectors that never join the default registry
- `run-http-connector` and provider-aware `run-connectors-and-import`
- isolated ConnectorRun failure/disabled records and successful import handoff

This layer does not implement authentication, cookie/session use, private API
keys, login-based Toss or brokerage scraping, external orders, or investment
advice. Network access remains opt-in.

Latest verified result after the Public HTTP Data Connector / Network Safety Layer:

```text
268 passed
```

## Provider Normalization Layer

Added a file-only normalization layer between raw provider outputs and Unified
Import.

Implemented:

- typed NormalizeRun and per-source results with SQLite persistence
- generic price, news, dilution, flow, and FX normalizers
- provider column mapping, as-of filtering, row-level warnings/errors, and safe output paths
- source failure isolation with COMPLETED/PARTIAL/FAILED/NO_INPUT statuses
- normalizer registry and JSON/YAML multi-source config loading
- `normalize-file`, `normalize-run`, `normalize-and-import`, `normalize-runs`, and `normalize-show`
- normalized FX import plus `fx_rates` save/list/latest repository helpers

Normalizers create reproducible local files and never write business data
directly or make network requests. FX data is stored for future use and is not
connected to current sizing or pipeline decisions.

Latest verified result after the Provider Normalization Layer:

```text
280 passed
```

## FX-aware Portfolio / Risk Layer

Added a context/wrapper layer that interprets account-currency inputs while
preserving the existing trading-currency sizing and hard-risk engines.

Implemented:

- same-currency, direct, inverse, manual, latest-as-of, stale, and missing FX handling
- KRW account equity/cash conversion into USD trading values before paper pipeline execution
- nullable FX metadata across TradePlan, basket, paper, PipelineRun, and PipelineSummary records
- safe SQLite `fx_json` migrations for stored trade, allocation, and paper artifacts
- FX summary in pipeline reports, notifications, and static dashboards
- stale FX WARNING alerts without hard block or CRITICAL escalation
- `fx-rates`, `fx-latest`, and `fx-convert` CLI commands
- FX options on `run-paper-pipeline` and `watch-loop`

No external FX API, web request, order execution, sizing-engine rewrite, or
hard-risk rule change was introduced. Missing FX preserves legacy
trading-currency behavior with warnings.

Latest verified result after the FX-aware Portfolio / Risk Layer:

```text
292 passed
```

## Provider Pack #1: Price And FX Public Data Adapter

Added a config-driven orchestration layer that reuses the Safe HTTP Connector,
Provider Normalization, Unified Import, and FX-aware pipeline inputs.

Implemented:

- one provider-pack config as the source for connector, normalizer, and column mappings
- public HTTP and local-file raw acquisition with existing network safety
- price and FX raw-to-normalized-to-import execution
- persisted ProviderPackRun audit records with connector/normalize/import IDs
- price-core combined status rules and isolated FX partial failures
- price, FX, combined, list, and show CLI commands

Networking remains default-off and allowlisted. No authentication, scraping,
broker API, external order execution, or new downloader was introduced.

Latest verified result after Provider Pack #1:

```text
303 passed
```

## Provider Pack #2: News Public Data Adapter

Added a news-only extension to the existing Provider Pack orchestration.

Implemented:

- `news.providers` in the shared provider-pack config
- external `headline` to internal signal `title` mapping
- INFO-to-LOW normalization with original provider payload preservation
- conservative News Provider Pack-only score deltas
- rich news metadata import while preserving legacy news import behavior
- safe public HTTP and network-free local-file news providers
- `run-news-provider-pack` CLI and stored NEWS ProviderPackRun records
- unchanged common signal scoring and existing critical/high enrichment rules

The adapter adds no credentials, login, cookies, sessions, private scraping,
Toss scraping, order execution, or default-on networking.

Latest verified result after Provider Pack #2:

```text
314 passed
```

## Provider Pack #3: Dilution / Filings Public Data Adapter

Added a dilution-only extension to the shared Provider Pack orchestration.

Implemented:

- `dilution.providers` in the single provider-pack config
- required provider mappings for ticker, observation time, event, dilution risk, and source
- safe HTTP and network-free local-file acquisition
- raw provider payload preservation and conservative UNKNOWN handling
- Dilution Provider Pack-only non-positive score mapping
- existing HIGH-to-WATCH and CRITICAL-to-EXCLUDE signal enrichment behavior
- `run-dilution-provider-pack` CLI and stored DILUTION ProviderPackRun records
- unchanged common signal scoring and Risk Engine hard-risk rules

Dilution Provider Pack signals currently feed Signal Enrichment only. They do
not automatically populate `CompanyRisk.dilution_risk`. The existing
`block_dilution_high` and `block_unknown_dilution` rules remain intact, while
the direct Provider Pack signal-to-CompanyRisk hard-risk bridge is future
work.

Latest verified result after Provider Pack #3:

```text
324 passed
```

## Provider Pack #4: Flow Public Data Adapter

Added a Flow-only extension to the shared Provider Pack orchestration.

Implemented:

- `flow.providers` in the single provider-pack config
- safe HTTP and network-free local-file acquisition
- provider-config-scope amount precedence with shares-only fallback
- deterministic sign-based LOW/MEDIUM Flow Provider Pack scores
- explicit `RICH_FLOW_PROVIDER` metadata rather than score-based record identification
- raw provider payload preservation
- `run-flow-provider-pack` CLI and stored FLOW ProviderPackRun records
- unchanged legacy/common signal scoring and Risk Engine hard-risk rules

Flow is a ranking and watching aid, not hard-risk or a buy instruction. It
does not create HIGH/CRITICAL signals by default, and positive Flow alone
cannot promote EXCLUDE or blocked candidates.

Latest verified result after Provider Pack #4:

```text
336 passed
```

## v2.8 Real-Time Market Data Foundation + Dynamic Watchlist

Added the first read-only realtime monitoring layer:

- typed market events and rolling intraday metrics
- deterministic mock and network-free local replay providers
- bounded symbol/event/HOT-watchlist limits
- automatic CANDIDATE/HOT/COOLING/BLOCKED watchlist transitions
- persisted realtime monitor runs and latest watchlist entries
- `run-realtime-monitor`, `watchlist-list`, `realtime-runs`, and
  `realtime-show` CLI commands
- memory-only raw events and rolling history

Relative volume uses the current 1-minute bucket divided by the average of up
to 15 preceding positive-volume 1-minute buckets for the same symbol and
region. The current bucket and future data are excluded. No valid history or
non-positive current volume produces `None`.

This stage is realtime monitoring only. It adds no OrderIntent, broker
integration, or live order path. The long-term automatic buy/sell goal remains
scheduled for the execution-gated roadmap after v2.8.

## v2.9 Order Intent / Execution Gate Foundation

Added the broker-neutral, paper-only execution boundary:

- typed OrderIntent, RiskGateDecision, ExecutionGateDecision, and
  PaperExecution models
- deterministic RiskGate with immutable safety blocks
- PAPER-only ExecutionGate with expiry and duplicate checks
- deterministic paper fills without slippage, network, or broker integration
- SQLite audit tables and repository lifecycle helpers
- five JSON CLI commands for intent creation, evaluation, execution, and lists

Strategies and signals still cannot execute directly. HOT watchlist status
does not approve a BUY, while BLOCKED watchlist status prevents approval.
MARKET, margin, short selling, options, futures, and leverage remain blocked
by default. BUY intents require calculable stop-loss risk.

No Kiwoom or other broker API, account/balance/position API, network call, or
secret-reading path was added. Future work proceeds through v2.10 Broker
Adapter Interface, v2.11 Kiwoom REST Read-only Adapter, v2.12 Kiwoom
Sandbox/Mock Execution Adapter, and v2.13 Kiwoom Live Execution Adapter with
an explicit kill switch.

## v2.10 Broker Adapter Interface

Added a broker-neutral interface boundary after the v2.9 execution gate:

- broker request, receipt, health, capability, environment, and status models
- broker-neutral `BrokerAdapter` protocol
- deterministic local-only `MockBrokerAdapter`
- `BrokerAdapterService` requiring matching approved PAPER gate decisions
- append-only broker request, receipt, and health SQLite audit tables
- four JSON CLI commands for health, mock submit, request list, and receipt list

Every submission attempt is saved. Duplicate submissions save a new request
and a new REJECTED receipt with `duplicate broker submission`; the mock
adapter is not called again and no second fill is created.

v2.9 PaperExecutor remains unchanged and independent. v2.10 MockBrokerAdapter
proves the interface boundary for future broker integrations but adds no
Kiwoom connection, broker SDK, account/balance/position read, external network
call, secret access, or live order path.

Future work remains v2.11 Kiwoom REST Read-only Adapter, v2.12 Kiwoom
Sandbox/Mock Execution Adapter, and v2.13 Kiwoom Live Execution Adapter with
an explicit kill switch.

## v2.11 Kiwoom REST Read-only Adapter

Added a fake-transport-only read-only contract for future Kiwoom REST
integration:

- seven exact internal `/readonly/*` endpoint pairs
- deterministic fake fixtures and bounded continuation handling
- normalized stock info, quote, ranking, flow, chart, and condition results
- sanitized append-only SQLite request/response audits
- nine JSON CLI commands with `MOCK` default and `PROD_DISABLED` behavior
- safety checks excluding HTTP/Kiwoom SDK imports, credentials, environment
  access, account reads, orders, and strategy/execution integration

This stage is **internal deterministic endpoint only; official Kiwoom endpoint
mapping deferred**. It does not implement official `api_id` or path mappings,
OAuth, real network calls, account/balance/position reads, or orders. Official
Kiwoom REST verification remains future work. OpenAPI+/OCX/pykiwoom are not
imported.

The next execution stages remain v2.12 Kiwoom Sandbox/Mock Execution Adapter
and v2.13 Kiwoom Live Execution Adapter with an explicit kill switch and
default-off live trading.

## v2.12 Kiwoom Sandbox/Mock Execution Adapter

Added a Kiwoom-shaped deterministic local execution boundary:

- dedicated `KiwoomMockExecutionService` requiring approved RiskGate and
  ExecutionGate decisions
- `KiwoomMockExecutionAdapter` with ORDER_SUBMIT and ORDER_CANCEL only
- local-only `FakeKiwoomExecutionTransport` using three exact internal fixture
  endpoints
- KR-only deterministic LIMIT/STOP_LIMIT fills and explicit-price MARKET fills
- generic broker plus Kiwoom mock-specific append-only SQLite audits
- duplicate submission rejection without a second adapter fill
- audited deterministic cancel and status operations
- six JSON CLI commands

This stage does not use official Kiwoom API IDs or paths. It performs no OAuth,
real network call, credential access, account/balance/position/holdings/cash
read, live order, OpenAPI+/OCX/pykiwoom import, or Windows-only integration.

Future work proceeds through v2.13 official endpoint verification, v2.14
explicitly opt-in real-network sandbox integration, and v2.15 default-off live
execution with an explicit kill switch.

## v2.13 Kiwoom Official Endpoint Verification

Added a curated official endpoint manifest and deterministic safety validator:

- representative official AUTH, READ_ONLY, ORDER, and ACCOUNT_READ entries
- strict schema with official source and verification date
- duplicate, class, dangerous-path, source-host, and runtime-overlap checks
- three JSON-only list/validate/show CLI commands
- complete separation from v2.11 `/readonly/*` and v2.12 `/kiwoom-mock/*`

v2.13 uses a curated official endpoint manifest. It is not a complete Kiwoom
API catalog. It verifies endpoint classification and runtime safety policy.
Full official endpoint coverage is intentionally deferred.

All official manifest entries are runtime-disabled, including READ_ONLY
entries. The manifest is file-based verification data only; it is not wired
to any transport, adapter, OAuth flow, account runtime, or order execution
path.

Future work is v2.14 opt-in real-network read-only integration, v2.15 opt-in
sandbox order integration, and v2.16 default-off live execution with an
explicit kill switch.

## v2.14 Kiwoom Real-Network Read-only Opt-in Adapter

Added a separate, default-disabled real-network read-only boundary without
changing the v2.11 fake read-only service:

- exact `https://mockapi.kiwoom.com` base URL and MOCK-only environment
- six curated v2.13 manifest REST READ_ONLY API IDs
- WebSocket/ORDER/ACCOUNT_READ/UNKNOWN blocking
- AUTH restricted to the explicitly enabled token provider
- explicit ENV or exact credential-file loading with no auto-discovery
- per-run request limits, bounded timeout, and redacted SQLite audits
- separate `kiwoom-real-readonly-*` CLI commands

Tests and system smoke remain fake/local-only. Audit rows exclude credentials,
tokens, authorization headers, request bodies, and response bodies. This stage
does not add order, account, balance, position, holdings, or live execution.

## v2.15 Kiwoom Real-Network Read-only Manual Smoke

Added a separate manual-only harness around the v2.14 MOCK read-only adapter:

- offline smoke plan with no credential read or network
- validation-only dry-run with no credential read, token request, or HTTP call
- six-ID REST READ_ONLY allowlist, `minimal=ka10001`, deduplication, and a
  three-endpoint hard maximum
- sequential fake-testable execution with completed/partial/failed aggregation
- append-only redacted smoke run and step SQLite audits
- plan/run/reports/show JSON CLI commands

The harness blocks PROD, WebSocket, ORDER, ACCOUNT_READ, AUTH outside the
controlled token provider, and unknown endpoints. Reports exclude credentials,
credential paths, tokens, authorization headers, account numbers, and raw
request/response bodies. Pytest and system-smoke never execute a real manual
smoke call. This release adds no live trading or account runtime.

## v2.16 Kiwoom Sandbox Order Adapter

Added a separate MOCK-only sandbox order boundary behind OrderIntent,
RiskGateDecision, and the new explicitly enabled `ExecutionMode.SANDBOX`.
PAPER behavior is unchanged and LIVE remains blocked.

- official manifest ORDER endpoints only: `kt10000` submit and `kt10003` cancel
- BUY KR equity LIMIT submission only; SELL blocked because no verified
  SELL-submit endpoint exists in the curated manifest
- offline health/plan and credential/network-free dry-run
- stable client order IDs and duplicate rejection before transport
- bounded known-order cancel and local-audit-only status
- append-only redacted run/request/receipt/status audit tables
- separate sandbox order CLI commands

PROD, account reads, MARKET, margin, short, options, futures, leverage,
fractional quantities, and direct strategy broker access remain blocked.
Pytest and system-smoke use no real network. v2.17 remains a future
live-execution design checkpoint with an explicit kill switch.
## v2.17 Live Execution Safety Checkpoint

- Added a documentation-only safety checkpoint; no live runtime path, PROD
  transport, live CLI, credential loader, OAuth, or account-read service was
  added.
- Kept `ExecutionMode.LIVE` unconditionally blocked and added a regression
  test that proves approved risk input and sandbox opt-in cannot enable it.
- Defined future explicit live gates: verified exact PROD URL, explicit
  credential source, account confirmation, acknowledgement phrase, approved
  RiskGate/ExecutionGate decisions, notional caps, ticker/side/type allowlists,
  and default-blocking kill switches.
- Defined fail-closed global, session, broker, and account kill-switch checks
  before credential, token, network, planning, submit, cancel, or retry work.
- Deferred account-read to a separate future v2.18 opt-in boundary. Future live
  SELL remains blocked unless a local live ledger proves holdings.
- Required append-only live audits and strict secret/account/body redaction.
- Kept fake-only tests and system smoke with `external_network_calls=false`.

## v2.20 Account-Read Manual MOCK Smoke And Reconciliation Hardening

- Added offline smoke plan plus gated manual MOCK smoke run, reports, and show
  commands around the v2.19 account-read service.
- Fixed the `minimal` endpoint set to `kt00001` and enforced a hard maximum of
  two curated `ACCOUNT_READ` endpoints before credentials/token/network.
- Added redacted smoke run and step SQLite audits containing only safe status
  counts, classifications, status codes, sanitized errors, and timestamps.
- Hardened reconciliation to require an inactive kill switch before reading
  an explicitly selected local ledger or persisting results.
- Added honest aggregate-only symbol-count comparison. Missing ledger returns
  `LOCAL_LEDGER_UNAVAILABLE`; missing account summary returns
  `ACCOUNT_DATA_UNAVAILABLE`; symbol-detail requests return
  `ACCOUNT_DETAILS_UNAVAILABLE` because account details are not persisted.
- Reconciliation remains count-only, order-free, LIVE-disabled, strategy-free,
  sizing-free, credential-free, token-free, and network-free.
- Kept PROD, LIVE, ORDER, market-data READ_ONLY, unknown, and WebSocket
  account-read paths blocked.
- Tests use fake dependencies only; system smoke remains local-only with
  `external_network_calls=false`.

## v2.19 Kiwoom Account-Read MOCK Opt-in Adapter

- Added a separate, default-disabled MOCK-only account-read gate, transport,
  service, redacted models, SQLite audits, and six JSON CLI commands.
- Restricted account-read to the curated manifest IDs `kt00001`, `kt00018`,
  and `kt00007`, exact `https://mockapi.kiwoom.com`, and at most two endpoints
  per run.
- Required explicit real-network/account-read enablement, credentials, auth
  opt-in, account confirmation, account fingerprint confirmation,
  acknowledgement, and inactive kill switch.
- Kept health, plan, and dry-run credential/token/network free.
- Stored only irreversible short account fingerprints, normalized counts,
  sanitized errors, and redacted metadata. Raw account and broker payload data
  is discarded rather than persisted or printed.
- Added count-only kill-switch-gated reconciliation preview with no order,
  LIVE, strategy, or automatic sizing integration.
- Kept PROD, LIVE, ORDER, READ_ONLY market data, WebSocket, unknown endpoints,
  and direct strategy account-read blocked.
- Tests use fake credentials/token/HTTP dependencies only; system smoke
  remains local-only with `external_network_calls=false`.

## v2.18 Account-Read Opt-in Safety Checkpoint

- Added a documentation-only account-read safety checkpoint; no account
  transport, account/balance/holding/fill/order-history call, PROD access,
  credential loading, or live execution was added.
- Kept the curated manifest account candidates `kt00001`, `kt00018`, and
  `kt00007` classified `ACCOUNT_READ` and runtime-disabled.
- Added fake-only regression guards proving account candidates are rejected
  before HTTP and `ExecutionMode.LIVE` remains blocked.
- Defined future explicit enablement, MOCK-first environment policy, exact
  base URL, credential source, account/fingerprint confirmation,
  acknowledgement, strict allowlist, and redaction gates.
- Defined fail-closed global/session/broker/account kill switches before any
  credential, token, network, or account endpoint work.
- Separated future account-read from strategy, risk scoring, automatic sizing,
  market-data READ_ONLY, sandbox orders, and live orders.
- Limited future normalized storage to privacy-safe ledger and audit fields;
  raw account identifiers and raw broker response bodies remain forbidden.
- Kept fake-only tests and system smoke with `external_network_calls=false`.

## v2.21 Local Ledger Sell-Safety Integration

- Added offline local ledger positions, transactions, snapshots, repository
  helpers, SQLite audit tables, and JSON CLI commands.
- Defined available SELL quantity as local `quantity - reserved_quantity`,
  floored at zero. Broker account-read data is not automatically promoted into
  the local ledger.
- Added append-only `SellSafetyDecision` audits for approved, blocked, and
  reconciliation-required outcomes.
- Required an approved matching SellSafetyDecision for SELL RiskGate and
  SANDBOX ExecutionGate approval. BUY and existing PAPER behavior remain
  unchanged.
- Kept actual Kiwoom sandbox SELL submission blocked with
  `SELL_SANDBOX_ORDER_SCHEMA_NOT_VERIFIED` because the curated manifest has no
  verified SELL submit schema.
- Kept PROD, LIVE, account-read-driven automatic orders, direct strategy
  access, credentials, tokens, and network calls outside the layer.
- Reconciliation may conservatively block SELL eligibility but never creates
  or submits an order. Verified-schema ledger-backed sandbox SELL reservation
  or a separate live execution dry-run gate remains v2.22 future work.

## v2.22 Kiwoom Sandbox SELL Schema Verification And Dry-Run Gate

- Added offline SELL schema verification models, field evidence, reports, and
  append-only SQLite audits.
- Verified only project-local official manifest evidence. Internal request
  models and test fixtures are not treated as official schema proof.
- Current result is `UNVERIFIED`: the repository lacks an explicit official
  SELL value and official side, LIMIT-type, symbol, quantity, limit-price, and
  account-field mapping.
- Added a fail-closed SELL dry-run service and four JSON CLI commands.
- Required a `VERIFIED` report, approved SellSafety/RiskGate/SANDBOX
  ExecutionGate decisions, sufficient current local ledger, LIMIT order, and
  MOCK environment for dry-run approval.
- Kept current dry-run blocked with
  `SELL_SANDBOX_ORDER_SCHEMA_NOT_VERIFIED`.
- Kept actual sandbox SELL submission blocked in v2.22 regardless of a stored
  test-fixture report. Existing BUY sandbox behavior is unchanged.
- Kept credentials, tokens, transports, network, raw account data,
  account-read-driven orders, strategy broker access, PROD, and LIVE outside
  this layer.
- Future v2.23 work may import/review official SELL schema evidence and then
  consider MOCK sandbox SELL submission in a separate release.
