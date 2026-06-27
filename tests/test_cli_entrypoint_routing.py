from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from stock_risk_mcp.cli import build_command_parser, main, run_command
from stock_risk_mcp.kiwoom_oauth_models import KiwoomEnvironment, KiwoomOAuthStatus, KiwoomOAuthTokenIssueResponse


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
    assert "--upd-stkpc-tp" in result.stdout
    assert "--request-sleep-seconds" in result.stdout
    assert "--symbol-sleep-seconds" in result.stdout
    assert "--max-symbols-per-run" in result.stdout
    assert "--resume-from-capture-state" in result.stdout
    assert "--reuse-existing-raw-lake" in result.stdout
    assert "--backfill-cache-gaps" in result.stdout
    assert "--max-backfill-pages-per-symbol" in result.stdout
    assert "--prefer-full-coverage-training" in result.stdout
    assert "--symbols-file" in result.stdout
    assert "--batch-size" in result.stdout
    assert "--batch-index" in result.stdout
    assert "--max-batches" in result.stdout
    assert "--resume-all" in result.stdout
    assert "--capture-state-root" in result.stdout
    assert "--strategy-families" in result.stdout
    assert "--search-mode" in result.stdout
    assert "--walk-forward-mode" in result.stdout
    assert "--promotion-profile" in result.stdout
    assert "--fill-policy" in result.stdout
    assert "--direction" in result.stdout
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


def test_token_command_reports_failed_top_level_status(monkeypatch, tmp_path) -> None:
    parser = build_command_parser()
    output_file = tmp_path / "token_issue.json"
    args = parser.parse_args(
        [
            "kiwoom-oauth-token-issue-run",
            "--kiwoom-environment",
            "MOCK",
            "--credential-ref",
            str(tmp_path),
            "--acknowledge-readonly-only",
            "--acknowledge-user-initiated",
            "--acknowledge-credential-redaction",
            "--allow-real-chart-capture",
            "--output-file",
            str(output_file),
        ]
    )
    monkeypatch.setattr(
        "stock_risk_mcp.cli.issue_kiwoom_oauth_token",
        lambda _request: KiwoomOAuthTokenIssueResponse(
            status=KiwoomOAuthStatus.PROVIDER_TOKEN_ERROR,
            stage="TOKEN_ISSUE_HTTP",
            kiwoom_environment=KiwoomEnvironment.MOCK,
            endpoint_base_url="https://mockapi.kiwoom.com",
            endpoint_path="/oauth2/token",
            request_content_type="application/json;charset=UTF-8",
            request_body_shape=["grant_type", "appkey", "secretkey"],
            credential_ref_status="LOADED",
            token_written=False,
            provider_return_code=5001,
            provider_return_msg="mock provider token rejected",
            issued_at="2026-06-27T00:00:00+00:00",
            return_msg_redacted="mock provider token rejected",
        ),
    )
    result = run_command(args)
    assert result["status"] == "FAILED"
    assert result["token_status"] == "PROVIDER_TOKEN_ERROR"
    assert result["provider_return_code"] == 5001
    assert output_file.exists()


def test_main_exits_nonzero_on_failed_token_command(monkeypatch) -> None:
    monkeypatch.setattr("stock_risk_mcp.cli.run_command", lambda args: {"status": "FAILED", "args_seen": bool(args.command)})
    with pytest.raises(SystemExit) as exc:
        main(["kiwoom-oauth-token-issue-run", "--kiwoom-environment", "MOCK", "--credential-ref", "/tmp/ref"])
    assert exc.value.code == 1
