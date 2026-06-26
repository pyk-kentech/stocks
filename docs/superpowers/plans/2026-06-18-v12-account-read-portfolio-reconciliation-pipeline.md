# v12.0 Account-Read / Portfolio Reconciliation Pipeline

## Architecture

Introduce a new independent `account_read_*` layer for canonical read-only account snapshots and a separate `portfolio_reconciliation_*` layer for paper-vs-account and target-vs-account reconciliation. Keep orchestration in `portfolio_reconciliation_integration_engine.py` and keep account canonicalization and reconciliation math in their own engines.

## Work Items

- Add canonical `account_read_models.py` and `portfolio_reconciliation_models.py`
- Add account-read guard, fixture loader, adapter preview layer, and snapshot engine
- Add reconciliation engine and orchestration/integration engine
- Wire CLI report commands
- Extend system smoke with an offline v12 path
- Add focused tests and run full verification

## Verification

- Focused pytest for `account_read_*`, `portfolio_reconciliation_*`, and `test_system_smoke.py`
- Standalone `test_system_smoke.py`
- Full repository `pytest -q`
- Commit and tag `v12.0.0-account-read-portfolio-reconciliation-pipeline`
