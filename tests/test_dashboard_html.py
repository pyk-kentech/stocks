from stock_risk_mcp.dashboard_html import render_dashboard_html
from stock_risk_mcp.dashboard_models import DashboardSection, DashboardType
from stock_risk_mcp.notifications import NotificationSeverity


def test_dashboard_html_is_self_contained_escaped_and_sorted() -> None:
    html = render_dashboard_html("Test <Dashboard>", DashboardType.OVERVIEW, [
        DashboardSection(title="Info", summary="safe", html="<p>safe</p>", severity=NotificationSeverity.INFO),
        DashboardSection(title="<Critical>", summary="<script>alert(1)</script>", html="<p>escaped body</p>", severity=NotificationSeverity.CRITICAL),
    ])

    assert "&lt;Dashboard&gt;" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert html.index("&lt;Critical&gt;") < html.index("Info")
    assert "paper trading and research monitoring" in html
    assert "<script" not in html.lower()
    assert "cdn" not in html.lower()
    assert "http://" not in html.lower()
    assert "https://" not in html.lower()
