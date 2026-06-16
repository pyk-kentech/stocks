# Paper Trading Strategy Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an offline deterministic paper-only strategy evaluation layer that consumes one explicit local JSON fixture, simulates OHLC rule-based paper trades, and produces a JSON report with equity, drawdown, and trade metrics.

**Architecture:** Keep v3.6 split into strict fixture loading, pure OHLC fill logic, pure paper evaluation logic, and a thin JSON-only service boundary. Reuse existing CLI and system-smoke patterns, but keep all core paper evaluation modules free of repository, broker, Kiwoom, account, order, credential, and network imports.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, existing `stock_risk_mcp` CLI and system-smoke framework

---

### Task 1: Fixture And Model Contract

**Files:**
- Create: `src/stock_risk_mcp/paper_eval_models.py`
- Create: `src/stock_risk_mcp/paper_eval_fixture.py`
- Test: `tests/test_paper_eval_fixture.py`

- [ ] **Step 1: Write the failing fixture validation tests**

```python
def test_paper_eval_fixture_normalizes_tickers_and_validates_ohlc(tmp_path):
    fixture = load_paper_eval_fixture(write(tmp_path, "paper_eval_fixture.json", fixture_payload()))
    assert fixture.inputs[0].ticker == "ABC"
    assert fixture.price_paths[0].ticker == "ABC"


def test_paper_eval_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_paper_eval_fixture(write(tmp_path, "paper_eval_fixture.txt", fixture_payload()))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest -q tests/test_paper_eval_fixture.py`
Expected: FAIL with `ModuleNotFoundError` for `stock_risk_mcp.paper_eval_fixture`

- [ ] **Step 3: Write minimal fixture models and loader**

```python
class PaperEvalFixture(StrictModel):
    schema_version: str
    run_id: str
    created_at: datetime
    config: PaperEvalConfig
    inputs: list[PaperEvalInput]
    price_paths: list[PaperPricePath]


def load_paper_eval_fixture(path) -> PaperEvalFixture:
    selected = Path(path)
    if selected.suffix.lower() != ".json":
        raise ValueError("paper evaluation fixture must be an explicit local JSON file")
    return PaperEvalFixture.model_validate(json.loads(selected.read_text(encoding="utf-8")))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest -q tests/test_paper_eval_fixture.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_paper_eval_fixture.py src/stock_risk_mcp/paper_eval_models.py src/stock_risk_mcp/paper_eval_fixture.py
git commit -m "Add paper evaluation fixture models"
```

### Task 2: Deterministic OHLC Fill Engine

**Files:**
- Create: `src/stock_risk_mcp/paper_fill_engine.py`
- Test: `tests/test_paper_fill_engine.py`

- [ ] **Step 1: Write the failing fill-policy tests**

```python
def test_buy_entry_fills_when_low_to_high_contains_entry():
    result = simulate_bar_fill(open_position=None, candidate=input_row(), bar=bar(low=99, high=101))
    assert result.entry_filled is True
    assert result.fill_price == 100


def test_same_bar_stop_and_target_conflict_uses_stop_first():
    position = entered_position()
    result = evaluate_exit(position, bar(low=95, high=109))
    assert result.exit_reason == "STOP_HIT"
    assert result.exit_price == 96
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest -q tests/test_paper_fill_engine.py`
Expected: FAIL with `ModuleNotFoundError` for `stock_risk_mcp.paper_fill_engine`

- [ ] **Step 3: Write minimal pure OHLC fill logic**

```python
def should_fill_long_entry(entry_price: float, bar: PaperPriceBar) -> bool:
    return bar.low <= entry_price <= bar.high


def evaluate_long_exit(position: PaperPosition, bar: PaperPriceBar) -> tuple[str, float] | None:
    stop_hit = bar.low <= position.stop_price
    target_hit = bar.high >= position.target_price
    if stop_hit and target_hit:
        return ("STOP_HIT", position.stop_price)
    if stop_hit:
        return ("STOP_HIT", position.stop_price)
    if target_hit:
        return ("TARGET_HIT", position.target_price)
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest -q tests/test_paper_fill_engine.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_paper_fill_engine.py src/stock_risk_mcp/paper_fill_engine.py
git commit -m "Add deterministic paper fill engine"
```

### Task 3: Paper Evaluation Engine

**Files:**
- Create: `src/stock_risk_mcp/paper_eval_engine.py`
- Test: `tests/test_paper_eval_engine.py`

- [ ] **Step 1: Write the failing paper lifecycle tests**

```python
def test_forced_end_of_fixture_closes_open_position():
    report = build_paper_eval_report(fixture_with_open_position(), "checksum")
    trade = report.paper_trades[0]
    assert trade.exit_reason == "FORCED_END_OF_FIXTURE"
    assert trade.simulated_exit_price == 107


def test_insufficient_cash_blocks_candidate():
    report = build_paper_eval_report(fixture_with_large_quantity(), "checksum")
    assert report.metrics.blocked_plan_count == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest -q tests/test_paper_eval_engine.py`
Expected: FAIL with `ModuleNotFoundError` for `stock_risk_mcp.paper_eval_engine`

- [ ] **Step 3: Write minimal portfolio, trade, and metrics engine**

```python
def build_paper_eval_report(fixture: PaperEvalFixture, fixture_checksum: str) -> PaperEvalReport:
    state = PaperPortfolioState(cash_available=fixture.config.initial_cash, equity=fixture.config.initial_cash)
    # normalize inputs, simulate fills, enforce cash checks, update equity curve,
    # force-close remaining positions at final close, then compute metrics
    return PaperEvalReport(...)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest -q tests/test_paper_eval_engine.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_paper_eval_engine.py src/stock_risk_mcp/paper_eval_engine.py
git commit -m "Add paper evaluation engine"
```

