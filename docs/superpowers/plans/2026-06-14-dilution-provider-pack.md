# Dilution Provider Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a config-driven Dilution Provider Pack that imports conservative dilution signals without changing common signal scoring or CompanyRisk hard-block inputs.

**Architecture:** Extend the existing Provider Pack orchestration with a `dilution` group and pack type. Use rich-provider mode in `GenericDilutionCSVNormalizer` to map provider risk values to fixed non-positive signal scores, then let Unified Import preserve those explicit values. Legacy dilution normalization/import and Risk Engine behavior remain unchanged.

**Tech Stack:** Python, Pydantic, SQLite repository, argparse CLI, pytest

---

### Task 1: Lock The Provider Contract With Tests

**Files:**
- Create: `tests/test_dilution_provider_pack.py`
- Modify: `tests/test_provider_pack_config.py`
- Modify: `tests/test_provider_packs.py`
- Modify: `tests/test_signal_normalizers.py`

- [ ] **Step 1: Write failing config and model tests**

Add tests proving `ProviderPackConfig.dilution`, `ProviderPackType.DILUTION`, required `dilution_risk` columns, and rich dilution normalization are required.

- [ ] **Step 2: Write failing end-to-end pack tests**

Add local-file, disabled HTTP, CLI, mapping, metadata preservation, enrichment, common-score isolation, and no-CompanyRisk-bridge tests.

- [ ] **Step 3: Run tests to verify RED**

Run:

```powershell
pytest -q tests/test_dilution_provider_pack.py tests/test_provider_pack_config.py tests/test_provider_packs.py tests/test_signal_normalizers.py
```

Expected: failures because the dilution provider group, pack type, CLI, and rich normalization path do not exist.

### Task 2: Add Provider Pack Dilution Routing

**Files:**
- Create: `src/stock_risk_mcp/dilution_provider_pack.py`
- Modify: `src/stock_risk_mcp/provider_config.py`
- Modify: `src/stock_risk_mcp/http_connector.py`
- Modify: `src/stock_risk_mcp/provider_pack_config.py`
- Modify: `src/stock_risk_mcp/provider_packs.py`
- Modify: `src/stock_risk_mcp/provider_pack_pipeline.py`
- Modify: `src/stock_risk_mcp/cli.py`

- [ ] **Step 1: Add DILUTION types and config group**

Add `ProviderDataKind.DILUTION`, `ProviderPackType.DILUTION`, `ProviderPackConfig.dilution`, required provider columns, and shared validation/path handling.

- [ ] **Step 2: Route the pack through existing orchestration**

Select dilution providers, normalize them to JSON, detect successful `DILUTION_SIGNAL` import, and expose `run_dilution_provider_pack`.

- [ ] **Step 3: Add the CLI command**

Add `run-dilution-provider-pack` using the same arguments and output contract as the existing news pack command.

### Task 3: Implement Conservative Dilution Signal Mapping

**Files:**
- Modify: `src/stock_risk_mcp/signal_normalizers.py`
- Modify: `src/stock_risk_mcp/data_import.py`

- [ ] **Step 1: Add rich-provider normalization**

When `dilution_risk` and `source_name` mappings are present, preserve the raw row, generate a title, and map:

```python
NONE -> ("LOW", 0)
LOW -> ("LOW", -1)
MEDIUM -> ("MEDIUM", -3)
HIGH -> ("HIGH", -7)
CRITICAL -> ("CRITICAL", -10)
UNKNOWN -> ("HIGH", -7)
```

- [ ] **Step 2: Preserve explicit provider scores during import**

For rich dilution records only, use normalized direction, severity, source, score, title, and raw payload. Keep the legacy path on `calculate_signal_score`.

- [ ] **Step 3: Run focused tests to verify GREEN**

Run:

```powershell
pytest -q tests/test_dilution_provider_pack.py tests/test_provider_pack_config.py tests/test_provider_packs.py tests/test_signal_normalizers.py tests/test_signal_scoring.py tests/test_signal_enrichment.py
```

Expected: all focused tests pass.

### Task 4: Document The Safety Boundary

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] **Step 1: Document usage and mapping**

Document the shared provider config, local/default-off network behavior, fixed non-positive dilution score mapping, and CLI example.

- [ ] **Step 2: Document future hard-risk bridge**

State that imported dilution signals affect Signal Enrichment only; they are not automatically converted to `CompanyRisk.dilution_risk`. Existing `block_dilution_high` and `block_unknown_dilution` rules remain unchanged, with the direct bridge reserved for future work.

### Task 5: Verify And Commit

**Files:**
- Modify: `WORK_SUMMARY.md`

- [ ] **Step 1: Run complete verification**

```powershell
pytest -q
python -m compileall -q src
git diff --check
python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs
```

Expected: all tests pass, compileall and diff check are clean, system smoke is COMPLETED with `external_network_calls=false`.

- [ ] **Step 2: Commit**

```powershell
git add src tests README.md WORK_SUMMARY.md docs/superpowers/plans/2026-06-14-dilution-provider-pack.md
git commit -m "Add dilution provider pack"
```
