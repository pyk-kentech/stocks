# Provider Pack #2: News Public Data Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe news-only Provider Pack that maps provider headlines into existing NEWS signals without changing shared signal scoring.

**Architecture:** Extend the combined provider-pack config and generic orchestration with NEWS selection. Enhance only the generic news normalization/import path to emit and honor richer provider fields while retaining legacy file behavior.

**Tech Stack:** Python, Pydantic, SQLite, argparse, pytest

---

### Task 1: News Configuration And Pack Type

**Files:**
- Modify: `src/stock_risk_mcp/provider_pack_config.py`
- Modify: `src/stock_risk_mcp/provider_packs.py`
- Modify: `src/stock_risk_mcp/provider_pack_pipeline.py`
- Create: `src/stock_risk_mcp/news_provider_pack.py`
- Test: `tests/test_provider_pack_config.py`
- Test: `tests/test_provider_packs.py`
- Test: `tests/test_news_provider_pack.py`

- [x] Write failing tests for NEWS pack type, `news.providers`, required headline/source_name columns, and missing-normalizer failure.
- [x] Run focused tests and confirm they fail for missing NEWS support.
- [x] Add NEWS config selection, pack success mapping, and wrapper.
- [x] Run focused tests and confirm they pass.

### Task 2: Rich News Normalization And Compatible Import

**Files:**
- Modify: `src/stock_risk_mcp/signal_normalizers.py`
- Modify: `src/stock_risk_mcp/data_import.py`
- Test: `tests/test_signal_normalizers.py`
- Test: `tests/test_news_provider_pack.py`
- Test: `tests/test_signal_cli.py`

- [x] Write failing tests for headline-to-title, INFO-to-LOW, raw payload preservation, News Pack scores, and imported source metadata.
- [x] Run focused tests and confirm expected failures.
- [x] Implement rich News Provider Pack normalization and optional import field precedence while preserving legacy behavior.
- [x] Run focused tests and confirm they pass.

### Task 3: CLI, Enrichment Regression, And Documentation

**Files:**
- Modify: `src/stock_risk_mcp/cli.py`
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`
- Test: `tests/test_news_provider_pack.py`
- Test: `tests/test_provider_pack_pipeline.py`
- Test: `tests/test_signal_enrichment.py`
- Test: `tests/test_signal_scoring.py`

- [x] Write failing `run-news-provider-pack` CLI test and regression assertions for common scoring and enrichment.
- [x] Run focused tests and confirm expected CLI failure.
- [x] Add CLI dispatch and document mappings, safety, and downstream use.
- [x] Run all provider-pack and signal tests.

### Task 4: Full Verification And Commit

**Files:**
- Modify: `docs/superpowers/plans/2026-06-14-news-provider-pack.md`

- [x] Run `pytest -q`.
- [x] Run `python -m compileall -q src`.
- [x] Run `git diff --check`.
- [x] Run `python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`.
- [x] Confirm `COMPLETED` and `external_network_calls=false`.
- [x] Mark the plan complete and commit with `Add news provider pack`.
