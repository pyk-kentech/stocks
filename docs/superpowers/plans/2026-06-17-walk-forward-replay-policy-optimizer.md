# Walk-Forward Replay Policy Optimizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an offline deterministic walk-forward replay optimizer that reruns baseline and candidate policies on the same local replay fixture, compares per-window metrics, and emits advisory-only promotion decisions.

**Architecture:** Keep v3.7 split into strict fixture loading, deterministic timestamp window splitting, pure policy rerun logic, pure promotion gating, and a thin JSON-only service boundary. Reuse pure replay/paper-eval style behavior where appropriate, but keep all v3.7 core modules free of repository, broker, Kiwoom, account, order, credential, token, and network imports.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, existing `stock_risk_mcp` CLI and system-smoke framework

---

### Task 1: Fixture And Policy Models

**Files:**
- Create: `src/stock_risk_mcp/walk_forward_policy_models.py`
- Create: `src/stock_risk_mcp/walk_forward_policy_fixture.py`
- Test: `tests/test_walk_forward_policy_fixture.py`

- [ ] **Step 1: Write the failing fixture validation tests**

```python
def test_policy_replay_fixture_normalizes_tickers_and_policy_ids(tmp_path):
    fixture = load_walk_forward_policy_fixture(write(tmp_path, "policy_replay_fixture.json", fixture_payload()))
    assert fixture.replay_rows[0].ticker == "ABC"
    assert fixture.baseline_policy.policy_id == "baseline-v1"


def test_policy_replay_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_walk_forward_policy_fixture(write(tmp_path, "policy_replay_fixture.txt", fixture_payload()))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest -q tests/test_walk_forward_policy_fixture.py`
Expected: FAIL with `ModuleNotFoundError` for `stock_risk_mcp.walk_forward_policy_fixture`

- [ ] **Step 3: Write minimal fixture and policy models**

```python
class WalkForwardPolicyFixture(StrictModel):
    schema_version: str
    run_id: str
    created_at: datetime
    window_config: WalkForwardWindowConfig
    promotion_gates: PolicyPromotionGates
    baseline_policy: ReplayPolicyConfig
    candidate_policies: list[ReplayPolicyConfig]
    replay_rows: list[ReplayReplayRow]
    price_paths: list[ReplayPricePath]


def load_walk_forward_policy_fixture(path) -> WalkForwardPolicyFixture:
    selected = Path(path)
    if selected.suffix.lower() != ".json":
        raise ValueError("policy replay fixture must be an explicit local JSON file")
    return WalkForwardPolicyFixture.model_validate(json.loads(selected.read_text(encoding="utf-8")))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest -q tests/test_walk_forward_policy_fixture.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_walk_forward_policy_fixture.py src/stock_risk_mcp/walk_forward_policy_models.py src/stock_risk_mcp/walk_forward_policy_fixture.py
git commit -m "Add walk-forward policy fixture models"
```

### Task 2: Window Split And Promotion Gates

**Files:**
- Create: `src/stock_risk_mcp/walk_forward_window_split.py`
- Create: `src/stock_risk_mcp/walk_forward_promotion_gate.py`
- Test: `tests/test_walk_forward_window_split.py`
- Test: `tests/test_walk_forward_promotion_gate.py`

- [ ] **Step 1: Write the failing window and gate tests**

```python
def test_window_split_is_timestamp_ordered_and_walk_forward():
    windows = build_walk_forward_windows(fixture_payload())
    assert len(windows) == 2
    assert windows[0].train_start < windows[0].eval_start


def test_unsafe_policy_is_rejected_before_promotion():
    decision = build_promotion_decision(candidate_summary_unsafe(), gates())
    assert decision.status == "REJECT_UNSAFE_POLICY"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest -q tests/test_walk_forward_window_split.py tests/test_walk_forward_promotion_gate.py`
Expected: FAIL with `ModuleNotFoundError` for `stock_risk_mcp.walk_forward_window_split`

- [ ] **Step 3: Write minimal timestamp window splitter and gate evaluator**

