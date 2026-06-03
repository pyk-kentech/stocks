# Work Summary

This document summarizes the work completed so far, excluding the contents of any installed skills.

## Project

Project path:

```text
D:\KENTECH\stock\stock-risk-mcp
```

The project started as a local MVP for evaluating stock trade proposals. It does not execute real orders and does not call external APIs. The core idea is that an LLM or external client may propose a trade, but a deterministic risk engine acts as the final gate.

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

## Test Status

The test suite grew over the work:

- initial MVP tests passed
- ingestion tests passed
- backtesting tests passed
- reporting tests passed
- evidence/provenance tests passed
- Nasdaq noncompliant file compliance tests passed
- price history market data adapter tests passed

Latest verified result:

```text
54 passed
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
