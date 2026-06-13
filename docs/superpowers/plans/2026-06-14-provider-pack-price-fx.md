# Provider Pack #1: Price and FX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an auditable, config-driven Price and FX Provider Pack that safely connects raw acquisition to normalization and unified import.

**Architecture:** A combined provider config supplies both connector and normalization settings. A thin orchestration pipeline reuses existing HTTP/local acquisition, normalizer registry, unified import, and repository patterns while applying price-core combined status rules.

**Tech Stack:** Python, Pydantic, SQLite, argparse, pytest

---

### Task 1: Models, Configuration, and Persistence

**Files:**
- Create: `src/stock_risk_mcp/provider_packs.py`
- Create: `src/stock_risk_mcp/provider_pack_config.py`
- Modify: `src/stock_risk_mcp/database.py`
- Modify: `src/stock_risk_mcp/repository.py`
- Test: `tests/test_provider_packs.py`
- Test: `tests/test_provider_pack_config.py`

- [x] Write failing model, config validation, and repository round-trip tests.
- [x] Run the focused tests and confirm failures are caused by missing provider-pack modules.
- [x] Implement ProviderPack enums/model, combined config loading/validation, SQLite table, and repository helpers.
- [x] Run focused tests and confirm they pass.

### Task 2: Provider Pack Orchestration

**Files:**
- Create: `src/stock_risk_mcp/provider_pack_pipeline.py`
- Create: `src/stock_risk_mcp/price_provider_pack.py`
- Create: `src/stock_risk_mcp/fx_provider_pack.py`
- Test: `tests/test_provider_pack_pipeline.py`
- Test: `tests/test_price_provider_pack.py`
- Test: `tests/test_fx_provider_pack.py`

- [x] Write failing tests for network-off, fake HTTP price/FX flows, missing normalizer, and combined status rules.
- [x] Run focused tests and confirm expected failures.
- [x] Implement raw acquisition, provider-specific normalization source creation, unified import handoff, status aggregation, and pack wrappers.
- [x] Run focused tests and confirm they pass.

### Task 3: CLI and Documentation

**Files:**
- Modify: `src/stock_risk_mcp/cli.py`
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`
- Test: `tests/test_provider_pack_pipeline.py`

- [x] Write failing CLI tests for run/list/show commands without a separate normalizer config.
- [x] Run focused CLI tests and confirm expected failures.
- [x] Add parser and dispatch branches, JSON output, README workflow, and work summary.
- [x] Run all provider-pack tests and confirm they pass.

### Task 4: Full Verification and Commit

**Files:**
- Modify: `docs/superpowers/plans/2026-06-14-provider-pack-price-fx.md`

- [x] Run `pytest -q`.
- [x] Run `python -m compileall -q src`.
- [x] Run `git diff --check`.
- [x] Run `python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`.
- [x] Confirm system smoke is COMPLETED with `external_network_calls=false`.
- [x] Mark the plan complete and commit the implementation.
