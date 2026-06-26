from __future__ import annotations

from stock_risk_mcp.historical_market_data_capture_plan_engine import build_historical_chart_capture_plan
from stock_risk_mcp.historical_market_data_coverage_engine import build_historical_market_data_coverage
from stock_risk_mcp.historical_market_data_import_engine import import_historical_chart_responses
from stock_risk_mcp.historical_market_data_manifest_engine import (
    build_historical_market_data_storage_capability_report,
    build_historical_ohlcv_dataset_manifest,
)
from stock_risk_mcp.historical_market_data_models import (
    HistoricalMarketDataPipelineInput,
    HistoricalMarketDataPipelineResult,
    HistoricalMarketDataReadinessStatus,
    HistoricalMarketDataSafetyReport,
    HistoricalMarketDataStrategyResearchReadinessItem,
    HistoricalMarketDataStrategyResearchReadinessReport,
    HistoricalMarketDataStrategyResearchSupport,
    HistoricalMarketDataV10IntegrationReport,
    HistoricalMarketDataV11IntegrationReport,
    HistoricalMarketDataV8IntegrationReport,
)
from stock_risk_mcp.historical_market_data_normalizer import normalize_historical_ohlcv_rows
from stock_risk_mcp.historical_market_data_raw_lake import persist_historical_chart_raw_lake


def _strategy_report(dataset_id: str, rows) -> HistoricalMarketDataStrategyResearchReadinessReport:
    intervals = {row.interval.value for row in rows}
    has_intraday = "1M" in intervals
    has_daily = "1D" in intervals
    has_volume = any(row.volume is not None for row in rows)
    support = HistoricalMarketDataStrategyResearchSupport.SUPPORTED if has_daily else HistoricalMarketDataStrategyResearchSupport.PARTIAL
    volume_support = HistoricalMarketDataStrategyResearchSupport.SUPPORTED if has_volume else HistoricalMarketDataStrategyResearchSupport.PARTIAL
    intraday_partial = HistoricalMarketDataStrategyResearchSupport.PARTIAL if has_intraday else HistoricalMarketDataStrategyResearchSupport.UNSUPPORTED
    return HistoricalMarketDataStrategyResearchReadinessReport(
        report_id=f"{dataset_id}-STRATEGY-RESEARCH-READINESS-REPORT",
        rows=[
            HistoricalMarketDataStrategyResearchReadinessItem(
                strategy_family="MACD/RSI crossover and pullback strategies",
                support=support,
                rationale="daily and normalized OHLCV rows support indicator computation",
            ),
            HistoricalMarketDataStrategyResearchReadinessItem(
                strategy_family="RSI divergence strategies",
                support=support,
                rationale="price path supports deterministic divergence research inputs",
            ),
            HistoricalMarketDataStrategyResearchReadinessItem(
                strategy_family="HMA trend-filter strategies",
                support=support,
                rationale="normalized close series supports moving-average trend filters",
            ),
            HistoricalMarketDataStrategyResearchReadinessItem(
                strategy_family="volume-confirmed momentum strategies",
                support=volume_support,
                rationale="volume field is present for normalized bars",
            ),
            HistoricalMarketDataStrategyResearchReadinessItem(
                strategy_family="reward/risk and stop/target label simulation",
                support=support,
                rationale="future OHLCV path can support deterministic label simulation in downstream layers",
            ),
            HistoricalMarketDataStrategyResearchReadinessItem(
                strategy_family="CVD/order-flow strategies",
                support=HistoricalMarketDataStrategyResearchSupport.UNSUPPORTED,
                rationale="tick/trade/order-flow data is required",
            ),
            HistoricalMarketDataStrategyResearchReadinessItem(
                strategy_family="POC/volume-profile strategies",
                support=intraday_partial,
                rationale="intraday volume-at-price or stronger intraday reconstruction is required",
            ),
            HistoricalMarketDataStrategyResearchReadinessItem(
                strategy_family="true liquidity absorption detection",
                support=HistoricalMarketDataStrategyResearchSupport.UNSUPPORTED,
                rationale="daily OHLCV alone cannot represent true absorption",
            ),
        ],
    )


