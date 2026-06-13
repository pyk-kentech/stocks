from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from stock_risk_mcp.connector_pipeline import run_connectors
from stock_risk_mcp.connector_registry import ConnectorRegistry
from stock_risk_mcp.connector_run import ConnectorMode, ConnectorRunStatus
from stock_risk_mcp.http_connector import KIND_TO_CONNECTOR, PublicHTTPConnector
from stock_risk_mcp.import_run import ImportSourceType
from stock_risk_mcp.local_connector import LocalFileConnector
from stock_risk_mcp.provider_normalization import normalize_sources
from stock_risk_mcp.provider_pack_config import ProviderPackConfig, ProviderPackProviderConfig
from stock_risk_mcp.provider_packs import ProviderPackRun, ProviderPackRunStatus, ProviderPackType
from stock_risk_mcp.repository import RiskRepository


def run_provider_pack(
    repository: RiskRepository,
    config: ProviderPackConfig,
    pack_type: ProviderPackType,
    output_dir: str | Path,
    as_of_date: date,
    *,
    enable_network: bool = False,
    allowed_hosts: list[str] | None = None,
    tickers: list[str] | None = None,
    client=None,
) -> ProviderPackRun:
    providers = _selected_providers(config, pack_type)
    output_root = Path(output_dir)
    connector_results = []
    provider_outputs = []
    for provider in providers:
        registry = ConnectorRegistry()
        connector = _build_connector(provider, enable_network, allowed_hosts, client)
        registry.register_connector(connector)
        result = run_connectors(
            repository, registry, as_of_date, output_root / "raw" / provider.provider_name,
            [provider.provider_name], tickers or [],
        )[0]
        connector_results.append(result)
        if result.output:
            provider_outputs.append((provider, result.output.output_path))

    normalize_run = None
    import_run = None
    if provider_outputs:
        sources = [{
            "normalizer": provider.normalizer or "",
            "input_file": path,
            "output_name": f"{provider.provider_name}-normalized.csv",
            "columns": provider.columns,
        } for provider, path in provider_outputs]
        normalize_run, import_run = normalize_sources(
            sources, output_root / "normalized", as_of_date,
            repository=repository, save=True, import_outputs=True,
        )

    errors = [
        error
        for result in connector_results
        for error in result.connector_run.errors
    ]
    warnings = [
        warning
        for result in connector_results
        for warning in result.connector_run.warnings
    ]
    if normalize_run:
        errors.extend(error for item in normalize_run.source_results for error in item.errors)
        warnings.extend(warning for item in normalize_run.source_results for warning in item.warnings)
    if import_run:
        errors.extend(error for item in import_run.source_results for error in item.errors)
        warnings.extend(warning for item in import_run.source_results for warning in item.warnings)

    status = _pack_status(pack_type, providers, connector_results, normalize_run, import_run)
    output_paths = [path for _, path in provider_outputs]
    if normalize_run:
        output_paths.extend(normalize_run.output_paths)
    run = ProviderPackRun(
        provider_pack_type=pack_type,
        as_of_date=as_of_date,
        status=status,
        connector_run_ids=[item.connector_run.connector_run_id for item in connector_results],
        normalize_run_id=normalize_run.normalize_run_id if normalize_run else None,
        import_run_id=import_run.import_run_id if import_run else None,
        output_paths=output_paths,
        warnings=warnings,
        errors=errors,
        completed_at=datetime.now(),
    )
    repository.save_provider_pack_run(run)
    return run


def _selected_providers(config: ProviderPackConfig, pack_type: ProviderPackType):
    if pack_type == ProviderPackType.PRICE:
        return config.price.providers
    if pack_type == ProviderPackType.FX:
        return config.fx.providers
    if pack_type == ProviderPackType.PRICE_AND_FX:
        return [*config.price.providers, *config.fx.providers]
    return []


def _build_connector(provider: ProviderPackProviderConfig, enable_network, allowed_hosts, client):
    if provider.url:
        return PublicHTTPConnector(
            provider.as_http_config(), enable_network=enable_network,
            runtime_allowed_hosts=allowed_hosts, client=client,
        )
    connector = LocalFileConnector(
        provider.provider_name, KIND_TO_CONNECTOR[provider.data_kind], provider.local_file, copy=True,
    )
    if provider.enabled:
        return connector
    connector.mode = ConnectorMode.DISABLED
    return connector


def _pack_status(pack_type, providers, connector_results, normalize_run, import_run):
    connector_statuses = [item.connector_run.status for item in connector_results]
    if connector_statuses and all(item == ConnectorRunStatus.DISABLED for item in connector_statuses):
        return ProviderPackRunStatus.DISABLED
    price_success = _import_succeeded(import_run, ImportSourceType.PRICE_HISTORY)
    fx_success = _import_succeeded(import_run, ImportSourceType.FX_RATE)
    failed_step = (
        not providers
        or any(item != ConnectorRunStatus.COMPLETED for item in connector_statuses)
        or (normalize_run is not None and any(item.error_count for item in normalize_run.source_results))
        or (import_run is not None and any(item.error_count for item in import_run.source_results))
    )
    if pack_type == ProviderPackType.PRICE_AND_FX:
        if not price_success:
            return ProviderPackRunStatus.FAILED
        return ProviderPackRunStatus.PARTIAL if not fx_success or failed_step else ProviderPackRunStatus.COMPLETED
    success = price_success if pack_type == ProviderPackType.PRICE else fx_success
    if not success:
        return ProviderPackRunStatus.FAILED
    return ProviderPackRunStatus.PARTIAL if failed_step else ProviderPackRunStatus.COMPLETED


def _import_succeeded(import_run, source_type: ImportSourceType) -> bool:
    return bool(import_run and any(
        item.source_type == source_type and item.error_count == 0
        for item in import_run.source_results
    ))
