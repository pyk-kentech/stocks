# Flow Provider Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe Flow Provider Pack that imports deterministic sign-based foreign and institution flow signals without changing common scoring or hard-risk behavior.

**Architecture:** Extend the shared Provider Pack routing with a `flow` group and FLOW pack type. Rich mode in `GenericFlowCSVNormalizer` selects amount or shares at provider-config scope, writes explicit `provider_record_mode=RICH_FLOW_PROVIDER`, and emits conservative LOW/MEDIUM scores. Unified Import preserves explicit rich flow values only when the FLOW source, internal mode marker, and rich fields identify the record.

**Tech Stack:** Python, Pydantic, SQLite repository, argparse CLI, pytest

---

### Task 1: Lock Flow Provider Contracts With Failing Tests

**Files:**
- Create: `tests/test_flow_provider_pack.py`
- Modify: `tests/test_provider_pack_config.py`
- Modify: `tests/test_provider_packs.py`
- Modify: `tests/test_signal_normalizers.py`

- [ ] **Step 1: Add provider config and pack-type tests**

Test `flow.providers`, `ProviderPackType.FLOW`, base required columns, and the requirement for at least one foreign/institution amount or shares mapping.

- [ ] **Step 2: Add sign mapping and selection tests**

Test both positive, one positive, both negative, one negative, opposite signs, both zero/missing, amount precedence, and shares fallback.

- [ ] **Step 3: Add rich-record discrimination tests**

Test that rich normalized records include `provider_record_mode=RICH_FLOW_PROVIDER`, and a legacy flow record containing only `score_delta` does not enter the rich provider import path.

- [ ] **Step 4: Add pack integration and safety tests**

Test local file, fake HTTP, default-off HTTP, missing normalizer, raw payload, imported signal type, no HIGH/CRITICAL generation, positive-flow EXCLUDE protection, CLI, list, and show.

- [ ] **Step 5: Verify RED**

Run:

```powershell
pytest -q tests/test_flow_provider_pack.py tests/test_provider_pack_config.py tests/test_provider_packs.py tests/test_signal_normalizers.py
```

Expected: failures because FLOW provider routing and rich flow mode do not exist.

### Task 2: Add Flow Provider Pack Routing

**Files:**
- Create: `src/stock_risk_mcp/flow_provider_pack.py`
- Modify: `src/stock_risk_mcp/provider_config.py`
- Modify: `src/stock_risk_mcp/http_connector.py`
- Modify: `src/stock_risk_mcp/provider_pack_config.py`
- Modify: `src/stock_risk_mcp/provider_packs.py`
- Modify: `src/stock_risk_mcp/provider_pack_pipeline.py`
- Modify: `src/stock_risk_mcp/cli.py`

- [ ] **Step 1: Add Flow enums and config group**

Add `ProviderDataKind.FOREIGN_INSTITUTION_FLOW`, `ProviderPackType.FLOW`, and `ProviderPackConfig.flow`.

- [ ] **Step 2: Validate Flow mappings**

Require `ticker`, `observed_at`, and `source_name`, plus at least one of:

```python
{
    "foreign_net_buy_amount",
    "institution_net_buy_amount",
    "foreign_net_buy_shares",
    "institution_net_buy_shares",
}
```

- [ ] **Step 3: Route raw-to-normalized-to-import execution**

Select Flow providers, write rich Flow normalized output as JSON, detect successful `FLOW_SIGNAL` import, and expose `run_flow_provider_pack`.

- [ ] **Step 4: Add CLI**

Add `run-flow-provider-pack` with the same safe options and JSON result shape as other Provider Packs.

### Task 3: Implement Rich Flow Normalization And Import

**Files:**
- Modify: `src/stock_risk_mcp/signal_normalizers.py`
- Modify: `src/stock_risk_mcp/data_import.py`

- [ ] **Step 1: Implement provider-config-scope value selection**

Use amount fields when either amount mapping exists. Use shares only when neither amount mapping exists. Treat missing selected row values as zero and do not perform row-level fallback.

- [ ] **Step 2: Implement deterministic mapping**

Return only:

```python
("POSITIVE", "LOW", 2)
("POSITIVE", "LOW", 1)
("NEGATIVE", "MEDIUM", -3)
("NEGATIVE", "LOW", -1)
("NEUTRAL", "LOW", 0)
```

- [ ] **Step 3: Emit explicit rich Flow metadata**

Set `provider_record_mode="RICH_FLOW_PROVIDER"`, preserve the raw row, generate a title when absent, and retain optional provider fields.

- [ ] **Step 4: Preserve rich Flow values during import**

Recognize rich Flow records only when:

```python
source_type == ImportSourceType.FLOW_SIGNAL
and record["provider_record_mode"] == "RICH_FLOW_PROVIDER"
and at least one rich flow field exists
```

Do not use `score_delta` as the sole discriminator. Leave legacy Flow and common scoring unchanged.

- [ ] **Step 5: Verify GREEN**

Run:

```powershell
pytest -q tests/test_flow_provider_pack.py tests/test_provider_pack_config.py tests/test_provider_packs.py tests/test_provider_pack_pipeline.py tests/test_signal_normalizers.py tests/test_signal_scoring.py tests/test_signal_enrichment.py
```

Expected: all focused tests pass.

### Task 4: Document Flow Safety Boundaries

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] **Step 1: Document config, CLI, and deterministic mapping**

Document `flow.providers`, provider-entry-only normalizer/columns, amount precedence, shares fallback, and `run-flow-provider-pack`.

- [ ] **Step 2: Document safety limits**

State that Flow is a ranking/watching aid, creates no default HIGH/CRITICAL signals, cannot promote EXCLUDE or blocked candidates, does not change common scoring or hard-risk rules, and performs no real orders or automatic trading.

### Task 5: Verify And Commit

**Files:**
- Modify: `WORK_SUMMARY.md`

- [ ] **Step 1: Run full release verification**

```powershell
pytest -q
python -m compileall -q src
git diff --check
python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs
```

Expected: all tests pass, compileall and diff check pass, and smoke is `COMPLETED` with `external_network_calls=false`.

- [ ] **Step 2: Commit**

```powershell
git add src tests README.md WORK_SUMMARY.md docs/superpowers/specs/2026-06-14-flow-provider-pack-design.md docs/superpowers/plans/2026-06-14-flow-provider-pack.md
git commit -m "Add flow provider pack"
```
