# v2.21 Local Ledger Sell-Safety Integration Design

## Scope

v2.21 adds an offline local ledger and a deterministic SellSafetyGate. SELL
intents require an approved matching SellSafetyDecision before RiskGate and
SANDBOX ExecutionGate approval. PROD and LIVE remain blocked.

The curated manifest contains a verified BUY endpoint (`kt10000`) and cancel
endpoint (`kt10003`), but no verified SELL submit endpoint or SELL request
schema. Therefore v2.21 keeps actual Kiwoom sandbox SELL submit blocked with
`SELL_SANDBOX_ORDER_SCHEMA_NOT_VERIFIED`. No endpoint or request field is
guessed.

## Local Ledger

Local ledger positions are manually/system maintained records, not broker
dumps. Position and reserved quantities are non-negative integers. Available
quantity is `quantity - reserved_quantity`, floored at zero. Snapshots are
point-in-time redacted copies. Transactions audit manual upsert changes.

## Sell Safety

SellSafetyGate blocks missing ledger, missing symbol, fractional/non-positive
quantity, insufficient available quantity, and unsafe reconciliation.
Reconciliation is optional for a local-ledger-only decision; when explicitly
provided, any state other than `COMPLETED` blocks or requires reconciliation.

SellSafety checks never load credentials, request tokens, call account-read,
call strategy, size orders, or submit orders.

## Order Integration

SELL RiskGate and SANDBOX ExecutionGate require an approved matching
SellSafetyDecision. BUY and PAPER behavior remain unchanged. The sandbox order
plan reports sell-safety status. Submit remains blocked at the adapter boundary
because the verified SELL schema is absent.

## Privacy And Testing

SQLite stores local ledger records and decisions only. It never stores broker
account numbers, raw holdings, balances, credentials, tokens, authorization,
or raw broker payloads. Tests are local/fake-only and system smoke remains
`external_network_calls=false`.
