from datetime import date, datetime

from stock_risk_mcp.dashboard_models import DashboardBuildResult, DashboardBuildStatus, DashboardType
from stock_risk_mcp.repository import RiskRepository


def test_dashboard_build_repository_round_trip(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    result = DashboardBuildResult(
        dashboard_id="dashboard-1", dashboard_type=DashboardType.DAILY, as_of_date=date(2026, 6, 13),
        status=DashboardBuildStatus.COMPLETED, output_path="daily.html", section_count=3,
        warnings=["research only"], generated_at=datetime(2026, 6, 13),
    )

    repository.save_dashboard_build(result)

    assert repository.get_dashboard_build("dashboard-1") == result
    assert repository.list_dashboard_builds() == [result]
