# Account-Read Manual MOCK Smoke And Ledger Reconciliation Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a redacted manual MOCK smoke workflow and honest aggregate-only local-ledger reconciliation.

**Architecture:** Wrap the v2.19 service with a separate smoke service and audit tables. Extend reconciliation to read only an explicit local ledger file, compare safe aggregate counts, and report unavailable details without guessing.

**Tech Stack:** Python, Pydantic, SQLite, argparse, pytest

---

### Task 1: Manual Smoke

- [ ] Write failing tests for offline plan, minimal set, hard maximum, gate
  blocking, dry-run dependency isolation, fake execution, redaction, and audit.
- [ ] Add smoke models/service and repository tables/helpers.
- [ ] Run focused tests until green.

### Task 2: Ledger Reconciliation

- [ ] Write failing tests for kill-switch blocking, missing ledger, aggregate
  mismatch counts, unavailable account details, no orders, and redacted audit.
- [ ] Extend reconciliation models/service with explicit local-ledger input.
- [ ] Run focused tests until green.

### Task 3: CLI And Documentation

- [ ] Write failing tests for smoke plan/run/reports/show and hardened
  reconciliation CLI.
- [ ] Add CLI integration and documentation.
- [ ] Run focused tests until green.

### Task 4: Validation

- [ ] Run pytest, compileall, diff check, and system smoke.
- [ ] Confirm system smoke `COMPLETED` and `external_network_calls=false`.
- [ ] Commit with `Harden account-read manual smoke and reconciliation`.
- [ ] Do not create a v2.20 tag.
