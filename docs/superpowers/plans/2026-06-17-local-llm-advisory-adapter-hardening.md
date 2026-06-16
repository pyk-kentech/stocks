# Local LLM Advisory Adapter Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a hardened local LLM advisory adapter that consumes one explicit local JSON fixture, defaults to a disabled backend, validates safety strictly, and emits advisory-only responses or safe refusals.

**Architecture:** Keep v3.8 split into strict fixture loading, pure advisory models, pure safety guard logic, a pure deterministic advisory engine, and a thin JSON-only service boundary. Do not reuse the existing network-capable `local_llm_client` path in the v3.8 core.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, existing `stock_risk_mcp` CLI and system-smoke framework

---

### Task 1: Fixture And Advisory Models

**Files:**
- Create: `src/stock_risk_mcp/local_llm_advisory_models.py`
- Create: `src/stock_risk_mcp/local_llm_advisory_fixture.py`
- Test: `tests/test_local_llm_advisory_fixture.py`

- [ ] **Step 1: Write the failing fixture validation tests**

```python
def test_local_llm_advisory_fixture_normalizes_tickers_and_enforces_flags(tmp_path):
    fixture = load_local_llm_advisory_fixture(write(tmp_path, "local_llm_advisory_fixture.json", fixture_payload()))
    assert fixture.inputs.ticker == "ABC"
    assert fixture.safety.advisory_only is True


def test_local_llm_advisory_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_local_llm_advisory_fixture(write(tmp_path, "local_llm_advisory_fixture.txt", fixture_payload()))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest -q tests/test_local_llm_advisory_fixture.py`
Expected: FAIL with `ModuleNotFoundError` for `stock_risk_mcp.local_llm_advisory_fixture`

- [ ] **Step 3: Write minimal advisory models and loader**

```python
class LocalLLMAdvisoryFixture(StrictModel):
    schema_version: str
    run_id: str
    created_at: datetime
    task_type: AdvisoryTaskType
    backend: LocalLLMAdvisoryBackendConfig
    prompt_metadata: LocalLLMAdvisoryPromptMetadata
    inputs: LocalLLMAdvisoryInputs
    safety: LocalLLMAdvisorySafetyFlags


def load_local_llm_advisory_fixture(path) -> LocalLLMAdvisoryFixture:
    selected = Path(path)
    if selected.suffix.lower() != ".json":
        raise ValueError("local LLM advisory fixture must be an explicit local JSON file")
    return LocalLLMAdvisoryFixture.model_validate(json.loads(selected.read_text(encoding="utf-8")))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest -q tests/test_local_llm_advisory_fixture.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_local_llm_advisory_fixture.py src/stock_risk_mcp/local_llm_advisory_models.py src/stock_risk_mcp/local_llm_advisory_fixture.py
git commit -m "Add local LLM advisory fixture models"
```

### Task 2: Guard And Engine

**Files:**
- Create: `src/stock_risk_mcp/local_llm_advisory_guard.py`
- Create: `src/stock_risk_mcp/local_llm_advisory_engine.py`
- Test: `tests/test_local_llm_advisory_engine.py`

- [ ] **Step 1: Write the failing advisory and fail-closed tests**

```python
def test_disabled_backend_returns_safe_refusal():
    result = run_local_llm_advisory_fixture(fixture())
    assert result.status == "BACKEND_DISABLED"
    assert result.metadata_json["advisory_only"] is True


def test_unsafe_output_is_rejected_fail_closed():
    result = run_local_llm_advisory_fixture(fixture_with_text("Buy now and place an order"))
    assert result.status == "UNSAFE_OUTPUT_REJECTED"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest -q tests/test_local_llm_advisory_engine.py`
Expected: FAIL with `ModuleNotFoundError` for `stock_risk_mcp.local_llm_advisory_engine`

- [ ] **Step 3: Write minimal pure guard and advisory engine**

```python
def run_local_llm_advisory_fixture(fixture: LocalLLMAdvisoryFixture) -> LocalLLMAdvisoryResult:
    if fixture.backend.backend_type == LocalLLMAdvisoryBackend.DISABLED:
        return safe_refusal(fixture, "local advisory backend disabled")
    content = build_fixture_derived_advisory_text(fixture)
    if unsafe := detect_unsafe_output(content):
        return unsafe_rejection(fixture, unsafe)
    return advisory_response(fixture, content)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest -q tests/test_local_llm_advisory_engine.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_local_llm_advisory_engine.py src/stock_risk_mcp/local_llm_advisory_guard.py src/stock_risk_mcp/local_llm_advisory_engine.py
git commit -m "Add local LLM advisory guard and engine"
```

### Task 3: Service And CLI

**Files:**
- Create: `src/stock_risk_mcp/local_llm_advisory_service.py`
- Modify: `src/stock_risk_mcp/cli.py`
- Test: `tests/test_local_llm_advisory_service.py`
- Test: `tests/test_local_llm_advisory_cli.py`

- [ ] **Step 1: Write the failing service and CLI tests**

