# Kiwoom Official Endpoint Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a curated official Kiwoom endpoint manifest with deterministic schema, classification, and runtime-safety validation.

**Architecture:** A committed JSON manifest is loaded into strict models and validated without transport integration. Three read-only CLI commands list, show, and validate manifest entries while existing deterministic and mock runtime allowlists remain unchanged.

**Tech Stack:** Python, Pydantic, JSON, argparse, pytest

---

### Task 1: Curated Manifest Models And Fixture

**Files:**
- Create: `configs/kiwoom_official_endpoint_manifest.json`
- Create: `src/stock_risk_mcp/kiwoom_official_manifest.py`
- Test: `tests/test_kiwoom_official_manifest.py`

- [ ] Write failing tests for strict manifest schema, official source presence, class counts, and representative entries.
- [ ] Run focused tests and verify RED.
- [ ] Add strict models and loader.
- [ ] Add only endpoints whose ID, path, method, name, and category were directly verified from official guide pages.
- [ ] Run focused tests and verify GREEN.

### Task 2: Manifest Safety Validator

**Files:**
- Create: `src/stock_risk_mcp/kiwoom_official_manifest_validator.py`
- Test: `tests/test_kiwoom_official_manifest_validator.py`

- [ ] Write failing tests for duplicate pairs, disabled forbidden classes, disabled dangerous paths, official source host, and runtime allowlist isolation.
- [ ] Verify RED.
- [ ] Implement deterministic validation and structured result.
- [ ] Verify GREEN.

### Task 3: CLI

**Files:**
- Modify: `src/stock_risk_mcp/cli.py`
- Create: `tests/test_kiwoom_official_manifest_cli.py`

- [ ] Write failing tests for list filters, validate output, and show selectors.
- [ ] Verify RED.
- [ ] Add three JSON-only CLI commands with no network or secret options.
- [ ] Verify GREEN.

### Task 4: Safety And Documentation

**Files:**
- Create: `tests/test_kiwoom_official_manifest_safety.py`
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Write safety tests proving no manifest path enters v2.11/v2.12 allowlists and no network/secret/runtime integration exists.
- [ ] Document curated scope, class policy, runtime separation, and deferred full coverage.
- [ ] Run focused v2.11-v2.13 and safety tests.

### Task 5: Full Verification And Commit

- [ ] Run `pytest -q`.
- [ ] Run `python -m compileall -q src`.
- [ ] Run `git diff --check`.
- [ ] Run `python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`.
- [ ] Confirm `COMPLETED` and `external_network_calls=false`.
- [ ] Commit with `git commit -m "Add Kiwoom official endpoint manifest verification"`.
- [ ] Report without creating a v2.13 tag.
