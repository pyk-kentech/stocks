# External Data Connector Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a network-free connector interface, deterministic mock/local connectors, persisted runs, and Unified Import integration.

**Architecture:** Connectors return normalized file outputs and run metadata. A sequential pipeline isolates connector failures, persists every run, and optionally maps successful outputs into the existing Unified Import Pipeline.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite, argparse, pytest

---

### Task 1: Connector Models And Persistence

**Files:** `connector_run.py`, `connectors.py`, `database.py`, `repository.py`, `tests/test_connector_run.py`, `tests/test_connectors.py`

- [ ] Write failing model and repository round-trip tests.
- [ ] Implement connector enums/models, protocol, schema, and repository methods.
- [ ] Run focused tests.

### Task 2: Outputs, Registry, Mock And Local Connectors

**Files:** `connector_outputs.py`, `connector_registry.py`, `mock_connectors.py`, `local_connector.py`, matching tests.

- [ ] Write failing output, registry, deterministic mock, and local-file tests.
- [ ] Implement normalized output helpers and connectors.
- [ ] Run focused tests.

### Task 3: Pipeline And CLI

**Files:** `connector_pipeline.py`, `cli.py`, `data_import.py`, `tests/test_connector_pipeline.py`

- [ ] Write failing tests for continued execution, no-output failed import, aggregate status, and CLI inspection.
- [ ] Implement sequential persistence, output mapping, import integration, and five CLI commands.
- [ ] Run focused and full tests.

### Task 4: Documentation And Verification

**Files:** `README.md`, `WORK_SUMMARY.md`

- [ ] Document skeleton-only scope and command usage.
- [ ] Run `pytest -q`, `python -m compileall -q src`, and `git diff --check`.
- [ ] Commit verified changes.
