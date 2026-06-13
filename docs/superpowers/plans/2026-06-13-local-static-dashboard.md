# Local Static Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate safe, self-contained local HTML dashboards from stored research and paper-trading evidence.

**Architecture:** Repository-backed section builders create typed DashboardSection records. A pure renderer escapes values and emits inline-only HTML, while a coordinator handles output persistence, build status, and optional SQLite audit records.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite, argparse, stdlib html/json/pathlib/webbrowser, pytest

---

### Task 1: Models And Persistence

- [ ] Write failing DashboardBuildResult repository round-trip tests.
- [ ] Implement dashboard models, SQLite schema, and repository methods.
- [ ] Run focused tests.

### Task 2: Safe HTML Renderer

- [ ] Write failing escaping, disclaimer, section ordering, and external-resource tests.
- [ ] Implement inline assets and pure HTML rendering helpers.
- [ ] Run focused tests.

### Task 3: Dashboard Sections And Builders

- [ ] Write failing overview, pipeline, daily, policy, no-data, and output-failure tests.
- [ ] Implement repository-backed section builders and file build coordinator.
- [ ] Run focused tests.

### Task 4: CLI And Pipeline Integration

- [ ] Write failing dashboard CLI and opt-in pipeline dashboard tests.
- [ ] Implement CLI commands and error-isolated post-pipeline build behavior.
- [ ] Run focused tests.

### Task 5: Optional Preview And Documentation

- [ ] Add a dependency-free local preview/smoke script.
- [ ] Update README and WORK_SUMMARY with static/local-only safety boundaries.
- [ ] Run full verification and commit.
