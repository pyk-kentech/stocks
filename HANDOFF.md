# Stock Risk MCP Handoff

## Repository State

- GitHub target: `https://github.com/pyk-kentech/stocks`
- Current branch: `master`
- Current release: `v2.23.0-official-sell-schema-evidence-import-review`
- Current implementation commit: `ced623e5aeaac7f8b7cb19656609dc946389c914`
- Design commit: `d983136`
- Expected working tree after publish: clean

The repository contains the full project history and release tags from
`v2.4.0-provider-pack-price-fx` through
`v2.23.0-official-sell-schema-evidence-import-review`.

## Current Capability

The project is a local-first, risk-capped trading research and execution
platform foundation. Implemented areas include:

- provider packs, unified import, scanner, enrichment, and reports
- paper trading, replay, policy evaluation, notifications, and dashboard
- realtime market data foundation and dynamic watchlist
- OrderIntent, RiskGate, ExecutionGate, and SQLite audit trails
- MOCK-only broker and Kiwoom sandbox adapter boundaries
- Kiwoom official endpoint manifest and opt-in read-only/account-read safety
- local ledger and SELL safety decisions
- offline Kiwoom SELL schema verification
- official SELL schema evidence import and append-only review

## v2.23 Boundary

v2.23 imports and reviews explicit local JSON/YAML official SELL schema
evidence. Complete evidence with latest `VALIDATED` review may make the offline
schema verifier report `VERIFIED`.

This does **not** grant execution permission:

- SELL dry-run remains blocked with
  `SELL_DRY_RUN_APPROVAL_DISABLED_IN_V2_23`.
- Actual sandbox SELL submission remains blocked.
- PROD and LIVE remain blocked.
- BUY sandbox behavior remains unchanged.

## Safety Invariants

- No live trading.
- No PROD order execution.
- No account-read-driven or reconciliation-driven automatic orders.
- No direct strategy broker/API access.
- MARKET, margin, short, credit, leverage, options, futures, and fractional
  shares remain blocked in protected execution paths.
- Tests and system smoke must not make external network calls.
- Raw account data, credentials, tokens, authorization headers, and secret
  paths must not be stored or printed.
- Local broker/API secrets must remain outside the repository.

## Important Documents

- `README.md`: usage and release behavior
- `WORK_SUMMARY.md`: cumulative implementation history
- `docs/superpowers/specs/`: approved release designs
- `docs/superpowers/plans/`: implementation plans
- `docs/superpowers/specs/2026-06-15-kiwoom-official-sell-schema-evidence-import-review-design.md`
- `docs/superpowers/plans/2026-06-15-kiwoom-official-sell-schema-evidence-import-review.md`

## Important v2.23 Files

- `src/stock_risk_mcp/kiwoom_official_sell_schema_evidence.py`
- `src/stock_risk_mcp/kiwoom_official_sell_schema_evidence_service.py`
- `src/stock_risk_mcp/kiwoom_sandbox_sell_schema_verifier.py`
- `src/stock_risk_mcp/kiwoom_sandbox_sell_dry_run.py`
- `src/stock_risk_mcp/database.py`
- `src/stock_risk_mcp/repository.py`
- `src/stock_risk_mcp/cli.py`

## Verification Baseline

The v2.23 implementation was validated with:

```powershell
pytest -q
python -m compileall -q src
git diff --check
python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs
```

Expected baseline:

- `pytest -q`: `569 passed`
- compileall: passed
- `git diff --check`: passed
- system-smoke: `COMPLETED`
- `external_network_calls=false`

Run the full baseline again after behavior changes and before release tags.

## Local Setup

```powershell
cd D:\KENTECH\stock\stock-risk-mcp
python -m pip install -e .[dev]
pytest -q
```

Do not inspect or import local broker secret directories into the repository.

## Useful v2.23 CLI

```powershell
python -m stock_risk_mcp.cli kiwoom-official-sell-schema-evidence-validate --evidence-file <explicit-json-or-yaml>
python -m stock_risk_mcp.cli kiwoom-official-sell-schema-evidence-import --db data/stock_risk_mcp.sqlite3 --evidence-file <explicit-json-or-yaml>
python -m stock_risk_mcp.cli kiwoom-official-sell-schema-evidence-list --db data/stock_risk_mcp.sqlite3
python -m stock_risk_mcp.cli kiwoom-official-sell-schema-evidence-show --db data/stock_risk_mcp.sqlite3 --evidence-id <evidence-id>
python -m stock_risk_mcp.cli kiwoom-official-sell-schema-evidence-review --db data/stock_risk_mcp.sqlite3 --evidence-id <evidence-id> --status VALIDATED --reviewed-by <operator>
```

## Recommended Next Release

Suggested next step: `v2.24 MOCK Sandbox SELL Dry-run Approval`.

Keep it as a separate approval boundary:

1. Require complete reviewed official evidence and verifier `VERIFIED`.
2. Require approved SellSafetyDecision, RiskGate, and SANDBOX ExecutionGate.
3. Keep actual sandbox SELL submission blocked.
4. Keep PROD and LIVE blocked.
5. Add explicit opt-in for dry-run approval.
6. Preserve local-only tests and `external_network_calls=false`.

## Release Workflow

1. Write and approve a design document.
2. Write an implementation plan.
3. Implement with focused tests first.
4. Run the full verification baseline.
5. Commit implementation.
6. Create a release tag only after explicit approval.

