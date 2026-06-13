# FX-aware Portfolio / Risk Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Interpret account-currency inputs using stored/manual FX while preserving existing trading-currency risk behavior.

**Architecture:** A pure FX model and service build a pipeline currency context. The existing pipeline receives converted trading values, then small enrichment helpers attach nullable FX metadata to generated artifacts and presentation layers.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite, argparse, pytest

---

### Task 1: FX Models, Lookup, And Sizing Wrapper

- [x] Write failing conversion, lookup, stale, missing, and sizing-wrapper tests.
- [x] Implement `fx.py`, `fx_service.py`, `portfolio_currency.py`, and `fx_risk.py`.
- [x] Run focused tests.

### Task 2: Artifact Metadata And Persistence

- [x] Write failing TradePlan, basket, paper, and PipelineRun propagation tests.
- [x] Add backward-compatible model fields, migrations, repository mapping, and enrichment.
- [x] Run focused tests.

### Task 3: Pipeline, CLI, And Presentation

- [x] Write failing pipeline conversion, FX CLI, report, notification, and dashboard tests.
- [x] Integrate context into paper/watch pipeline and presentation layers.
- [x] Run focused tests.

### Task 4: Documentation And Verification

- [x] Update README and WORK_SUMMARY.
- [x] Run pytest, compileall, diff check, and system-smoke.
- [x] Commit verified changes.
