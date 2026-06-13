from datetime import date, datetime

from stock_risk_mcp.mcp_bridge import ReadOnlyMCPBridge
from stock_risk_mcp.pipeline_run import PipelineMode, PipelineRun, PipelineRunStatus
from stock_risk_mcp.repository import RiskRepository


def test_mcp_bridge_exposes_read_only_repository_lookups(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    repository.save_pipeline_run(PipelineRun(
        pipeline_run_id="pipe-1", mode=PipelineMode.SCAN_ONLY, as_of_date=date(2026, 6, 13),
        status=PipelineRunStatus.COMPLETED, candidate_count=0, included_count=0, watch_count=0,
        basket_allocation_count=0, alert_count=0, created_at=datetime(2026, 6, 13),
    ))

    bridge = ReadOnlyMCPBridge(repository)

    assert bridge.get_pipeline_run("pipe-1")["pipeline_run_id"] == "pipe-1"
    assert all(item["read_only"] for item in bridge.agent_tools())
