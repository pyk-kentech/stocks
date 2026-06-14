# Account-Read Opt-in Safety Checkpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the v2.18 account-read safety contract without adding account-read runtime behavior.

**Architecture:** Keep all manifest `ACCOUNT_READ` endpoints runtime-disabled, preserve existing service separation, document future activation and privacy gates, and add fake-only regression guards. No account transport, credential access, PROD access, or live-order path is created.

**Tech Stack:** Python, pytest, Markdown, v2.13 curated endpoint manifest, existing real READ_ONLY transport and ExecutionGate

---

### Task 1: Freeze Account-Read And LIVE Blocking

**Files:**
- Create: `tests/test_account_read_checkpoint.py`

- [ ] Assert the curated manifest account candidates are exactly classified
  `ACCOUNT_READ`, require an account, and remain runtime-disabled.
- [ ] Assert the existing real READ_ONLY transport rejects every account
  candidate before fake HTTP is called.
- [ ] Assert `ExecutionMode.LIVE` remains blocked.
- [ ] Run `pytest -q tests/test_account_read_checkpoint.py`.

### Task 2: Document The Future Account-Read Boundary

**Files:**
- Create: `docs/superpowers/specs/2026-06-15-account-read-opt-in-safety-checkpoint-design.md`
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document explicit account-read activation, account confirmation,
  fingerprint confirmation, exact acknowledgement phrase, endpoint allowlist,
  and MOCK-first/PROD-blocked policy.
- [ ] Document strategy, market-data, sandbox-order, live-order, and risk
  separation.
- [ ] Document fail-closed kill-switch ordering before credential, token,
  network, or account work.
- [ ] Document normalized storage limits, default-output privacy, audit
  redaction, and fake-only testing.

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
- [ ] Commit with
  `git commit -m "Document account-read opt-in safety checkpoint"`.
- [ ] Do not create a v2.18 tag.
