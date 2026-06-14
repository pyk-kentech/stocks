# Kiwoom REST Read-only Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fake-transport-only Kiwoom REST read-only adapter using internal deterministic endpoints, strict allowlisting, sanitized audits, and no real credentials or network.

**Architecture:** Models and allowlist define the safe contract. A transport protocol isolates deterministic fake responses from a permanently disabled real-transport stub. The client handles exact endpoint validation and continuation, while the adapter normalizes outputs and an orchestration helper persists sanitized audits.

**Tech Stack:** Python, Pydantic, Protocol, SQLite, argparse, pytest

---

### Task 1: Add Models And Strict Internal Allowlist

**Files:**
- Create: `src/stock_risk_mcp/kiwoom_readonly_models.py`
- Create: `src/stock_risk_mcp/kiwoom_readonly_allowlist.py`
- Create: `tests/test_kiwoom_readonly_models.py`
- Create: `tests/test_kiwoom_readonly_allowlist.py`

- [ ] Write failing tests for enums, endpoint/token/normalized/audit models, ticker normalization, and JSON serialization.
- [ ] Write failing tests accepting the seven exact internal endpoint pairs and rejecting unknown, mismatched, disabled, non-read-only, order-like, account-like, balance-like, position-like, fill-like, and execution-like endpoints.
- [ ] Run both test files and verify RED.
- [ ] Implement models and the fixed internal allowlist. Do not include OAUTH or realtime endpoint definitions.
- [ ] Re-run focused tests and verify GREEN.

### Task 2: Add Fake And Disabled Transport

**Files:**
- Create: `src/stock_risk_mcp/kiwoom_transport.py`
- Create: `tests/test_kiwoom_transport.py`

- [ ] Write failing tests for deterministic default fixtures across all seven paths, configured continuation/error responses, sanitized call metadata, and disabled real transport.
- [ ] Verify RED.
- [ ] Implement `KiwoomTransport` Protocol, constant fixture factory, `FakeKiwoomTransport`, `DisabledNetworkError`, and `RealKiwoomHttpTransport` whose `post()` always raises.
- [ ] Re-run focused tests and verify GREEN.

### Task 3: Add KiwoomRestClient

**Files:**
- Create: `src/stock_risk_mcp/kiwoom_rest_client.py`
- Create: `tests/test_kiwoom_rest_client.py`

- [ ] Write failing tests for exact allowlist validation, fake bearer usage without exposure, bounded continuation merge, normalized transport errors, and response envelopes that omit authorization/token/header fields.
- [ ] Verify RED.
- [ ] Implement `KiwoomRestClient.request_readonly` with a default fake token and max continuation pages.
- [ ] Re-run focused tests and verify GREEN.

### Task 4: Add Read-only Adapter And Normalization

**Files:**
- Create: `src/stock_risk_mcp/kiwoom_readonly_adapter.py`
- Create: `tests/test_kiwoom_readonly_adapter.py`

- [ ] Write failing tests for health/endpoints, stock info, quote, rankings, flow, chart, condition list/run, and PROD_DISABLED JSON-safe behavior.
- [ ] Verify RED.
- [ ] Implement adapter methods using only internal endpoint IDs/paths and normalize records into the requested models.
- [ ] Re-run focused tests and verify GREEN.

### Task 5: Add Sanitized SQLite Audit

**Files:**
- Modify: `src/stock_risk_mcp/database.py`
- Modify: `src/stock_risk_mcp/repository.py`
- Create: `src/stock_risk_mcp/kiwoom_readonly_service.py`
- Create: `tests/test_kiwoom_readonly_repository.py`
- Create: `tests/test_kiwoom_readonly_service.py`

- [ ] Write failing repository tests for append-only request/response audit save/list and selector filters.
- [ ] Write failing service tests proving transport requests save sanitized audits and failures remain JSON-safe.
- [ ] Verify RED.
- [ ] Add `kiwoom_readonly_requests` and `kiwoom_readonly_responses` tables and repository helpers.
- [ ] Implement service orchestration without storing token, authorization, headers, secrets, raw environment, or external paths.
- [ ] Re-run focused tests and verify GREEN.

### Task 6: Add Nine CLI Commands

**Files:**
- Modify: `src/stock_risk_mcp/cli.py`
- Create: `tests/test_kiwoom_readonly_cli.py`

- [ ] Write failing CLI tests for health, endpoints, stock info, quote, rankings, flow, chart, condition list, and condition run.
- [ ] Assert PROD_DISABLED and normal validation errors return JSON without traceback.
- [ ] Assert all outputs omit authorization/token/secret/account values.
- [ ] Verify RED.
- [ ] Add parsers and command routing. Add no network-enable, OAuth, token, credential, account, or order flags.
- [ ] Re-run CLI tests and verify GREEN.

### Task 7: Add Safety And Regression Tests

**Files:**
- Create: `tests/test_kiwoom_readonly_safety.py`

- [ ] Write tests proving no official-looking/non-internal endpoint exists, no forbidden endpoint terms exist, no HTTP/network/Kiwoom SDK import exists, no external secret path text exists, no environment enumeration exists, and no strategy/execution integration exists.
- [ ] Verify `.gitignore` already contains the required local broker/API secret patterns without inspecting external directories.
- [ ] Run safety tests plus broker adapter, order intent, realtime, and provider-pack regressions.
- [ ] Make only minimal changes needed for GREEN.

### Task 8: Document v2.11

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document purpose, fake transport default, internal endpoint-only contract, official mapping deferral, read-only categories, secret/network/order/account prohibitions, and v2.12-v2.13 future path.
- [ ] Do not include any real local key path or credential example.
- [ ] Run `git diff --check`.

### Task 9: Full Verification And Commit

**Files:**
- Verify all changed files

- [ ] Run `pytest -q`.
- [ ] Run `python -m compileall -q src`.
- [ ] Run `git diff --check`.
- [ ] Run `python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`.
- [ ] Verify smoke is `COMPLETED` and `external_network_calls=false`.
- [ ] Confirm no secret-like path/file is staged and local broker/API ignore patterns remain.
- [ ] Commit implementation:

```powershell
git add .
git commit -m "Add Kiwoom REST read-only adapter"
```

- [ ] Run `git status --short` and record the final commit hash. Do not create a v2.11 tag.
