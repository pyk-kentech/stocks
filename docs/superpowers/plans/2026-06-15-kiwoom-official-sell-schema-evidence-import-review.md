# Kiwoom Official SELL Schema Evidence Import And Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an offline explicit-file import, validation, review, and audit workflow for official SELL schema evidence without enabling SELL dry-run or submission.

**Architecture:** Parse strict JSON/YAML evidence from one explicit path, reject sensitive or unofficial content before persistence, and store normalized append-only audits. Integrate only latest validated review into the v2.22 verifier while adding an unconditional v2.23 dry-run policy block.

**Tech Stack:** Python, Pydantic, PyYAML, SQLite, argparse, pytest

---

### Task 1: Evidence Models And Validator

**Files:**
- Create: `src/stock_risk_mcp/kiwoom_official_sell_schema_evidence.py`
- Create: `src/stock_risk_mcp/kiwoom_official_sell_schema_evidence_service.py`
- Test: `tests/test_kiwoom_official_sell_schema_evidence.py`

- [ ] Write failing tests for explicit JSON/YAML parsing, manifest matching,
  required mappings, unofficial/guessed evidence, missing files, checksum, and
  sensitive-pattern rejection.
- [ ] Run tests and confirm missing modules fail.
- [ ] Implement strict models and offline validator with no directory search,
  credential, token, or network dependency.
- [ ] Run tests and confirm safe validation passes.

### Task 2: Persistence And Review Audit

**Files:**
- Modify: `src/stock_risk_mcp/database.py`
- Modify: `src/stock_risk_mcp/repository.py`
- Test: `tests/test_kiwoom_official_sell_schema_evidence_repository.py`

- [ ] Write failing tests for safe normalized import, field rows, checksum,
  append-only reviews, latest review, and redacted list/show.
- [ ] Add four SQLite tables and repository helpers.
- [ ] Implement validate-then-import and append-only review service methods.
- [ ] Run repository tests.

### Task 3: Verifier Integration And v2.23 Dry-Run Block

**Files:**
- Modify: `src/stock_risk_mcp/kiwoom_sandbox_sell_schema_verifier.py`
- Modify: `src/stock_risk_mcp/kiwoom_sandbox_sell_dry_run.py`
- Test: `tests/test_kiwoom_official_sell_schema_verifier_integration.py`

- [ ] Write failing tests proving absent/unreviewed/rejected evidence remains
  `UNVERIFIED`, reviewed complete evidence becomes `VERIFIED`, and dry-run
  remains blocked by v2.23 policy.
- [ ] Integrate latest eligible reviewed evidence into verifier.
- [ ] Add unconditional `SELL_DRY_RUN_APPROVAL_DISABLED_IN_V2_23`.
- [ ] Prove actual sandbox SELL remains blocked and BUY remains unchanged.

### Task 4: CLI And Safety

**Files:**
- Modify: `src/stock_risk_mcp/cli.py`
- Create: `tests/test_kiwoom_official_sell_schema_evidence_cli.py`
- Create: `tests/test_kiwoom_official_sell_schema_evidence_safety.py`

- [ ] Write failing tests for validate/import/list/show/review JSON commands,
  missing-file safe errors, and sanitized output.
- [ ] Add command parsers and offline dispatch.
- [ ] Add source-level guards against credential/token/network/account/strategy
  dependencies and secret path scanning.
- [ ] Run CLI and safety tests.

### Task 5: Documentation, Validation, And Commit

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document evidence format, review workflow, verifier integration, v2.23
  dry-run block, actual SELL block, and v2.24 boundary.
- [ ] Run full pytest, compileall, diff check, and system smoke.
- [ ] Commit with `Add official SELL schema evidence import and review`.
- [ ] Do not create a v2.23 tag.
