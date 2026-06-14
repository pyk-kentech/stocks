# Local Ledger Sell-Safety Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add offline local-ledger proof and sell-safety decisions while keeping actual sandbox SELL submission blocked.

**Architecture:** Persist validated local positions, transactions, and snapshots; evaluate SELL eligibility in a separate gate; require the decision in RiskGate and SANDBOX ExecutionGate; report but do not submit SELL through Kiwoom.

**Tech Stack:** Python, Pydantic, SQLite, argparse, pytest

---

### Task 1: Local Ledger

- [ ] TDD integer quantity validation, upsert, reservation, available quantity,
  listing, transactions, and snapshots.
- [ ] Add models, service, SQLite tables, and repository methods.

### Task 2: Sell Safety And Gates

- [ ] TDD missing/insufficient/sufficient ledger decisions and reconciliation
  blocking.
- [ ] TDD SELL RiskGate and SANDBOX ExecutionGate requiring approved matching
  decisions while preserving BUY/PAPER behavior.
- [ ] Keep sandbox SELL submit blocked with verified-schema reason.

### Task 3: CLI And Documentation

- [ ] TDD seven local-ledger/sell-safety CLI commands.
- [ ] Extend sandbox plan output with sell-safety state.
- [ ] Update README and WORK_SUMMARY.

### Task 4: Validation

- [ ] Run pytest, compileall, diff check, and system smoke.
- [ ] Commit with `Add local ledger sell-safety integration`.
- [ ] Do not create a v2.21 tag.
