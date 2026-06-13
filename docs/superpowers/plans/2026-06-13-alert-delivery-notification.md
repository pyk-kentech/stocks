# Alert Delivery / Notification Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-only, deduplicated notification outbox over stored research alerts and summaries.

**Architecture:** Typed source converters feed isolated local channel adapters through one delivery service. SQLite persistence is opt-in, and pipeline notification is an error-isolated post-processing step.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite, argparse, pytest

---

### Task 1: Models And Persistence

- [ ] Write failing repository round-trip and dedupe tests.
- [ ] Add notification models, schema tables, and repository methods.
- [ ] Run focused tests.

### Task 2: Templates And Local LLM Conversion

- [ ] Write failing pipeline, report, brief, and LocalLLMResponse conversion tests.
- [ ] Implement severity filtering, sorting, disclaimers, preview limits, and dedupe keys.
- [ ] Run focused tests.

### Task 3: Channels And Outbox

- [ ] Write failing console, local-file, mock, disabled, duplicate, and failure tests.
- [ ] Implement local adapters and fault-isolated delivery aggregation.
- [ ] Run focused tests.

### Task 4: Digest, CLI, And Pipeline Integration

- [ ] Write failing digest, notification CLI, and opt-in pipeline notification tests.
- [ ] Implement digest generation, CLI commands, and post-pipeline notification.
- [ ] Run focused tests.

### Task 5: Documentation And Verification

- [ ] Update README and WORK_SUMMARY.
- [ ] Run `pytest -q`, `python -m compileall -q src`, and `git diff --check`.
- [ ] Commit verified changes.
