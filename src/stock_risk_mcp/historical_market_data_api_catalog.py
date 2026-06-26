from __future__ import annotations

from stock_risk_mcp.historical_market_data_models import (
    HistoricalMarketDataApiCapability,
    HistoricalMarketDataApiCatalogReport,
    HistoricalMarketDataApiId,
    HistoricalMarketDataCredentialPolicy,
    HistoricalMarketDataInterval,
    HistoricalMarketDataProvider,
    HistoricalMarketDataSchemaStatus,
)


def build_historical_market_data_api_catalog() -> HistoricalMarketDataApiCatalogReport:
    capabilities = [
        HistoricalMarketDataApiCapability(
            api_id=HistoricalMarketDataApiId.KA10080,
            provider=HistoricalMarketDataProvider.KIWOOM_REST,
            interval=HistoricalMarketDataInterval.ONE_MINUTE,
            schema_status=HistoricalMarketDataSchemaStatus.SCHEMA_READY,
            credential_policy=HistoricalMarketDataCredentialPolicy.KEY_REF_ONLY,
            request_path="/api/dostk/chart",
            request_fields=["STK_CD", "TIC_SCOPE", "UPD_STKPC_TP", "BASE_DT"],
            real_capture_boundary_supported=True,
            notes=["repo-local v8 chart adapter evidence exists"],
        ),
        HistoricalMarketDataApiCapability(
            api_id=HistoricalMarketDataApiId.KA10081,
            provider=HistoricalMarketDataProvider.KIWOOM_REST,
            interval=HistoricalMarketDataInterval.ONE_DAY,
            schema_status=HistoricalMarketDataSchemaStatus.SCHEMA_READY,
            credential_policy=HistoricalMarketDataCredentialPolicy.KEY_REF_ONLY,
            request_path="/api/dostk/chart",
            request_fields=["STK_CD", "BASE_DT", "UPD_STKPC_TP"],
            real_capture_boundary_supported=True,
            notes=["repo-local v8 chart adapter evidence exists"],
        ),
        HistoricalMarketDataApiCapability(
            api_id=HistoricalMarketDataApiId.KA10079,
            provider=HistoricalMarketDataProvider.KIWOOM_REST,
            interval=HistoricalMarketDataInterval.TICK,
            schema_status=HistoricalMarketDataSchemaStatus.CAPABILITY_ONLY,
            credential_policy=HistoricalMarketDataCredentialPolicy.MANUAL_IMPORT_ONLY,
            request_path="/api/dostk/chart",
            request_fields=[],
            real_capture_boundary_supported=False,
            notes=["tick chart parser intentionally not implemented in v14"],
        ),
        HistoricalMarketDataApiCapability(
            api_id=HistoricalMarketDataApiId.KA10082,
            provider=HistoricalMarketDataProvider.KIWOOM_REST,
            interval=HistoricalMarketDataInterval.ONE_WEEK,
            schema_status=HistoricalMarketDataSchemaStatus.SCHEMA_GAP,
            credential_policy=HistoricalMarketDataCredentialPolicy.MANUAL_IMPORT_ONLY,
            request_path="/api/dostk/chart",
            request_fields=[],
            real_capture_boundary_supported=False,
            notes=["weekly chart schema evidence missing"],
        ),
        HistoricalMarketDataApiCapability(
            api_id=HistoricalMarketDataApiId.KA10083,
            provider=HistoricalMarketDataProvider.KIWOOM_REST,
            interval=HistoricalMarketDataInterval.ONE_MONTH,
            schema_status=HistoricalMarketDataSchemaStatus.SCHEMA_GAP,
            credential_policy=HistoricalMarketDataCredentialPolicy.MANUAL_IMPORT_ONLY,
            request_path="/api/dostk/chart",
            request_fields=[],
            real_capture_boundary_supported=False,
            notes=["monthly chart schema evidence missing"],
        ),
        HistoricalMarketDataApiCapability(
            api_id=HistoricalMarketDataApiId.KA10094,
            provider=HistoricalMarketDataProvider.KIWOOM_REST,
            interval=HistoricalMarketDataInterval.ONE_YEAR,
            schema_status=HistoricalMarketDataSchemaStatus.CAPABILITY_ONLY,
            credential_policy=HistoricalMarketDataCredentialPolicy.MANUAL_IMPORT_ONLY,
            request_path="/api/dostk/chart",
            request_fields=[],
            real_capture_boundary_supported=False,
            notes=["yearly chart parser intentionally deferred"],
        ),
    ]
    return HistoricalMarketDataApiCatalogReport(
        report_id="HISTORICAL-MARKET-DATA-API-CATALOG-REPORT",
        capabilities=capabilities,
        schema_ready_api_ids=[item.api_id.value for item in capabilities if item.schema_status == HistoricalMarketDataSchemaStatus.SCHEMA_READY],
        capability_only_api_ids=[item.api_id.value for item in capabilities if item.schema_status == HistoricalMarketDataSchemaStatus.CAPABILITY_ONLY],
        schema_gap_api_ids=[item.api_id.value for item in capabilities if item.schema_status == HistoricalMarketDataSchemaStatus.SCHEMA_GAP],
    )
