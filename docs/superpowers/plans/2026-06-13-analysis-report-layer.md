# Analysis Report Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build deterministic structured JSON and Markdown reports from stored operational research records.

**Architecture:** Focused context builders read repository records, typed report builders create evidence-oriented reports, and shared render/persistence helpers serve all report CLI commands.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite, argparse, pytest

---

### Task 1: Models, Renderers, And Persistence

- [ ] Write failing tests for report model, JSON/Markdown output, disclaimer, and repository round trip.
- [ ] Implement models, templates, renderers, schema, and repository methods.
- [ ] Run focused tests.

### Task 2: Source Context And Builders

- [ ] Write failing pipeline, scan, basket/replay, and policy report tests.
- [ ] Implement repository-backed deterministic context and report builders.
- [ ] Run focused tests.

### Task 3: CLI And Output Persistence

- [ ] Write failing tests for six CLI commands, optional DB save, successful output file, and failed output file warning.
- [ ] Implement common report command runner and persistence metadata.
- [ ] Run focused and full tests.

### Task 4: Documentation And Verification

- [ ] Update README and WORK_SUMMARY.
- [ ] Run `pytest -q`, `python -m compileall -q src`, and `git diff --check`.
- [ ] Commit verified changes.
