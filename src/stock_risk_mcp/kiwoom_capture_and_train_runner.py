from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.historical_market_data_capture_runner import run_historical_market_data_real_capture
from stock_risk_mcp.historical_market_data_manifest_engine import load_historical_ohlcv_dataset_manifest
from stock_risk_mcp.historical_market_data_models import (
    HistoricalChartCaptureRunResult,
    HistoricalMarketDataPipelineInput,
    HistoricalMarketDataReadinessStatus,
)
from stock_risk_mcp.historical_market_data_transport import RealKiwoomChartTransport
from stock_risk_mcp.historical_market_data_guard import validate_safe_local_root
from stock_risk_mcp.kiwoom_oauth_engine import build_kiwoom_oauth_request, issue_kiwoom_oauth_token
from stock_risk_mcp.kiwoom_oauth_models import KiwoomCredentialRef, KiwoomEnvironment, KiwoomOAuthStatus
from stock_risk_mcp.offline_strategy_integration_engine import build_offline_strategy_pipeline
from stock_risk_mcp.offline_strategy_models import OfflineStrategyPipelineInput


def _kiwoom_base_url(environment: KiwoomEnvironment) -> str:
    return "https://mockapi.kiwoom.com" if environment == KiwoomEnvironment.MOCK else "https://api.kiwoom.com"


def _read_bearer_header_from_token_ref(token_ref_path: str) -> str:
    payload = json.loads(Path(token_ref_path).read_text(encoding="utf-8"))
    token = str(payload.get("token") or "").strip()
    token_type = str(payload.get("token_type") or "Bearer").strip()
    if not token:
        raise ValueError("token ref did not contain token")
    return f"{token_type} {token}"


def run_historical_market_data_real_capture_and_manifest(
    pipeline_input: HistoricalMarketDataPipelineInput,
    *,
    environment: KiwoomEnvironment,
    token_store_root: str,
    force_refresh_token: bool = False,
) -> tuple[HistoricalChartCaptureRunResult, dict[str, object]]:
    if pipeline_input.real_capture_config is None or pipeline_input.real_capture_config.credential_ref is None:
        raise ValueError("real capture credential ref is required")
    historical_ref = pipeline_input.real_capture_config.credential_ref
    oauth_credential_ref = KiwoomCredentialRef(
        credential_id=historical_ref.credential_ref_id,
        credential_ref_dir=historical_ref.credential_ref_dir,
        appkey_ref_path=historical_ref.appkey_ref_path,
        secretkey_ref_path=historical_ref.secretkey_ref_path,
    )
    oauth_request = build_kiwoom_oauth_request(
        environment=environment,
        credential_ref=oauth_credential_ref,
        token_store_root=token_store_root,
        allow_real_network=pipeline_input.opt_in.allow_real_chart_capture,
        allow_token_issue=True,
        acknowledge_readonly_only=pipeline_input.opt_in.acknowledge_readonly_only,
        acknowledge_user_initiated=pipeline_input.opt_in.acknowledge_user_initiated,
        acknowledge_credential_redaction=pipeline_input.opt_in.acknowledge_credential_redaction,
        force_refresh_token=force_refresh_token,
    )
    token_response = issue_kiwoom_oauth_token(oauth_request)
    if token_response.status not in {KiwoomOAuthStatus.TOKEN_ISSUED, KiwoomOAuthStatus.TOKEN_CACHE_HIT} or token_response.token_ref is None:
        blocked = HistoricalChartCaptureRunResult.model_validate(
            {
                "run_id": f"{pipeline_input.dataset_id}-REAL-CAPTURE-RUN",
                "dataset_id": pipeline_input.dataset_id,
                "readiness_status": HistoricalMarketDataReadinessStatus.BLOCKED_AUTH_OR_TOKEN.value,
                "task_results": [
                    {
                        "task_id": f"{pipeline_input.dataset_id}-BLOCKED",
                        "request_id": f"{pipeline_input.dataset_id}-BLOCKED",
                        "execution_decision": "BLOCKED",
                        "blocked_reasons": [token_response.status.value],
                    }
                ],
            }
        )
        return blocked, {"oauth_status": token_response.status.value}
    transport = RealKiwoomChartTransport(
        timeout_seconds=pipeline_input.real_capture_config.timeout_seconds,
        base_url=_kiwoom_base_url(environment),
    )
    result = run_historical_market_data_real_capture(
        pipeline_input,
        transport=transport,
        auth_header=_read_bearer_header_from_token_ref(token_response.token_ref.token_ref_path),
    )
    return result, {
        "oauth_status": token_response.status.value,
        "token_ref_path": token_response.token_ref.token_ref_path,
    }


