from __future__ import annotations

from stock_risk_mcp.historical_market_data_api_catalog import build_historical_market_data_api_catalog
from stock_risk_mcp.historical_market_data_guard import validate_profile_guard, validate_real_capture_opt_in
from stock_risk_mcp.historical_market_data_models import (
    HistoricalChartCaptureDecision,
    HistoricalChartCapturePlan,
    HistoricalChartCaptureTask,
    HistoricalChartRequestPreview,
    HistoricalChartRequestSpec,
    HistoricalMarketDataMode,
    HistoricalMarketDataPipelineInput,
    HistoricalMarketDataProvider,
    HistoricalMarketDataReadinessStatus,
    HistoricalMarketDataSchemaStatus,
)


def _preview(spec: HistoricalChartRequestSpec, request_path: str) -> HistoricalChartRequestPreview:
    body = {
        "stk_cd": spec.provider_symbol,
        "upd_stkpc_tp": spec.upd_stkpc_tp,
    }
    if spec.base_dt is not None:
        body["base_dt"] = spec.base_dt
    if spec.tic_scope is not None:
        body["tic_scope"] = spec.tic_scope
    return HistoricalChartRequestPreview(
        report_id=f"{spec.request_id}-REQUEST-PREVIEW",
        api_id=spec.api_id,
        provider=HistoricalMarketDataProvider.KIWOOM_REST,
        path=request_path,
        headers={
            "api-id": spec.api_id.value,
            "authorization": "Bearer <TOKEN_REF_ONLY>",
            "cont-yn": spec.cont_yn,
            "next-key": spec.next_key,
        },
        body_json=body,
    )


def build_historical_chart_capture_plan(pipeline_input: HistoricalMarketDataPipelineInput) -> tuple[object, HistoricalChartCapturePlan]:
    catalog = build_historical_market_data_api_catalog()
    capability_by_api = {item.api_id: item for item in catalog.capabilities}
    profile_reasons = validate_profile_guard(pipeline_input.capture_profile)
    real_capture_reasons = validate_real_capture_opt_in(pipeline_input.mode, pipeline_input.opt_in)
    tasks: list[HistoricalChartCaptureTask] = []

    for spec in pipeline_input.request_specs:
        capability = capability_by_api[spec.api_id]
        reasons = list(profile_reasons)
        if capability.schema_status != HistoricalMarketDataSchemaStatus.SCHEMA_READY:
            reasons.append("SCHEMA_NOT_READY")
        if pipeline_input.mode == HistoricalMarketDataMode.REAL_OPT_IN_BOUNDARY:
            reasons.extend(real_capture_reasons)
            if not capability.real_capture_boundary_supported:
                reasons.append("REAL_CAPTURE_NOT_SUPPORTED_FOR_API")
        decision = HistoricalChartCaptureDecision.ALLOWED if not reasons else HistoricalChartCaptureDecision.BLOCKED
        tasks.append(
            HistoricalChartCaptureTask(
                task_id=f"{spec.request_id}-TASK",
                request_spec=spec,
                request_preview=_preview(spec, capability.request_path),
                capability=capability,
                execution_decision=decision,
                blocking_reasons=sorted(set(reasons)),
            )
        )

    readiness = HistoricalMarketDataReadinessStatus.CAPTURE_PLAN_READY
    if any(task.execution_decision == HistoricalChartCaptureDecision.BLOCKED for task in tasks):
        readiness = HistoricalMarketDataReadinessStatus.RESEARCH_ONLY
    if pipeline_input.mode == HistoricalMarketDataMode.REAL_OPT_IN_BOUNDARY and all(
        task.execution_decision == HistoricalChartCaptureDecision.BLOCKED for task in tasks
    ):
        readiness = HistoricalMarketDataReadinessStatus.BLOCKED
    return catalog, HistoricalChartCapturePlan(
        plan_id=f"{pipeline_input.dataset_id}-CAPTURE-PLAN",
        dataset_id=pipeline_input.dataset_id,
        capture_profile=pipeline_input.capture_profile,
        mode=pipeline_input.mode,
        tasks=tasks,
        readiness_status=readiness,
        bounded=True,
    )