```python
def test_local_llm_advisory_service_writes_optional_json_output_only(tmp_path):
    result = run_local_llm_advisory(fixture_file, output_file=output_file)
    assert output_file.exists()
    assert result.metadata_json["external_network_calls"] is False


def test_local_llm_advisory_run_and_show_commands(tmp_path, capsys):
    summary = run(capsys, ["local-llm-advisory-run", "--fixture-file", str(fixture_file), "--output-file", str(output_file)])
    shown = run(capsys, ["local-llm-advisory-show", "--output-file", str(output_file)])
    assert summary["status"] == "COMPLETED"
    assert shown["metadata_json"]["may_create_order"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest -q tests/test_local_llm_advisory_service.py tests/test_local_llm_advisory_cli.py`
Expected: FAIL with `ModuleNotFoundError` for `stock_risk_mcp.local_llm_advisory_service`

- [ ] **Step 3: Write minimal JSON-only service and CLI wiring**

```python
def run_local_llm_advisory(fixture_file, output_file=None):
    fixture = load_local_llm_advisory_fixture(fixture_file)
    result = run_local_llm_advisory_fixture(fixture, _checksum(fixture_file))
    if output_file:
        Path(output_file).write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest -q tests/test_local_llm_advisory_service.py tests/test_local_llm_advisory_cli.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_local_llm_advisory_service.py tests/test_local_llm_advisory_cli.py src/stock_risk_mcp/local_llm_advisory_service.py src/stock_risk_mcp/cli.py
git commit -m "Add local LLM advisory CLI"
```

### Task 4: Safety And System Smoke

**Files:**
- Modify: `src/stock_risk_mcp/system_smoke.py`
- Test: `tests/test_local_llm_advisory_safety.py`
- Test: `tests/test_system_smoke.py`

- [ ] **Step 1: Write the failing safety and smoke tests**

```python
def test_local_llm_advisory_core_has_no_forbidden_imports_or_artifact_creation():
    files = (
        "local_llm_advisory_models.py",
        "local_llm_advisory_fixture.py",
        "local_llm_advisory_guard.py",
        "local_llm_advisory_engine.py",
    )
    ...


def test_system_smoke_validates_local_workflow(tmp_path):
    result = run_system_smoke(tmp_path / "smoke.sqlite3", tmp_path / "outputs")
    assert result["checks"]["llm_advisory_fixture_run"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest -q tests/test_local_llm_advisory_safety.py tests/test_system_smoke.py`
Expected: FAIL because `llm_advisory_fixture_run` is missing

- [ ] **Step 3: Extend smoke with temporary disabled-backend advisory fixture**

```python
llm_advisory_fixture = Path(output_dir) / "local_llm_advisory_smoke_fixture.json"
llm_advisory_fixture.write_text(json.dumps({...}), encoding="utf-8")
llm_advisory = run_local_llm_advisory(llm_advisory_fixture)
checks["llm_advisory_fixture_run"] = llm_advisory.metadata_json["external_network_calls"] is False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest -q tests/test_local_llm_advisory_safety.py tests/test_system_smoke.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_local_llm_advisory_safety.py tests/test_system_smoke.py src/stock_risk_mcp/system_smoke.py
git commit -m "Add local LLM advisory smoke coverage"
```

### Task 5: Full Verification And Release Commit

**Files:**
- Modify: `src/stock_risk_mcp/local_llm_advisory_models.py`
- Modify: `src/stock_risk_mcp/local_llm_advisory_fixture.py`
- Modify: `src/stock_risk_mcp/local_llm_advisory_guard.py`
- Modify: `src/stock_risk_mcp/local_llm_advisory_engine.py`
- Modify: `src/stock_risk_mcp/local_llm_advisory_service.py`
- Modify: `src/stock_risk_mcp/cli.py`
- Modify: `src/stock_risk_mcp/system_smoke.py`
- Modify: `tests/test_local_llm_advisory_fixture.py`
- Modify: `tests/test_local_llm_advisory_engine.py`
- Modify: `tests/test_local_llm_advisory_service.py`
- Modify: `tests/test_local_llm_advisory_cli.py`
- Modify: `tests/test_local_llm_advisory_safety.py`
- Modify: `tests/test_system_smoke.py`

- [ ] **Step 1: Run the focused new test suite**

Run: `python3.11 -m pytest -q tests/test_local_llm_advisory_fixture.py tests/test_local_llm_advisory_engine.py tests/test_local_llm_advisory_service.py tests/test_local_llm_advisory_cli.py tests/test_local_llm_advisory_safety.py tests/test_system_smoke.py`
Expected: PASS

- [ ] **Step 2: Run the full repository test suite**

Run: `python3.11 -m pytest -q`
Expected: PASS with all existing v2-v3.7 tests preserved

- [ ] **Step 3: Run compile and diff checks**

Run: `python3.11 -m compileall -q src`
Expected: PASS

Run: `git diff --check`
Expected: no output

- [ ] **Step 4: Run system smoke**

Run: `python3.11 -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`
Expected: JSON with `"llm_advisory_fixture_run": true` and `"external_network_calls": false`

- [ ] **Step 5: Create the implementation commit**

```bash
git add .
git commit -m "Add local LLM advisory adapter hardening"
```
