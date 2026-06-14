# Kiwoom Account-Read MOCK Opt-in Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit, redacted, MOCK-only account-read service without enabling PROD, LIVE, orders, strategy access, or automatic network tests.

**Architecture:** Create a separate account-read gate, transport, service, audit models, SQLite persistence, and CLI. Reuse the curated manifest and explicit credential loader, while ensuring gate and kill-switch checks happen before dependencies are invoked.

**Tech Stack:** Python, Pydantic, SQLite, argparse CLI, pytest

---

### Task 1: Models, Gate, And Transport

- [ ] Write failing tests for disabled defaults, gate requirements, endpoint
  class separation, limits, kill switch, and fake transport.
- [ ] Add minimal models, endpoint selector, gate, and strict MOCK transport.
- [ ] Run focused tests until green.

### Task 2: Service And Redacted Audit

- [ ] Write failing tests for offline health/plan, dry-run, fake execution,
  redaction, persistence, reports/show, and count-only reconciliation preview.
- [ ] Add minimal service and SQLite repository support.
- [ ] Run focused tests until green.

### Task 3: CLI And Documentation

- [ ] Write failing CLI tests for six JSON commands and privacy-safe output.
- [ ] Add parser/dispatch integration and documentation.
- [ ] Run focused tests until green.

### Task 4: Validate And Commit

- [ ] Run `pytest -q`.
- [ ] Run `python -m compileall -q src`.
- [ ] Run `git diff --check`.
- [ ] Run system smoke and confirm `COMPLETED` and
  `external_network_calls=false`.
- [ ] Commit with `Add Kiwoom account-read MOCK opt-in adapter`.
- [ ] Do not create a v2.19 tag.
