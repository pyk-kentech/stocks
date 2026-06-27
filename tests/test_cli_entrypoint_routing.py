from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHONPATH = str(REPO_ROOT / "src")


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": PYTHONPATH}
    return subprocess.run(
        [sys.executable, "-m", "stock_risk_mcp.cli", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def test_root_help_includes_kiwoom_commands() -> None:
    result = _run_cli("--help")
    assert result.returncode == 0
    assert "kiwoom-oauth-token-issue-run" in result.stdout
    assert "kiwoom-ka10081-capture-and-train-run" in result.stdout


def test_kiwoom_oauth_help_uses_command_router() -> None:
    result = _run_cli("kiwoom-oauth-token-issue-run", "--help")
    assert result.returncode == 0
    assert "--kiwoom-environment" in result.stdout
    assert "--token-store-root" in result.stdout
    assert "--ticker" not in result.stdout
    assert "--side" not in result.stdout
    assert "--confidence" not in result.stdout
    assert "Evaluate a stock trade proposal" not in result.stdout


def test_kiwoom_capture_and_train_help_uses_command_router() -> None:
    result = _run_cli("kiwoom-ka10081-capture-and-train-run", "--help")
    assert result.returncode == 0
    assert "--training-handoff-mode" in result.stdout
    assert "--training-output-root" in result.stdout
    assert "--ticker" not in result.stdout
    assert "--side" not in result.stdout
    assert "--confidence" not in result.stdout
    assert "Evaluate a stock trade proposal" not in result.stdout


def test_unknown_command_fails_with_router_error() -> None:
    result = _run_cli("kiwoom-oauth-token-issue-run-typo")
    assert result.returncode != 0
    combined = f"{result.stdout}\n{result.stderr}"
    assert "invalid choice" in combined
    assert "--ticker" not in combined
    assert "Evaluate a stock trade proposal" not in combined


def test_oauth_command_missing_args_reports_oauth_requirements() -> None:
    result = _run_cli("kiwoom-oauth-token-issue-run")
    assert result.returncode != 0
    combined = f"{result.stdout}\n{result.stderr}"
    assert "--kiwoom-environment" in combined or "--credential-ref" in combined or "--appkey-ref-path" in combined
    assert "--ticker" not in combined
    assert "Evaluate a stock trade proposal" not in combined


def test_legacy_behavior_requires_explicit_route() -> None:
    result = _run_cli("legacy-evaluate", "--help")
    assert result.returncode == 0
    assert "--ticker" in result.stdout
    assert "--side" in result.stdout
    assert "--confidence" in result.stdout
    assert "Evaluate a stock trade proposal" in result.stdout
