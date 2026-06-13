# Provider Normalization Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert provider-specific local CSV/JSON files into reproducible normalized files and optionally feed them into Unified Import.

**Architecture:** Typed normalizer results and runs wrap small generic mapping normalizers. An orchestration layer isolates failures, persists audit records on request, and maps successful outputs to existing import arguments.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite, CSV/JSON, argparse, pytest

---

### Task 1: Models, Persistence, And Registry

- [x] Write failing NormalizeRun persistence and registry tests.
- [x] Add typed run models, DB tables, repository methods, and default registry.
- [x] Run focused tests.

### Task 2: Generic Normalizers

- [x] Write failing price, signal, and FX normalization tests.
- [x] Implement shared file helpers and generic normalizers.
- [x] Run focused tests.

### Task 3: Orchestration, Import, And CLI

- [x] Write failing multi-source, CLI, and normalize-and-import tests.
- [x] Implement orchestration, FX import, and CLI commands.
- [x] Run focused tests.

### Task 4: Documentation And Verification

- [x] Update README and WORK_SUMMARY.
- [x] Run pytest, compileall, diff check, and system-smoke.
- [x] Commit verified changes.