def run_kiwoom_ka10081_capture_and_train(
    pipeline_input: HistoricalMarketDataPipelineInput,
    *,
    environment: KiwoomEnvironment,
    token_store_root: str,
    training_output_root: str,
    training_handoff_mode: str = "persisted_manifest",
    requested_template_ids: list[str] | None = None,
    asset_liquidity_profile: str = "LARGE_CAP",
) -> dict[str, object]:
    capture_result, oauth_summary = run_historical_market_data_real_capture_and_manifest(
        pipeline_input,
        environment=environment,
        token_store_root=token_store_root,
    )
    if capture_result.manifest is None or not capture_result.manifest.manifest_path:
        return {
            "status": capture_result.readiness_status.value,
            "training_handoff_mode": training_handoff_mode,
            "manifest_written": False,
            "manifest_reloaded": False,
            "training_started": False,
            "training_completed": False,
            "oauth_status": oauth_summary.get("oauth_status"),
        }
    manifest_path = Path(capture_result.manifest.manifest_path)
    if not manifest_path.exists():
        raise ValueError("persisted manifest file missing after capture")
    manifest = load_historical_ohlcv_dataset_manifest(manifest_path)
    pipeline = OfflineStrategyPipelineInput(
        pipeline_id=f"{pipeline_input.dataset_id}-OFFLINE-STRATEGY",
        dataset_id=pipeline_input.dataset_id,
        manifest=manifest,
        requested_template_ids=requested_template_ids or [],
        asset_liquidity_profile=asset_liquidity_profile,
    )
    if training_handoff_mode == "in_process":
        pipeline = pipeline.model_copy(update={"manifest": capture_result.manifest})
    output_root = validate_safe_local_root(training_output_root) / pipeline_input.dataset_id.lower()
    reports_dir = output_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    training_started = True
    training_result = build_offline_strategy_pipeline(pipeline)
    training_plan_path = reports_dir / "offline_strategy_training_plan.json"
    promotion_gate_path = reports_dir / "offline_strategy_promotion_gate.json"
    summary_path = output_root / "capture_and_train_summary.json"
    training_plan_path.write_text(training_result.training_plan.model_dump_json(indent=2), encoding="utf-8")
    promotion_gate_path.write_text(
        json.dumps([item.model_dump(mode="json") for item in training_result.promotion_decisions], indent=2),
        encoding="utf-8",
    )
    raw_lake_paths = sorted(str(path) for path in Path(pipeline_input.raw_lake_root).glob("*.json"))
    normalized_paths = [path for path in [manifest.ohlcv_rows_path, manifest.manifest_path] if path]
    summary = {
        "status": capture_result.readiness_status.value,
        "oauth_status": oauth_summary.get("oauth_status"),
        "training_handoff_mode": training_handoff_mode,
        "manifest_written": True,
        "manifest_path": str(manifest_path),
        "manifest_id": manifest.manifest_id,
        "manifest_reloaded": True,
        "raw_lake_paths": raw_lake_paths,
        "normalized_ohlcv_paths": normalized_paths,
        "training_started": training_started,
        "training_completed": True,
        "offline_strategy_output_root": str(output_root),
        "promotion_gate_output_path": str(promotion_gate_path),
        "training_plan_output_path": str(training_plan_path),
        "candidate_count": len(training_result.candidates),
        "promotion_decision_count": len(training_result.promotion_decisions),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
