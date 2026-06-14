# Live Execution Safety Checkpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the v2.17 live-execution safety contract without adding a live runtime path.

**Architecture:** Preserve the existing unconditional `ExecutionMode.LIVE` block, document every future activation gate and fail-closed kill-switch rule, and add one narrow regression test. No production transport, credential loader, account-read service, or live CLI is created.

**Tech Stack:** Python, pytest, Markdown, existing OrderIntent/RiskGate/ExecutionGate models

---

### Task 1: Freeze The LIVE Block

**Files:**
- Create: `tests/test_live_execution_checkpoint.py`

- [ ] Add a regression test that supplies an approved matching RiskGate
  decision and sandbox opt-in, then asserts `ExecutionMode.LIVE` remains
  blocked with the existing explicit disabled reason.
- [ ] Run `pytest -q tests/test_live_execution_checkpoint.py` and confirm it
  passes without changing production runtime code.

### Task 2: Document The Safety Checkpoint

**Files:**
- Create: `docs/superpowers/specs/2026-06-15-live-execution-safety-checkpoint-design.md`
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document the future activation gates, exact acknowledgement phrase,
  unverified-PROD-URL block, and explicit credential sources.
- [ ] Document fail-closed global/session/broker/account kill switches checked
  before credential, token, network, plan, submit, cancel, or retry work.
- [ ] Document first-live restrictions, account-read separation, SELL ledger
  requirement, append-only audits, and redaction rules.
- [ ] State clearly that v2.17 adds no live runtime implementation and that
  LIVE remains blocked.

### Task 3: Validate And Commit

**Files:**
- Verify: repository-wide

- [ ] Run `pytest -q`.
- [ ] Run `python -m compileall -q src`.
- [ ] Run `git diff --check`.
- [ ] Run `python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`.
- [ ] Confirm system smoke is `COMPLETED` and
  `external_network_calls=false`.
- [ ] Run `git status --short`.
- [ ] Commit with `git commit -m "Document live execution safety checkpoint"`.
- [ ] Do not create a v2.17 tag.
