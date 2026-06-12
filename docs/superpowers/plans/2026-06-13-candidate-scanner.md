# Candidate Scanner And Universe Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and persist as-of-date candidate universes that feed existing TradePlan, Basket, and Replay workflows.

**Architecture:** Reuse the current as-of price, indicator, setup, TradePlan, basket, policy, and replay layers. Add focused universe, filter, scanner, orchestration, and conversion modules with opt-in persistence.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite, argparse, pytest

---

### Task 1: Scan Models And Persistence
- [ ] Write failing model/repository round-trip tests.
- [ ] Implement scan models, SQLite tables, repository methods, and row conversion.
- [ ] Run targeted tests.

### Task 2: Universe And Filters
- [ ] Write failing DB/file/manual universe and scoring/filter tests.
- [ ] Implement as-of universe loaders and pure filter rules.
- [ ] Run targeted tests.

### Task 3: Scanner Pipeline
- [ ] Write failing tests for as-of cutoff, insufficient data, policy metadata, compliance, ranking, and limits.
- [ ] Implement one-ticker scanner and full scan pipeline.
- [ ] Run scanner and existing indicator/setup tests.

### Task 4: Basket And Replay Conversion
- [ ] Write failing tests for scan-to-basket opt-in saving and scan-to-replay metadata.
- [ ] Implement downstream conversion using stored TradePlan metadata.
- [ ] Run conversion, basket, and replay tests.

### Task 5: CLI, Documentation, Verification
- [ ] Write failing tests for all five CLI commands.
- [ ] Implement parsers and handlers.
- [ ] Update README and WORK_SUMMARY.
- [ ] Run full verification, commit, and confirm clean worktree.
