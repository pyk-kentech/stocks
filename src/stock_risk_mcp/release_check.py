from __future__ import annotations

from datetime import date
from pathlib import Path


MAJOR_CLI_COMMANDS = [
    "run-local-demo", "system-smoke", "release-check", "run-connectors-and-import",
    "run-paper-pipeline", "report-pipeline", "agent-run-local", "notify-pipeline",
    "dashboard-overview",
]


def build_release_check(project_root: str | Path | None = None) -> dict[str, object]:
    root = Path(project_root or Path.cwd())
    dashboard_paths = sorted(root.glob("**/dashboard*.html"), key=lambda item: item.stat().st_mtime, reverse=True)
    return {
        "status": "READY_FOR_MANUAL_VERIFICATION",
        "commands": {
            "pytest": "pytest -q",
            "compileall": "python -m compileall -q src",
            "diff_check": "git diff --check",
            "system_smoke": "python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs",
        },
        "documents": {
            "README.md": (root / "README.md").exists(),
            "WORK_SUMMARY.md": (root / "WORK_SUMMARY.md").exists(),
        },
        "major_cli_commands": MAJOR_CLI_COMMANDS,
        "recent_dashboard_smoke": str(dashboard_paths[0]) if dashboard_paths else None,
        "recommended_tag": f"v0.1.0-local-demo-{date.today():%Y%m%d}",
        "tag_created": False,
        "notes": ["Commands are guidance only; release-check does not run them or create git tags."],
    }
