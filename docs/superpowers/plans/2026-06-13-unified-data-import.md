# Unified Data Import Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import local price, compliance, and signal CSV/JSON files in one fault-isolated, append-only run with persisted reports and CLI inspection.

**Architecture:** Add focused import-run models/reporting, generic local-file validation, source-specific append-only import functions, and a unified orchestrator. Extend the existing SQLite repository and CLI without changing standalone ingestion behavior.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite, argparse, pytest

---

### Task 1: Import Run Models And Persistence

**Files:**
- Create: `src/stock_risk_mcp/import_run.py`
- Create: `src/stock_risk_mcp/import_report.py`
- Modify: `src/stock_risk_mcp/database.py`
- Modify: `src/stock_risk_mcp/repository.py`
- Test: `tests/test_import_run.py`
- Test: `tests/test_import_report.py`

- [ ] Write failing tests for model totals, report serialization, and repository save/get/list.
- [ ] Run the focused tests and confirm they fail because the import-run API is missing.
- [ ] Add enums/models, aggregate report helper, SQLite tables, and repository methods.
- [ ] Run the focused tests and confirm they pass.

### Task 2: Validation And Append-Only Source Imports

**Files:**
- Create: `src/stock_risk_mcp/import_validators.py`
- Create: `src/stock_risk_mcp/data_import.py`
- Test: `tests/test_import_validators.py`
- Test: `tests/test_data_import.py`

- [ ] Write failing tests for CSV/JSON validation, malformed rows, price append-only dedupe, compliance dedupe/cutoff, and signal dedupe/cutoff.
- [ ] Run the focused tests and confirm expected failures.
- [ ] Implement row loading, required-column validation, and source-specific import functions.
- [ ] Run the focused tests and confirm they pass.

### Task 3: Unified Orchestration And CLI

**Files:**
- Modify: `src/stock_risk_mcp/data_import.py`
- Modify: `src/stock_risk_mcp/cli.py`
- Test: `tests/test_data_import.py`
- Test: `tests/test_import_report.py`

- [ ] Write failing tests for COMPLETED/PARTIAL/FAILED status and `import-data`, `import-runs`, `import-show`.
- [ ] Run the focused tests and confirm expected failures.
- [ ] Implement fault-isolated orchestration, run persistence, parser options, dispatch, and JSON output.
- [ ] Run the focused tests and confirm they pass.

### Task 4: Documentation And Verification

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document supported files, append-only dedupe keys, cutoff behavior, and the distinction between `import-data` and `ingest-prices`.
- [ ] Run `pytest -q`.
- [ ] Run `python -m compileall -q src`.
- [ ] Run `git diff --check`.
- [ ] Commit the verified changes.