### Task 4: Service And CLI

**Files:**
- Create: `src/stock_risk_mcp/paper_eval_service.py`
- Modify: `src/stock_risk_mcp/cli.py`
- Test: `tests/test_paper_eval_service.py`
- Test: `tests/test_paper_eval_cli.py`

- [ ] **Step 1: Write the failing service and CLI tests**

```python
def test_paper_eval_service_writes_optional_json_output_only(tmp_path):
    report = run_paper_eval(fixture_file, output_file=output_file)
    assert output_file.exists()
    assert report.metadata_json["external_network_calls"] is False


def test_paper_eval_run_and_show_commands(tmp_path, capsys):
    summary = run(capsys, ["paper-eval-run", "--fixture-file", str(fixture_file), "--output-file", str(output_file)])
    shown = run(capsys, ["paper-eval-show", "--output-file", str(output_file)])
    assert summary["status"] == "COMPLETED"
    assert shown["metadata_json"]["paper_only"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest -q tests/test_paper_eval_service.py tests/test_paper_eval_cli.py`
Expected: FAIL with `ModuleNotFoundError` for `stock_risk_mcp.paper_eval_service`

- [ ] **Step 3: Write minimal JSON-only service and CLI wiring**

```python
def run_paper_eval(fixture_file, output_file=None):
    fixture = load_paper_eval_fixture(fixture_file)
    report = build_paper_eval_report(fixture, _checksum(fixture_file))
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest -q tests/test_paper_eval_service.py tests/test_paper_eval_cli.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_paper_eval_service.py tests/test_paper_eval_cli.py src/stock_risk_mcp/paper_eval_service.py src/stock_risk_mcp/cli.py
git commit -m "Add paper evaluation CLI"
```

### Task 5: Safety And System Smoke

**Files:**
- Modify: `src/stock_risk_mcp/system_smoke.py`
- Test: `tests/test_paper_eval_safety.py`
- Test: `tests/test_system_smoke.py`

- [ ] **Step 1: Write the failing safety and smoke tests**

```python
def test_paper_eval_core_has_no_forbidden_imports_or_artifact_creation():
    files = ("paper_eval_models.py", "paper_eval_fixture.py", "paper_fill_engine.py", "paper_eval_engine.py")
    forbidden = ("database", "repository", "provider", "realtime", "broker", "kiwoom", "account", "order", "network")
    ...


def test_system_smoke_validates_local_workflow(tmp_path):
    result = run_system_smoke(tmp_path / "smoke.sqlite3", tmp_path / "outputs")
    assert result["checks"]["paper_eval_fixture_run"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest -q tests/test_paper_eval_safety.py tests/test_system_smoke.py`
Expected: FAIL because `paper_eval_fixture_run` is missing

- [ ] **Step 3: Extend smoke with temporary local paper-eval fixture**

```python
paper_eval_fixture = Path(output_dir) / "paper_eval_smoke_fixture.json"
paper_eval_fixture.write_text(json.dumps({...}), encoding="utf-8")
paper_eval = run_paper_eval(paper_eval_fixture)
checks["paper_eval_fixture_run"] = len(paper_eval.paper_trades) == 1
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest -q tests/test_paper_eval_safety.py tests/test_system_smoke.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_paper_eval_safety.py tests/test_system_smoke.py src/stock_risk_mcp/system_smoke.py
git commit -m "Add paper evaluation smoke coverage"
```

### Task 6: Full Verification And Release Commit

**Files:**
- Modify: `src/stock_risk_mcp/paper_eval_models.py`
- Modify: `src/stock_risk_mcp/paper_eval_fixture.py`
- Modify: `src/stock_risk_mcp/paper_fill_engine.py`
- Modify: `src/stock_risk_mcp/paper_eval_engine.py`
- Modify: `src/stock_risk_mcp/paper_eval_service.py`
- Modify: `src/stock_risk_mcp/cli.py`
- Modify: `src/stock_risk_mcp/system_smoke.py`
- Modify: `tests/test_paper_eval_fixture.py`
- Modify: `tests/test_paper_fill_engine.py`
- Modify: `tests/test_paper_eval_engine.py`
- Modify: `tests/test_paper_eval_service.py`
- Modify: `tests/test_paper_eval_cli.py`
- Modify: `tests/test_paper_eval_safety.py`
- Modify: `tests/test_system_smoke.py`

- [ ] **Step 1: Run the focused new test suite**

Run: `python3.11 -m pytest -q tests/test_paper_eval_fixture.py tests/test_paper_fill_engine.py tests/test_paper_eval_engine.py tests/test_paper_eval_service.py tests/test_paper_eval_cli.py tests/test_paper_eval_safety.py tests/test_system_smoke.py`
Expected: PASS

- [ ] **Step 2: Run the full repository test suite**

Run: `python3.11 -m pytest -q`
Expected: PASS with all existing v2-v3.5 tests preserved

- [ ] **Step 3: Run compile and diff checks**

Run: `python3.11 -m compileall -q src`
Expected: PASS

Run: `git diff --check`
Expected: no output

- [ ] **Step 4: Run system smoke**

Run: `python3.11 -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`
Expected: JSON with `"paper_eval_fixture_run": true` and `"external_network_calls": false`

- [ ] **Step 5: Create the implementation commit**

```bash
git add .
git commit -m "Add paper trading strategy evaluation"
```
