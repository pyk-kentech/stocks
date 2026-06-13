from datetime import date, datetime

from stock_risk_mcp.demo_pipeline import DemoRunResult, DemoRunStatus, DemoStepName, DemoStepResult, DemoStepStatus
from stock_risk_mcp.demo_report import write_demo_summary


def test_demo_summary_json_is_written_with_disclaimer(tmp_path) -> None:
    result = DemoRunResult(
        demo_run_id="demo-1", status=DemoRunStatus.COMPLETED, as_of_date=date(2026, 6, 13),
        db_path="demo.sqlite3", output_dir=str(tmp_path),
        step_results=[DemoStepResult(step_name=DemoStepName.SUMMARY, status=DemoStepStatus.COMPLETED)],
        created_at=datetime(2026, 6, 13),
    )

    path = write_demo_summary(result, tmp_path / "demo_summary.json")

    text = path.read_text(encoding="utf-8")
    assert '"demo_run_id": "demo-1"' in text
    assert "system smoke/release validation" in text
    assert "not investment advice" in text
