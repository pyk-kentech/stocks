# Policy Evaluation Suite And Promotion Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aggregate comparable Full Policy Replay pairs across multiple ReplayRuns and provide an explicit, auditable StrategyPolicy promotion gate.

**Architecture:** Add typed suite/promotion records and SQLite persistence, a batch replay coordinator, a pure completed-pair evaluator, explicit promotion/status services, and six CLI commands. Keep replay artifacts memory-only by default and never auto-activate policies.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite, argparse, pytest

---

### Task 1: Models And Persistence

- [ ] Add failing model and repository round-trip tests for evaluation suites and promotion proposals.
- [ ] Add the models, two SQLite tables, repository save/get/list methods, and row converters.
- [ ] Run targeted repository tests.

### Task 2: Completed-Pair Evaluation

- [ ] Add failing tests for both-completed inclusion and baseline-only, candidate-only, both-NO_DATA exclusion.
- [ ] Add failing tests for minimum runs, minimum completed pairs, no-data rate, candidate count, ACCEPT, and REJECT.
- [ ] Implement pure pair aggregation and recommendation notes.
- [ ] Run targeted suite tests.

### Task 3: Replay Batch

- [ ] Add failing tests for reuse, execution, failure isolation, and result pair return.
- [ ] Implement batch coordination using existing Full Policy Replay.
- [ ] Run batch and existing replay tests.

### Task 4: Promotion Gate

- [ ] Add failing tests for proposal mapping, explicit approve, approved-only activate, active retirement, and draft activation rejection.
- [ ] Implement proposal creation and explicit status transitions.
- [ ] Run promotion and existing strategy policy tests.

### Task 5: CLI And Documentation

- [ ] Add failing tests for six new CLI commands and required suite output fields.
- [ ] Implement parsers and handlers.
- [ ] Document suite/promotion behavior and operational warnings.
- [ ] Run full verification, commit, and confirm clean worktree.
