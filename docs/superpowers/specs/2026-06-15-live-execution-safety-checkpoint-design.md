# v2.17 Live Execution Safety Checkpoint Design

## Purpose And Scope

v2.17 is an approval and safety-design checkpoint. It does not implement live
trading, a PROD transport, a live-order CLI, credential loading, OAuth, account
reads, or automatic real-network tests. `ExecutionMode.LIVE` remains blocked
for every current configuration.

The exact official Kiwoom PROD base URL is not verified by this project.
Future live work must remain blocked until an exact official URL is verified
from official documentation and committed to the curated manifest. The URL
must never be guessed.

## Future Live Activation Model

A future live execution request must fail closed unless every gate below is
satisfied:

- persisted configuration has `live_enabled=true`; default is `false`
- CLI includes `--enable-live-execution`
- environment is explicitly `PROD`
- base URL exactly matches a verified official PROD URL
- credentials come only from explicit ENV names or one explicit credential file
- the user explicitly confirms the target account by a redacted fingerprint
- global, session, broker, and account kill switches are all unlocked
- explicit maximum order notional and maximum daily notional are configured
- ticker is in an explicit allowlist
- side and order type are explicitly allowed
- the exact acknowledgement phrase is supplied:
  `I_UNDERSTAND_THIS_CAN_PLACE_REAL_ORDERS`
- the source OrderIntent has approved matching RiskGate and ExecutionGate
  decisions

The acknowledgement phrase is documented only. v2.17 does not add a CLI flag
or runtime implementation for it.

## Kill-Switch Model

The future global kill switch defaults to active and blocking. Additional
switches apply per session, broker, and account. A future implementation must
check all switches before credential loading, token requests, planning,
submission, cancellation, and retry handling.

Kill-switch sources are:

- an explicitly configured emergency local file
- an environment variable, proposed as `STOCK_RISK_MCP_LIVE_KILL_SWITCH`
- SQLite persisted state and audit events

No kill-switch file is auto-discovered and no filesystem scanning is allowed.
If any switch is active, unknown, unreadable, inconsistent, or unavailable,
live execution is blocked before credential, token, network, or order work.
Every check and state change must be auditable.

## First Live Version Constraints

The first future live version is limited to KR cash equity LIMIT orders:

- no MARKET, margin, short, credit, leverage, options, futures, or fractional
  orders
- maximum one submission per run
- a deliberately small maximum order notional and daily notional
- BUY requires a stop-loss
- no automated averaging down
- no bracket simulation unless the broker officially and clearly supports it
- no submission retry
- SELL remains blocked unless a local live ledger proves sufficient holdings

Strategy, agent, and optimizer code may create OrderIntent records only. They
must never call a broker or transport directly or modify hard-risk rules.

## Account-Read Separation

v2.17 does not add account, balance, position, holding, cash, or fill reads.
Account-read is a separate future v2.18 opt-in boundary. Until a trustworthy
local live ledger exists, SELL live execution remains blocked. This avoids
silently widening live-order permissions merely to support SELL validation.

## Audit And Redaction

Future live execution must use append-only audit records for live runs, order
requests, receipts, kill-switch events, and gate decisions. Audit records may
store a redacted account fingerprint, endpoint identifier, decision reasons,
bounded response metadata, and timestamps.

Audit, logs, CLI output, tests, and documentation must never store or print:

- app keys, secret keys, access or refresh tokens, or authorization headers
- raw account numbers or raw credential file contents
- sensitive raw request or response bodies

## Fake-Only Test Plan

Future live implementation work must first prove, with fake transports only:

- LIVE is blocked by default and when any required flag or acknowledgement is
  missing
- each active or unreadable file, ENV, or SQLite kill switch blocks before
  credential, token, network, or order work
- missing RiskGate or ExecutionGate approval blocks LIVE
- MARKET and all prohibited instrument or financing types are blocked
- order and daily notional caps, ticker allowlist, side allowlist, and order
  type allowlist are enforced
- dry-run performs no credential, token, or network work
- CLI and SQLite audits remain redacted

`pytest` and `system-smoke` must never use real credentials or real network
calls. System smoke must remain `COMPLETED` with
`external_network_calls=false`.

## v2.17 Checkpoint Outcome

The only runtime assertion added by this checkpoint is a regression guard that
confirms `ExecutionMode.LIVE` remains blocked even when sandbox opt-in and
approved risk inputs are present. No live activation surface exists in v2.17.
