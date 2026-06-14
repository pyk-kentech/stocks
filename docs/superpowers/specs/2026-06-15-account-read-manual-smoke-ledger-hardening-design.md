# v2.20 Account-Read Manual MOCK Smoke And Ledger Reconciliation Hardening

## Scope

v2.20 adds a manual MOCK smoke wrapper around the v2.19 account-read service
and hardens local-ledger reconciliation. It does not enable PROD, LIVE, ORDER,
strategy account reads, automatic sizing, or automatic network tests.

## Manual Smoke

Smoke plan is offline. Smoke run reuses every v2.19 activation and kill-switch
gate. The `minimal` endpoint set is exactly `kt00001`; explicit endpoint
selection is limited to two. Invalid selection blocks before credentials,
token, transport, or network.

Smoke audits store a redacted run and redacted per-endpoint steps only. They
contain status counts, endpoint classifications, status codes, sanitized
errors, and timestamps, but no raw account or transport payloads.

## Reconciliation

The v2.19 account-read service deliberately stores aggregate normalized counts
and discards raw holdings. v2.20 does not infer or reconstruct missing account
details.

Reconciliation accepts an explicit local-ledger JSON file containing a list of
safe local symbols. It compares the local symbol count with the stored account
summary symbol count and returns aggregate mismatch counts. Missing local
ledger returns `LOCAL_LEDGER_UNAVAILABLE`. Missing account summary returns
`ACCOUNT_DATA_UNAVAILABLE`.

Symbol-level details require explicit opt-in. Because current account-side
symbol details are not persisted, that request returns
`ACCOUNT_DETAILS_UNAVAILABLE` rather than guessing. Reconciliation never calls
strategy, sizing, execution, broker order, credential, token, or network code.

## Safety

Smoke and reconciliation require an explicitly inactive kill switch.
Reconciliation checks it before reading the local ledger or persisting a
preview. Tests use fake dependencies only. System smoke remains local with
`external_network_calls=false`.
