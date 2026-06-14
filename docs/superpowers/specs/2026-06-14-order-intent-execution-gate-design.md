   # v2.9 Order Intent / Execution Gate Foundation Design

   ## Goal

   Add a broker-neutral, fully auditable order-intent and execution-gate
   foundation. Strategies and signals may create `OrderIntent` records, but they
   cannot execute orders directly. v2.9 supports deterministic paper execution
   only and adds no broker, account, position, balance, credential, or network
   integration.

   ## Architecture

   ```text
   Strategy / Signal / Manual Input
   -> OrderIntent
   -> RiskGate
   -> ExecutionGate
   -> PaperExecutor
   -> SQLite audit records
   ```

   Responsibilities remain separate:

   - `order_intent.py` defines broker-neutral models and lifecycle states.
   - `order_risk_gate.py` evaluates immutable safety rules without executing.
   - `execution_gate.py` verifies prior risk approval and PAPER-only eligibility.
   - `paper_execution.py` performs deterministic local fills.
   - `order_intent_service.py` orchestrates persistence and status transitions.
   - `repository.py` stores every intent, decision, and paper execution.

   No strategy, signal, optimizer, or agent receives a broker execution
   interface.

   ## Core Models

   ### Enums

   - `OrderSide`: `BUY`, `SELL`
   - `OrderType`: `LIMIT`, `STOP_LIMIT`, `MARKET`
   - `ExecutionMode`: `PAPER`, `SANDBOX_DISABLED`, `LIVE_DISABLED`
   - `OrderIntentStatus`: `CREATED`, `RISK_BLOCKED`, `RISK_APPROVED`,
   `EXECUTION_BLOCKED`, `EXECUTION_APPROVED`, `PAPER_EXECUTED`, `CANCELLED`,
   `EXPIRED`

   ### OrderIntent

   `OrderIntent` stores the requested ticker, market region, side, order type,
   quantity/notional, prices, source audit fields, reason, confidence, lifecycle
   timestamps, status, and metadata.

   Ticker is normalized to uppercase. Model validation keeps request values
   structurally typed, while safety validity is decided by RiskGate so blocked
   requests remain auditable.

   `metadata_json` is a dictionary. v2.9 recognizes these safety fields:

   - `margin: bool`
   - `short: bool`
   - `instrument_type: str`
   - `leverage: number`
   - `reference_price: number`, used only when an explicitly allowed MARKET order
   needs risk estimation

   Ordinary `SELL` does not imply short selling because it may represent a
   position exit. Short selling is blocked when `metadata_json.short=true`.

   ### Decisions And Execution

   `RiskGateDecision` and `ExecutionGateDecision` each receive their own unique
   ID and store approval, decision text, reasons, rule hits or execution mode,
   and creation time.

   `PaperExecution` stores the intent, ticker, side, requested and filled values,
   execution time, status, and metadata. There is at most one paper execution per
   intent.

   ## RiskGate

   RiskGate uses a `RiskGateConfig` containing:

   - `allow_market_orders`, default `False`
   - `max_risk_per_trade`
   - `max_position_notional`
   - `max_daily_loss`
   - `current_daily_loss`, default `0`
   - `blocked_tickers`

   It accumulates every applicable rule hit and approves only when none are hit.
   It does not mutate hard-risk rules and does not execute.

   RiskGate blocks:

   - missing ticker
   - missing or `UNKNOWN` region
   - invalid side
   - MARKET unless explicitly allowed
   - missing both quantity and notional
   - non-positive supplied quantity or notional
   - non-positive LIMIT or STOP_LIMIT limit price
   - BUY without stop loss
   - BUY stop loss at or above entry price
   - BUY risk that cannot be calculated
   - estimated loss above `max_risk_per_trade`
   - estimated position notional above `max_position_notional`
   - `current_daily_loss + estimated_loss > max_daily_loss`
   - margin, short, option, future, or leverage above 1
   - configured blocked ticker
   - linked `WatchlistEntry` with status `BLOCKED`

   HOT watchlist status adds no approval and bypasses no rule.

   ### Derived Values

   For LIMIT and STOP_LIMIT orders, entry price is `limit_price`.

   For an explicitly allowed MARKET order, entry price is
   `metadata_json.reference_price`. If it is missing or non-positive, BUY risk
   cannot be calculated and the intent is blocked.

   Derived quantity:

   ```text
   quantity, when supplied
   otherwise notional / entry_price
   ```

   Estimated position notional:

   ```text
   notional, when supplied
   otherwise derived_quantity * entry_price
   ```

   BUY estimated loss:

   ```text
   (entry_price - stop_loss_price) * derived_quantity
   ```

   `max_risk_per_trade`, `max_position_notional`, and `max_daily_loss` are
   absolute trading-currency amounts. A missing limit means that specific
   configurable amount check is not applied. The default hard blocks remain
   active regardless of optional limits.

   ## ExecutionGate

   ExecutionGate:

   - requires the latest RiskGateDecision to be approved
   - blocks expired intents
   - blocks intents that already have a paper execution
   - approves only `ExecutionMode.PAPER`
   - always blocks `SANDBOX_DISABLED` and `LIVE_DISABLED`
   - stores an audit decision for every evaluation

   There is no `--enable-live-trading` flag and no broker adapter in v2.9.

   ## Paper Execution

   PaperExecutor accepts only an `EXECUTION_APPROVED` intent with an approved
   PAPER ExecutionGateDecision and no existing paper execution.

   Fill price is deterministic:

   1. explicit CLI/test `fill_price`, when positive
   2. intent `limit_price`

   MARKET intents without an explicit deterministic fill price are not paper
   executed. v2.9 adds no slippage simulation.

   After saving `PaperExecution`, the intent status becomes `PAPER_EXECUTED`.
   Duplicate execution is blocked and recorded through the execution gate.

   ## Persistence

   Add four append-oriented audit tables:

   - `order_intents`
   - `risk_gate_decisions`
   - `execution_gate_decisions`
   - `paper_executions`

   `order_intents` status is updated as the lifecycle advances. Decision and
   execution rows are never overwritten. `paper_executions.order_intent_id` is
   unique.

   Repository APIs provide save/get/list operations, intent status updates,
   latest decision lookup, and duplicate paper-execution detection.

   Existing databases receive the tables through the current idempotent schema
   creation path.

   ## Service Flow

   `OrderIntentService` exposes three workflows:

   1. Create and persist an intent in `CREATED`.
   2. Evaluate selected or eligible intents:
      - run and save RiskGateDecision
      - update to `RISK_BLOCKED` or `RISK_APPROVED`
      - when risk-approved, run and save ExecutionGateDecision
      - update to `EXECUTION_BLOCKED` or `EXECUTION_APPROVED`
   3. Paper execute selected or eligible execution-approved intents:
      - re-check PAPER decision and duplicate state
      - save deterministic PaperExecution
      - update to `PAPER_EXECUTED`

   Normal blocked outcomes are returned as JSON results, not raised as CLI
   tracebacks.

   ## CLI

   Add:

   - `create-order-intent`
   - `order-intents-list`
   - `evaluate-order-intents`
   - `paper-execute-approved-intents`
   - `paper-executions-list`

   `evaluate-order-intents` supports:

   - `--order-intent-id`
   - `--execution-mode PAPER|SANDBOX_DISABLED|LIVE_DISABLED`
   - `--allow-market-orders`, opt-in boolean flag, default false
   - `--max-risk-per-trade`
   - `--max-position-notional`
   - `--max-daily-loss`
   - `--current-daily-loss`, default `0`
   - repeatable `--blocked-ticker`

   CLI output includes intents, gate decisions, paper executions, explicit
   statuses, and blocking reasons.

   ## Safety Boundaries

   - no live execution
   - no sandbox broker execution
   - no broker SDK or API module
   - no account, balance, or position API
   - no network calls
   - no secret or credential reads
   - MARKET default blocked
   - margin, short, options, futures, and leverage default blocked
   - BUY requires calculable stop-loss risk
   - HOT never implies approval
   - BLOCKED watchlist prevents approval
   - all decisions and executions are auditable in SQLite

   System smoke must remain `COMPLETED` with `external_network_calls=false`.

   ## Documentation And Future Path

   README and WORK_SUMMARY will explain why strategy code creates intents instead
   of calling brokers and why v2.9 remains paper-only.

   Future path:

   - v2.10 Broker Adapter Interface
   - v2.11 Kiwoom REST Read-only Adapter
   - v2.12 Kiwoom Sandbox/Mock Execution Adapter
   - v2.13 Kiwoom Live Execution Adapter with explicit kill switch

   ## Verification

   Tests cover models, every requested RiskGate and ExecutionGate block,
   watchlist interaction, audit persistence, deterministic paper fills,
   duplicates, all five CLI commands, existing provider packs, existing realtime
   monitoring, and absence of broker/network functionality.

   Final verification:

   ```powershell
   pytest -q
   python -m compileall -q src
   git diff --check
   python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs
   git status --short
   ```