```python
def build_walk_forward_windows(fixture: WalkForwardPolicyFixture) -> list[WalkForwardWindow]:
    # group replay rows by date, then slide train/eval windows by stride
    ...


def build_promotion_decision(comparison: CandidatePolicyComparison, gates: PolicyPromotionGates):
    # safety -> sample -> drawdown -> missing/blocked -> improvement -> stability
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest -q tests/test_walk_forward_window_split.py tests/test_walk_forward_promotion_gate.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_walk_forward_window_split.py tests/test_walk_forward_promotion_gate.py src/stock_risk_mcp/walk_forward_window_split.py src/stock_risk_mcp/walk_forward_promotion_gate.py
git commit -m "Add walk-forward windows and promotion gates"
```

### Task 3: Deterministic Policy Rerun Engine

**Files:**
- Create: `src/stock_risk_mcp/walk_forward_policy_engine.py`
- Test: `tests/test_walk_forward_policy_engine.py`

- [ ] **Step 1: Write the failing replay and comparison tests**

```python
def test_baseline_and_candidate_are_rerun_on_same_replay_fixture():
    report = build_walk_forward_policy_report(fixture(), "checksum")
    assert report.window_results[0].baseline.window_trade_count == report.window_results[0].candidate_results[0].window_trade_count


def test_candidate_can_be_promoted_demoted_or_kept_by_metrics():
    report = build_walk_forward_policy_report(fixture(), "checksum")
    assert report.candidate_comparisons[0].promotion_decision in {
        "PROMOTE_CANDIDATE_POLICY", "KEEP_BASELINE_POLICY", "DEMOTE_CANDIDATE_POLICY"
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest -q tests/test_walk_forward_policy_engine.py`
Expected: FAIL with `ModuleNotFoundError` for `stock_risk_mcp.walk_forward_policy_engine`

- [ ] **Step 3: Write minimal pure rerun engine**

```python
def build_walk_forward_policy_report(fixture: WalkForwardPolicyFixture, fixture_checksum: str) -> WalkForwardPolicyReport:
    windows = build_walk_forward_windows(fixture)
    # filter replay rows by policy, simulate deterministic trade outcomes on the linked price paths,
    # compute per-window metrics, aggregate candidate vs baseline deltas, then gate decisions
    return WalkForwardPolicyReport(...)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest -q tests/test_walk_forward_policy_engine.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_walk_forward_policy_engine.py src/stock_risk_mcp/walk_forward_policy_engine.py
git commit -m "Add walk-forward policy rerun engine"
```

### Task 4: Service And CLI

**Files:**
- Create: `src/stock_risk_mcp/walk_forward_policy_service.py`
- Modify: `src/stock_risk_mcp/cli.py`
- Test: `tests/test_walk_forward_policy_service.py`
- Test: `tests/test_walk_forward_policy_cli.py`

- [ ] **Step 1: Write the failing service and CLI tests**

```python
def test_policy_replay_service_writes_optional_json_output_only(tmp_path):
    report = run_walk_forward_policy_replay(fixture_file, output_file=output_file)
    assert output_file.exists()
    assert report.metadata_json["external_network_calls"] is False


def test_policy_replay_run_and_show_commands(tmp_path, capsys):
    summary = run(capsys, ["policy-replay-run", "--fixture-file", str(fixture_file), "--output-file", str(output_file)])
    shown = run(capsys, ["policy-replay-show", "--output-file", str(output_file)])
    assert summary["status"] == "COMPLETED"
    assert shown["metadata_json"]["production_policy_changed"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest -q tests/test_walk_forward_policy_service.py tests/test_walk_forward_policy_cli.py`
Expected: FAIL with `ModuleNotFoundError` for `stock_risk_mcp.walk_forward_policy_service`

- [ ] **Step 3: Write minimal JSON-only service and CLI wiring**

```python
def run_walk_forward_policy_replay(fixture_file, output_file=None):
    fixture = load_walk_forward_policy_fixture(fixture_file)
    report = build_walk_forward_policy_report(fixture, _checksum(fixture_file))
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest -q tests/test_walk_forward_policy_service.py tests/test_walk_forward_policy_cli.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_walk_forward_policy_service.py tests/test_walk_forward_policy_cli.py src/stock_risk_mcp/walk_forward_policy_service.py src/stock_risk_mcp/cli.py
git commit -m "Add policy replay CLI"
```

