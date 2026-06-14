# Kiwoom Real-Network Read-only Manual Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a manual-only, bounded, redacted smoke harness for the v2.14 Kiwoom MOCK read-only adapter.

**Architecture:** A separate smoke service validates activation and endpoint policy, performs dry-runs without credential or network access, and delegates explicitly enabled manual calls to the existing v2.14 service. Append-only smoke run/step tables store only redacted metadata, and separate CLI commands expose plan/run/list/show operations.

**Tech Stack:** Python 3.11, Pydantic, SQLite, argparse, pytest

---

### Task 1: Smoke Models And Endpoint Selection

**Files:**
- Create: `src/stock_risk_mcp/kiwoom_real_readonly_smoke_models.py`
- Create: `src/stock_risk_mcp/kiwoom_real_readonly_smoke.py`
- Test: `tests/test_kiwoom_real_readonly_smoke.py`

- [ ] Write failing tests for the offline plan, `minimal == ["ka10001"]`, explicit endpoint deduplication, the six-ID allowlist, and the hard maximum of three endpoints.
- [ ] Run `pytest -q tests/test_kiwoom_real_readonly_smoke.py` and verify failures are caused by missing smoke modules.
- [ ] Implement smoke statuses, run/step models, constants, plan generation, and pure endpoint selection helpers.
- [ ] Run the focused tests and confirm they pass.

### Task 2: Preflight And Dry-Run

**Files:**
- Modify: `src/stock_risk_mcp/kiwoom_real_readonly_smoke.py`
- Test: `tests/test_kiwoom_real_readonly_smoke.py`
- Test: `tests/test_kiwoom_real_readonly_smoke_safety.py`

- [ ] Write failing tests for disabled network, PROD, non-exact URL, missing explicit credential source, missing credential file selection, missing auth opt-in, WebSocket/ORDER/ACCOUNT_READ/AUTH/unknown rejection, and dry-run avoiding credential/token/HTTP access.
- [ ] Run the focused tests and verify expected failures.
- [ ] Implement preflight validation and dry-run orchestration. Dry-run must not call the credential loader or v2.14 service.
- [ ] Add safety source tests that prohibit secret-directory scanning and automatic network execution.
- [ ] Run the focused tests and confirm they pass.

### Task 3: Redacted SQLite Smoke Audit

**Files:**
- Modify: `src/stock_risk_mcp/database.py`
- Modify: `src/stock_risk_mcp/repository.py`
- Modify: `src/stock_risk_mcp/kiwoom_real_readonly_smoke.py`
- Test: `tests/test_kiwoom_real_readonly_smoke_repository.py`

- [ ] Write failing tests that save/list/show smoke runs and steps and assert token, authorization, appkey, secretkey, account number, bodies, and credential path/name are absent.
- [ ] Run the repository tests and verify failures are caused by missing tables/helpers.
- [ ] Add append-only `kiwoom_real_readonly_smoke_runs` and `kiwoom_real_readonly_smoke_steps` tables plus repository save/get/list helpers.
- [ ] Persist plan validation, dry-run, blocked, completed, partial, and failed outcomes using sanitized errors only.
- [ ] Run the focused tests and confirm they pass.

### Task 4: Fake-Only Execution Orchestration

**Files:**
- Modify: `src/stock_risk_mcp/kiwoom_real_readonly_smoke.py`
- Test: `tests/test_kiwoom_real_readonly_smoke_execution.py`

- [ ] Write failing tests using injected fake v2.14 services for completed, partial, and failed multi-endpoint runs.
- [ ] Assert steps run sequentially, one failure does not stop later validated endpoints, and no more than three endpoints execute.
- [ ] Run focused tests and verify expected failures.
- [ ] Implement bounded execution delegation and aggregate status/count calculation.
- [ ] Run focused tests and confirm they pass.

### Task 5: Separate Manual Smoke CLI

**Files:**
- Modify: `src/stock_risk_mcp/cli.py`
- Test: `tests/test_kiwoom_real_readonly_smoke_cli.py`

- [ ] Write failing CLI tests for `smoke-plan`, blocked default `smoke-run`, dry-run, `smoke-reports`, and `smoke-show`.
- [ ] Run focused CLI tests and verify expected failures.
- [ ] Add the four separate commands and JSON-safe output. Only a non-dry explicitly enabled run may load credentials and construct the real v2.14 service.
- [ ] Run focused CLI and existing v2.14 CLI tests.

### Task 6: Documentation And Regression Safety

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`
- Modify: `tests/test_kiwoom_real_readonly_smoke_safety.py`

- [ ] Document v2.15 purpose, v2.14 distinction, dry-run and placeholder real-MOCK examples, redaction, non-goals, and troubleshooting.
- [ ] Assert pytest/system-smoke paths do not invoke manual real-network smoke.
- [ ] Run Kiwoom v2.9-v2.15 and provider-pack regression tests.

### Task 7: Full Verification And Commit

**Files:**
- Verify all changed files

- [ ] Run `pytest -q`.
- [ ] Run `python -m compileall -q src`.
- [ ] Run `git diff --check`.
- [ ] Run `python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`.
- [ ] Confirm system-smoke is `COMPLETED` with `external_network_calls=false`.
- [ ] Confirm `git status --short` contains only intended changes.
- [ ] Commit with `git commit -m "Add Kiwoom real-network read-only manual smoke"`.
- [ ] Do not create a v2.15 tag.
