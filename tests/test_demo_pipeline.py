from datetime import date

from stock_risk_mcp.demo_pipeline import DemoRunStatus, DemoStepName, DemoStepStatus, run_local_demo


def test_run_local_demo_completes_deterministic_workflow(tmp_path) -> None:
    output_dir = tmp_path / "outputs"

    result = run_local_demo(tmp_path / "demo.sqlite3", date(2026, 6, 13), output_dir)

    names = {item.step_name for item in result.step_results}
    assert result.status in {DemoRunStatus.COMPLETED, DemoRunStatus.PARTIAL}
    assert {
        DemoStepName.CONNECTORS, DemoStepName.IMPORT, DemoStepName.PAPER_PIPELINE,
        DemoStepName.ANALYSIS_REPORT, DemoStepName.NOTIFICATION, DemoStepName.DASHBOARD,
    } <= names
    assert (output_dir / "demo_summary.json").exists()
    assert (output_dir / "notification.md").exists()
    assert (output_dir / "dashboard.html").exists()
    assert result.key_outputs["pipeline_run_id"]


def test_import_failure_skips_dependent_demo_steps(tmp_path) -> None:
    result = run_local_demo(
        tmp_path / "demo.sqlite3", date(2026, 6, 13), tmp_path / "outputs",
        connector_names=[],
    )

    steps = {item.step_name: item for item in result.step_results}
    assert result.status == DemoRunStatus.FAILED
    assert steps[DemoStepName.IMPORT].status == DemoStepStatus.FAILED
    assert steps[DemoStepName.PAPER_PIPELINE].status == DemoStepStatus.SKIPPED
    assert steps[DemoStepName.ANALYSIS_REPORT].status == DemoStepStatus.SKIPPED


def test_local_demo_does_not_call_external_llm_transport(tmp_path, monkeypatch) -> None:
    def blocked_network(*args, **kwargs):
        raise AssertionError("network transport must not be called")

    monkeypatch.setattr("stock_risk_mcp.local_llm_client.urlopen", blocked_network)

    result = run_local_demo(tmp_path / "demo.sqlite3", date(2026, 6, 13), tmp_path / "outputs")

    dry_run = next(item for item in result.step_results if item.step_name == DemoStepName.LOCAL_LLM_DRY_RUN)
    assert dry_run.status == DemoStepStatus.COMPLETED
    assert dry_run.metrics["network_access"] is False