### Task 5: Safety And System Smoke

**Files:**
- Modify: `src/stock_risk_mcp/system_smoke.py`
- Test: `tests/test_walk_forward_policy_safety.py`
- Test: `tests/test_system_smoke.py`

- [ ] **Step 1: Write the failing safety and smoke tests**

```python
def test_walk_forward_policy_core_has_no_forbidden_imports_or_artifact_creation():
    files = (
        "walk_forward_policy_models.py",
        "walk_forward_policy_fixture.py",
        "walk_forward_window_split.py",
        "walk_forward_policy_engine.py",
        "walk_forward_promotion_gate.py",
    )
    ...


def test_system_smoke_validates_local_workflow(tmp_path):
    result = run_system_smoke(tmp_path / "smoke.sqlite3", tmp_path / "outputs")
    assert result["checks"]["policy_replay_fixture_run"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest -q tests/test_walk_forward_policy_safety.py tests/test_system_smoke.py`
Expected: FAIL because `policy_replay_fixture_run` is missing

- [ ] **Step 3: Extend smoke with temporary local policy-replay fixture**

```python
policy_replay_fixture = Path(output_dir) / "policy_replay_smoke_fixture.json"
policy_replay_fixture.write_text(json.dumps({...}), encoding="utf-8")
policy_replay = run_walk_forward_policy_replay(policy_replay_fixture)
checks["policy_replay_fixture_run"] = bool(policy_replay.candidate_comparisons)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest -q tests/test_walk_forward_policy_safety.py tests/test_system_smoke.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_walk_forward_policy_safety.py tests/test_system_smoke.py src/stock_risk_mcp/system_smoke.py
git commit -m "Add policy replay smoke coverage"
```

### Task 6: Full Verification And Release Commit

**Files:**
- Modify: `src/stock_risk_mcp/walk_forward_policy_models.py`
- Modify: `src/stock_risk_mcp/walk_forward_policy_fixture.py`
- Modify: `src/stock_risk_mcp/walk_forward_window_split.py`
- Modify: `src/stock_risk_mcp/walk_forward_policy_engine.py`
- Modify: `src/stock_risk_mcp/walk_forward_promotion_gate.py`
- Modify: `src/stock_risk_mcp/walk_forward_policy_service.py`
- Modify: `src/stock_risk_mcp/cli.py`
- Modify: `src/stock_risk_mcp/system_smoke.py`
- Modify: `tests/test_walk_forward_policy_fixture.py`
- Modify: `tests/test_walk_forward_window_split.py`
- Modify: `tests/test_walk_forward_policy_engine.py`
- Modify: `tests/test_walk_forward_policy_service.py`
- Modify: `tests/test_walk_forward_policy_cli.py`
- Modify: `tests/test_walk_forward_policy_safety.py`
- Modify: `tests/test_system_smoke.py`

- [ ] **Step 1: Run the focused new test suite**

Run: `python3.11 -m pytest -q tests/test_walk_forward_policy_fixture.py tests/test_walk_forward_window_split.py tests/test_walk_forward_policy_engine.py tests/test_walk_forward_policy_service.py tests/test_walk_forward_policy_cli.py tests/test_walk_forward_policy_safety.py tests/test_system_smoke.py`
Expected: PASS

- [ ] **Step 2: Run the full repository test suite**

Run: `python3.11 -m pytest -q`
Expected: PASS with all existing v2-v3.6 tests preserved

- [ ] **Step 3: Run compile and diff checks**

Run: `python3.11 -m compileall -q src`
Expected: PASS

Run: `git diff --check`
Expected: no output

- [ ] **Step 4: Run system smoke**

Run: `python3.11 -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`
Expected: JSON with `"policy_replay_fixture_run": true` and `"external_network_calls": false`

- [ ] **Step 5: Create the implementation commit**

```bash
git add .
git commit -m "Add walk-forward replay policy optimizer"
```
