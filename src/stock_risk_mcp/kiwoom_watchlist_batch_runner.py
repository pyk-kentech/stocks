from __future__ import annotations

import csv
import json
from pathlib import Path

from stock_risk_mcp.historical_market_data_models import HistoricalChartRequestSpec, HistoricalMarketDataPipelineInput
from stock_risk_mcp.historical_market_data_guard import validate_safe_local_root
from stock_risk_mcp.kiwoom_capture_and_train_runner import run_kiwoom_ka10081_capture_and_train
from stock_risk_mcp.kiwoom_oauth_models import KiwoomEnvironment


def load_watchlist_symbols(symbols_file: str | None) -> list[dict[str, object]]:
    if not symbols_file:
        return []
    path = Path(symbols_file)
    if not path.exists():
        raise FileNotFoundError(f"symbols file not found: {symbols_file}")
    if path.suffix.lower() == ".txt":
        return [{"symbol": line.strip().upper()} for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = []
            for row in csv.DictReader(handle):
                symbol = str(row.get("symbol") or "").strip().upper()
                if not symbol:
                    continue
                rows.append(
                    {
                        "symbol": symbol,
                        "name": str(row.get("name") or "").strip() or None,
                        "sector": str(row.get("sector") or "").strip() or None,
                        "priority": str(row.get("priority") or "").strip() or None,
                    }
                )
            return rows
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = []
        for item in payload:
            if isinstance(item, str):
                symbol = item.strip().upper()
                if symbol:
                    rows.append({"symbol": symbol})
                continue
            if isinstance(item, dict):
                symbol = str(item.get("symbol") or "").strip().upper()
                if symbol:
                    rows.append(
                        {
                            "symbol": symbol,
                            "name": str(item.get("name") or "").strip() or None,
                            "sector": str(item.get("sector") or "").strip() or None,
                            "priority": item.get("priority"),
                        }
                    )
        return rows
    raise ValueError(f"unsupported symbols file format: {path.suffix}")


def merge_symbol_sources(explicit_symbols: list[str], file_entries: list[dict[str, object]]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for symbol in explicit_symbols + [str(item.get("symbol") or "").strip().upper() for item in file_entries]:
        if not symbol or symbol in seen:
            continue
        ordered.append(symbol)
        seen.add(symbol)
    return ordered


def split_symbol_batches(symbols: list[str], batch_size: int) -> list[list[str]]:
    if batch_size <= 0:
        return [symbols]
    return [symbols[index : index + batch_size] for index in range(0, len(symbols), batch_size)]


def build_batch_pipeline(
    pipeline_input: HistoricalMarketDataPipelineInput,
    batch_symbols: list[str],
    *,
    batch_index: int,
    total_batches: int,
    capture_state_root: str | None,
) -> HistoricalMarketDataPipelineInput:
    spec_by_symbol = {spec.provider_symbol: spec for spec in pipeline_input.request_specs}
    request_specs: list[HistoricalChartRequestSpec] = [spec_by_symbol[symbol] for symbol in batch_symbols if symbol in spec_by_symbol]
    dataset_suffix = batch_symbols[0] if len(batch_symbols) == 1 else f"MULTI-{len(batch_symbols)}"
    store_root = (
        str(validate_safe_local_root(capture_state_root) / f"batch-{batch_index:03d}")
        if capture_state_root
        else pipeline_input.store_root
    )
    return pipeline_input.model_copy(
        update={
            "dataset_id": f"{pipeline_input.dataset_id}-BATCH-{batch_index:03d}-{dataset_suffix}",
            "store_root": store_root,
            "request_specs": request_specs,
            "pipeline_id": f"{pipeline_input.pipeline_id}-BATCH-{batch_index:03d}-OF-{total_batches:03d}",
        }
    )


def _next_resume_command(
    *,
    capture_state_path: str | None,
    symbols: list[str],
    symbols_file: str | None,
    batch_size: int,
    batch_index: int,
) -> str | None:
    if not capture_state_path:
        return None
    parts = [
        "python3.11 -m stock_risk_mcp.cli kiwoom-ka10081-capture-and-train-run",
        f"--batch-size {batch_size}",
        f"--batch-index {batch_index}",
        f"--resume-from-capture-state {capture_state_path}",
        "--reuse-existing-raw-lake",
        "--backfill-cache-gaps",
        "--prefer-full-coverage-training",
    ]
    if symbols:
        parts.append(f"--symbols {','.join(symbols)}")
    if symbols_file:
        parts.append(f"--symbols-file {symbols_file}")
    return " ".join(parts)


def run_kiwoom_watchlist_capture_and_train(
    pipeline_input: HistoricalMarketDataPipelineInput,
    *,
    environment: KiwoomEnvironment,
    token_store_root: str,
    training_output_root: str,
    training_handoff_mode: str,
    requested_template_ids: list[str] | None,
    asset_liquidity_profile: str,
    strategy_families: list[str] | None,
    search_mode: str | None,
    walk_forward_mode: str | None,
    promotion_profile: str | None,
    fill_policy: str | None,
    direction: str | None,
    request_sleep_seconds: float,
    symbol_sleep_seconds: float,
    max_symbols_per_run: int,
    stop_on_provider_limit: bool,
    resume_from_capture_state: str | None,
    reuse_existing_raw_lake: bool,
    allow_training_on_partial_capture: bool,
    backfill_cache_gaps: bool,
    max_backfill_pages_per_symbol: int | None,
    prefer_full_coverage_training: bool,
    symbols: list[str],
    symbols_file: str | None,
    batch_size: int,
    batch_index: int,
    max_batches: int | None,
    resume_all: bool,
    capture_state_root: str | None,
) -> dict[str, object]:
    batches = split_symbol_batches(symbols, batch_size)
    if max_batches and max_batches > 0:
        batches = batches[: max_batches]
    if not batches:
        raise ValueError("no symbols resolved for capture")
    selected_indices = list(range(len(batches))) if resume_all else [max(batch_index - 1, 0)]
    batch_results: list[dict[str, object]] = []
    for selected in selected_indices:
        if selected >= len(batches):
            break
        batch_symbols = batches[selected]
        batch_pipeline = build_batch_pipeline(
            pipeline_input,
            batch_symbols,
            batch_index=selected + 1,
            total_batches=len(batches),
            capture_state_root=capture_state_root,
        )
        result = run_kiwoom_ka10081_capture_and_train(
            batch_pipeline,
            environment=environment,
            token_store_root=token_store_root,
            training_output_root=training_output_root,
            training_handoff_mode=training_handoff_mode,
            requested_template_ids=requested_template_ids,
            asset_liquidity_profile=asset_liquidity_profile,
            strategy_families=strategy_families,
            search_mode=search_mode,
            walk_forward_mode=walk_forward_mode,
            promotion_profile=promotion_profile,
            fill_policy=fill_policy,
            direction=direction,
            request_sleep_seconds=request_sleep_seconds,
            symbol_sleep_seconds=symbol_sleep_seconds,
            max_symbols_per_run=max_symbols_per_run,
            stop_on_provider_limit=stop_on_provider_limit,
            resume_from_capture_state=resume_from_capture_state,
            reuse_existing_raw_lake=reuse_existing_raw_lake or resume_all,
            allow_training_on_partial_capture=allow_training_on_partial_capture,
            backfill_cache_gaps=backfill_cache_gaps or bool(resume_from_capture_state),
            max_backfill_pages_per_symbol=max_backfill_pages_per_symbol,
            prefer_full_coverage_training=prefer_full_coverage_training,
        )
        result.update(
            {
                "total_requested_symbols": len(symbols),
                "batch_size": batch_size,
                "batch_index": selected + 1,
                "batch_count": len(batches),
                "batch_symbols": batch_symbols,
                "next_resume_command": _next_resume_command(
                    capture_state_path=result.get("capture_state_path"),
                    symbols=symbols,
                    symbols_file=symbols_file,
                    batch_size=batch_size,
                    batch_index=selected + 1,
                )
                if result.get("can_resume")
                else None,
                "capture_state_root": str(validate_safe_local_root(capture_state_root)) if capture_state_root else result.get("capture_state_root"),
            }
        )
        batch_results.append(result)
        if result.get("provider_limit_hit"):
            break
    final = batch_results[-1]
    if len(batch_results) > 1:
        final = dict(final)
        final["batch_results"] = batch_results
    return final
