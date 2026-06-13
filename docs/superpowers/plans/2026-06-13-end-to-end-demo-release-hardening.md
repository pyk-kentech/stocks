# End-to-End Demo / Release Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate the complete local stock-risk workflow through one deterministic, failure-isolated demo and release-smoke interface.

**Architecture:** A typed orchestrator calls existing public Python APIs and records every step result. Thin system-smoke, release-check, and CLI wrappers expose structured local validation without network access or order execution.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite, argparse, pathlib, pytest

---

### Task 1: Demo Models And Summary

- [ ] Write failing model, status aggregation, and summary-file tests.
- [ ] Implement demo models and JSON-safe summary writer.
- [ ] Run focused tests.

### Task 2: Local Demo Orchestration

- [ ] Write failing complete-demo and import-failure isolation tests.
- [ ] Implement deterministic connector-to-dashboard orchestration using existing APIs.
- [ ] Run focused tests.

### Task 3: System Smoke And Release Check

- [ ] Write failing smoke and release checklist tests.
- [ ] Implement local smoke summary and non-mutating release checklist.
- [ ] Run focused tests.

### Task 4: CLI And Documentation

- [ ] Write failing run-local-demo, system-smoke, and release-check CLI tests.
- [ ] Add CLI commands and document release workflow.
- [ ] Run focused tests.

### Task 5: Verification

- [ ] Run full pytest, compileall, and diff checks.
- [ ] Run required `system-smoke` command.
- [ ] Commit verified changes.
