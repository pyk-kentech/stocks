# Operational Pipeline And Watch Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build persisted one-shot and explicit watch-loop paper operation workflows from existing local services.

**Architecture:** Add focused execution-state, alert, reporting, orchestration, and loop modules. Reuse existing scanner, basket, paper, replay, and policy evaluation APIs without calling CLI handlers internally.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite, argparse, pytest

---

### Task 1: Pipeline Models And Persistence
- [ ] Write failing PipelineRun and PipelineAlert repository round-trip tests.
- [ ] Implement models, migration-safe tables, and repository methods.
- [ ] Run targeted tests.

### Task 2: Alerts And Reports
- [ ] Write failing deterministic alert and summary tests.
- [ ] Implement pure alert generation and summary construction.
- [ ] Run targeted tests.

### Task 3: Scan And Paper Coordinators
- [ ] Write failing scan-only, no-candidate, paper storage, replay, and partial-failure tests.
- [ ] Implement staged scan and paper pipelines using existing services.
- [ ] Run targeted and existing scanner/basket/paper tests.

### Task 4: Policy Evaluation And Watch Loop
- [ ] Write failing policy recommendation and bounded-loop tests.
- [ ] Implement evaluation coordinator and explicit watch loop.
- [ ] Run targeted and existing policy tests.

### Task 5: CLI, Documentation, Verification
- [ ] Write failing CLI tests for seven operational commands.
- [ ] Implement parsers and handlers.
- [ ] Update README and WORK_SUMMARY.
- [ ] Run full verification and commit.
