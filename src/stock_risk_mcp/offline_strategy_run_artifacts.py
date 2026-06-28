from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from stock_risk_mcp.historical_market_data_guard import validate_safe_local_root


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_output(*args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(_repo_root()), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = completed.stdout.strip()
    return value or None


def resolve_git_metadata() -> dict[str, str | None]:
    commit = _git_output("rev-parse", "HEAD")
    tags = _git_output("tag", "--points-at", "HEAD")
    git_tag = tags.splitlines()[0].strip() if tags else None
    return {
        "git_commit": commit,
        "git_tag": git_tag,
        "run_version": git_tag or (commit[:12] if commit else "UNKNOWN_VERSION"),
    }


def resolve_offline_strategy_runs_root(training_output_root: str | Path) -> Path:
    base = validate_safe_local_root(training_output_root)
    if base.name.startswith("offline_strategy"):
        return base.with_name("offline_strategy_runs")
    return base / "offline_strategy_runs"


def build_offline_strategy_run_id() -> str:
    created_at = datetime.now().astimezone()
    suffix = uuid4().hex[:6]
    return f"{created_at:%Y%m%d_%H%M%S}_{suffix}"


def initialize_offline_strategy_run(
    *,
    training_output_root: str | Path,
    dataset_id: str,
    search_mode: str,
    strategy_families: list[str] | None,
    watchlist_dataset_id: str | None = None,
) -> dict[str, object]:
    run_id = build_offline_strategy_run_id()
    metadata = resolve_git_metadata()
    created_at = datetime.now().astimezone().isoformat()
    runs_root = resolve_offline_strategy_runs_root(training_output_root)
    dataset_root = runs_root / dataset_id.lower()
    run_root = dataset_root / run_id
    run_root.mkdir(parents=True, exist_ok=True)
    reports_dir = run_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return {
        "offline_strategy_run_id": run_id,
        "offline_strategy_run_version": metadata["run_version"],
        "offline_strategy_run_root": str(run_root),
        "offline_strategy_reports_root": str(reports_dir),
        "offline_strategy_dataset_root": str(dataset_root),
        "offline_strategy_latest_pointer_path": str(dataset_root / "latest_run.json"),
        "git_commit": metadata["git_commit"],
        "git_tag": metadata["git_tag"],
        "created_at": created_at,
        "dataset_id": dataset_id,
        "watchlist_dataset_id": watchlist_dataset_id,
        "search_mode": str(search_mode or "BOUNDED_GRID").upper(),
        "strategy_families": sorted({str(item).strip().upper() for item in (strategy_families or []) if str(item).strip()}),
    }


def load_latest_run_pointer(dataset_root: str | Path) -> dict[str, object] | None:
    path = Path(dataset_root) / "latest_run.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_latest_run_pointer(dataset_root: str | Path, payload: dict[str, object]) -> str:
    path = Path(dataset_root) / "latest_run.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)