def build_historical_market_data_pipeline(pipeline_input: HistoricalMarketDataPipelineInput) -> HistoricalMarketDataPipelineResult:
    api_catalog_report, capture_plan = build_historical_chart_capture_plan(pipeline_input)
    raw_responses = import_historical_chart_responses(pipeline_input)
    raw_lake_records = persist_historical_chart_raw_lake(pipeline_input, raw_responses)
    ohlcv_rows = normalize_historical_ohlcv_rows(pipeline_input.dataset_id, raw_responses)
    coverage_report, freshness_report, completeness_report, gap_report = build_historical_market_data_coverage(
        pipeline_input.dataset_id,
        raw_responses,
        ohlcv_rows,
    )
    storage_capability_report = build_historical_market_data_storage_capability_report(
        pipeline_input.dataset_id,
        pipeline_input.requested_storage_formats,
    )
    dataset_manifest, price_history_rows = build_historical_ohlcv_dataset_manifest(pipeline_input, ohlcv_rows)
    v8_report = HistoricalMarketDataV8IntegrationReport(
        report_id=f"{pipeline_input.dataset_id}-V8-INTEGRATION-REPORT",
        chart_schema_alignment_ready=bool(ohlcv_rows),
        manual_import_lineage_ready=bool(raw_responses),
        readonly_capture_boundary_preserved=True,
    )
    v10_report = HistoricalMarketDataV10IntegrationReport(
        report_id=f"{pipeline_input.dataset_id}-V10-INTEGRATION-REPORT",
        price_history_rows_ready=bool(price_history_rows),
        normalized_manifest_ready=dataset_manifest.readiness_status == HistoricalMarketDataReadinessStatus.V10_MANIFEST_READY,
        feature_store_dataset_compatible=bool(price_history_rows),
        v10_price_history_rows=price_history_rows,
    )
    v11_report = HistoricalMarketDataV11IntegrationReport(
        report_id=f"{pipeline_input.dataset_id}-V11-INTEGRATION-REPORT",
        paper_evaluation_replay_ready=bool(ohlcv_rows),
        interval_support_ready=bool({row.interval.value for row in ohlcv_rows} & {"1D", "1M"}),
        ohlcv_label_simulation_ready=bool(ohlcv_rows),
    )
    safety_report = HistoricalMarketDataSafetyReport(
        report_id=f"{pipeline_input.dataset_id}-SAFETY-REPORT",
        readiness_status=HistoricalMarketDataReadinessStatus.RESEARCH_ONLY if capture_plan.readiness_status == HistoricalMarketDataReadinessStatus.BLOCKED else HistoricalMarketDataReadinessStatus.COVERAGE_READY,
        findings=[
            "real chart capture remains blocked by default",
            "tests use local/manual/mock capture only",
            "no account/order path is present",
            "no env/credential read is performed",
        ],
        real_capture_blocked=True,
    )
    return HistoricalMarketDataPipelineResult(
        api_catalog_report=api_catalog_report,
        capture_plan=capture_plan,
        raw_responses=raw_responses,
        raw_lake_records=raw_lake_records,
        ohlcv_rows=ohlcv_rows,
        dataset_manifest=dataset_manifest,
        coverage_report=coverage_report,
        freshness_report=freshness_report,
        completeness_report=completeness_report,
        storage_capability_report=storage_capability_report,
        v8_integration_report=v8_report,
        v10_integration_report=v10_report,
        v11_integration_report=v11_report,
        strategy_research_readiness_report=_strategy_report(pipeline_input.dataset_id, ohlcv_rows),
        safety_report=safety_report,
        gap_report=gap_report,
    )
