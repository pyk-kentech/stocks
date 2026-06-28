from __future__ import annotations

import csv
import json
from pathlib import Path

from stock_risk_mcp.historical_market_data_models import HistoricalChartRequestSpec, HistoricalMarketDataPipelineInput
from stock_risk_mcp.historical_market_data_guard import validate_safe_local_root
from stock_risk_mcp.kiwoom_capture_and_train_runner import run_kiwoom_ka10081_capture_and_train
from stock_risk_mcp.kiwoom_oauth_models import KiwoomEnvironment


def _watchlist_progress_path(capture_state_root: str | None, pipeline_input: HistoricalMarketDataPipelineInput) -> Path:
    base = validate_safe_local_root(capture_state_root or pipeline_input.store_root)
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{pipeline_input.dataset_id.lower()}-watchlist-state.json"


def _load_watchlist_progress(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_watchlist_progress(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


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
    resume_all: bool = False,
    watchlist_progress_path: str | None = None,
) -> str | None:
    if not capture_state_path and not watchlist_progress_path:
        return None
    parts = [
        "python3.11 -m stock_risk_mcp.cli kiwoom-ka10081-capture-and-train-run",
        f"--batch-size {batch_size}",
        f"--batch-index {batch_index}",
        "--reuse-existing-raw-lake",
        "--backfill-cache-gaps",
        "--prefer-full-coverage-training",
    ]
    if resume_all:
        parts.append("--resume-all")
    if capture_state_path:
        parts.append(f"--resume-from-capture-state {capture_state_path}")
    if symbols:
        parts.append(f"--symbols {','.join(symbols)}")
    if symbols_file:
        parts.append(f"--symbols-file {symbols_file}")
    if watchlist_progress_path:
        parts.append(f"--capture-state-root {Path(watchlist_progress_path).parent}")
    return " ".join(parts)


def _aggregate_ranking_reports(
    *,
    training_output_root: str,
    watchlist_dataset_id: str,
    batch_results: list[dict[str, object]],
) -> str | None:
    rows: list[dict[str, object]] = []
    for batch in batch_results:
        ranking_path = batch.get("ranking_report_path")
        if not ranking_path or not Path(ranking_path).exists():
            continue
        payload = json.loads(Path(ranking_path).read_text(encoding="utf-8"))
        for row in payload.get("rows", []):
            merged = dict(row)
            merged["batch_index"] = batch.get("batch_index")
            rows.append(merged)
    rows.sort(key=lambda item: (-float(item.get("score") or 0.0), int(item.get("batch_index") or 0), str(item.get("symbol") or ""), str(item.get("candidate_id") or "")))
    for index, row in enumerate(rows, start=1):
        row["global_rank"] = index
    output_root = validate_safe_local_root(training_output_root) / watchlist_dataset_id.lower() / "reports"
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / "offline_strategy_watchlist_ranking.json"
    output_path.write_text(json.dumps({"watchlist_dataset_id": watchlist_dataset_id, "rows": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(output_path)


def _global_status_sets(per_symbol_global_status: dict[str, str]) -> tuple[list[str], list[str], list[str], list[str], list[str]]:
    completed = sorted(symbol for symbol, status in per_symbol_global_status.items() if status == "COMPLETED")
    full = sorted(symbol for symbol, status in per_symbol_global_status.items() if status == "FULL_COVERAGE")
    partial = sorted(symbol for symbol, status in per_symbol_global_status.items() if status == "PARTIAL")
    skipped = sorted(symbol for symbol, status in per_symbol_global_status.items() if status == "SKIPPED")
    failed = sorted(symbol for symbol, status in per_symbol_global_status.items() if status == "FAILED")
    pending = sorted(symbol for symbol, status in per_symbol_global_status.items() if status == "PENDING")
    return completed, full, partial, skipped, failed, pending


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
    watchlist_dataset_id = f"{pipeline_input.dataset_id}-WATCHLIST"
    progress_path = _watchlist_progress_path(capture_state_root, pipeline_input)
    progress = _load_watchlist_progress(progress_path) or {}
    per_symbol_global_status: dict[str, str] = {
        symbol: str(progress.get("per_symbol_global_status", {}).get(symbol) or "PENDING")
        for symbol in symbols
    }
    if resume_all:
        pending_or_retry = [
            symbol
            for symbol in symbols
            if per_symbol_global_status.get(symbol) not in {"FULL_COVERAGE", "COMPLETED"}
        ]
        batches = split_symbol_batches(pending_or_retry, batch_size)
    else:
        batches = split_symbol_batches(symbols, batch_size)
    if max_batches and max_batches > 0:
        batches = batches[: max_batches]
    if not batches:
        raise ValueError("no symbols resolved for capture")
    selected_indices = list(range(len(batches))) if resume_all else [max(batch_index - 1, 0)]
    batch_results: list[dict[str, object]] = []
    capture_state_paths_by_batch: dict[str, str] = dict(progress.get("capture_state_paths_by_batch", {}))
    ranking_report_paths_by_batch: dict[str, str] = dict(progress.get("ranking_report_paths_by_batch", {}))
    provider_limit_hit_count = int(progress.get("provider_limit_hit_count") or 0)
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
                    resume_all=resume_all,
                    watchlist_progress_path=str(progress_path),
                )
                if result.get("can_resume")
                else None,
                "capture_state_root": str(validate_safe_local_root(capture_state_root)) if capture_state_root else result.get("capture_state_root"),
            }
        )
        batch_key = f"{selected + 1:03d}"
        if result.get("capture_state_path"):
            capture_state_paths_by_batch[batch_key] = str(result["capture_state_path"])
        if result.get("ranking_report_path"):
            ranking_report_paths_by_batch[batch_key] = str(result["ranking_report_path"])
        if result.get("provider_limit_hit"):
            provider_limit_hit_count += 1
        for symbol in result.get("full_coverage_symbols", []):
            per_symbol_global_status[symbol] = "FULL_COVERAGE"
        for symbol in result.get("completed_symbols", []):
            if per_symbol_global_status.get(symbol) != "FULL_COVERAGE":
                per_symbol_global_status[symbol] = "COMPLETED"
        for symbol in result.get("partial_symbols", []):
            if per_symbol_global_status.get(symbol) not in {"FULL_COVERAGE", "COMPLETED"}:
                per_symbol_global_status[symbol] = "PARTIAL"
        for symbol in result.get("failed_symbols", []):
            if per_symbol_global_status.get(symbol) not in {"FULL_COVERAGE", "COMPLETED"}:
                per_symbol_global_status[symbol] = "FAILED"
        for symbol in result.get("skipped_symbols", []):
            if per_symbol_global_status.get(symbol) not in {"FULL_COVERAGE", "COMPLETED"}:
                per_symbol_global_status[symbol] = "SKIPPED"
        batch_results.append(result)
        completed, full, partial, skipped, failed, pending = _global_status_sets(per_symbol_global_status)
        next_pending_symbols = [symbol for symbol in symbols if symbol in pending or symbol in skipped or symbol in partial]
        next_batch_symbols = split_symbol_batches(next_pending_symbols, batch_size)[0] if next_pending_symbols else []
        watchlist_progress = {
            "watchlist_run_id": f"{watchlist_dataset_id}-PROGRESS",
            "symbols_file": symbols_file,
            "requested_symbols": symbols,
            "total_requested_symbols": len(symbols),
            "batch_size": batch_size,
            "batches": split_symbol_batches(symbols, batch_size),
            "per_symbol_global_status": per_symbol_global_status,
            "completed_symbols": completed,
            "full_coverage_symbols": full,
            "partial_symbols": partial,
            "skipped_symbols": skipped,
            "failed_symbols": failed,
            "pending_symbols": pending,
            "provider_limit_hit_count": provider_limit_hit_count,
            "last_completed_batch_index": selected + 1,
            "next_batch_index": 1 if resume_all and next_pending_symbols else min(selected + 2, len(split_symbol_batches(symbols, batch_size))),
            "next_pending_symbols": next_pending_symbols,
            "next_resume_command": _next_resume_command(
                capture_state_path=result.get("capture_state_path"),
                symbols=symbols,
                symbols_file=symbols_file,
                batch_size=batch_size,
                batch_index=1 if resume_all and next_pending_symbols else min(selected + 2, len(split_symbol_batches(symbols, batch_size))),
                resume_all=resume_all,
                watchlist_progress_path=str(progress_path),
            )
            if next_pending_symbols
            else None,
            "capture_state_paths_by_batch": capture_state_paths_by_batch,
            "ranking_report_paths_by_batch": ranking_report_paths_by_batch,
            "aggregate_ranking_report_path": None,
            "can_resume_all": bool(next_pending_symbols),
        }
        _write_watchlist_progress(progress_path, watchlist_progress)
        if result.get("provider_limit_hit"):
            break
    final = batch_results[-1]
    completed, full, partial, skipped, failed, pending = _global_status_sets(per_symbol_global_status)
    aggregate_ranking_report_path = _aggregate_ranking_reports(
        training_output_root=training_output_root,
        watchlist_dataset_id=watchlist_dataset_id,
        batch_results=batch_results,
    )
    watchlist_status = "WATCHLIST_FAILED"
    if len(full) == len(symbols):
        if any(result.get("backfilled_symbols") for result in batch_results):
            watchlist_status = "WATCHLIST_COMPLETED_WITH_BACKFILL"
        elif any(result.get("reused_from_cache") for result in batch_results):
            watchlist_status = "WATCHLIST_COMPLETED_WITH_CACHE"
        else:
            watchlist_status = "WATCHLIST_COMPLETED"
    elif any(result.get("provider_limit_hit") for result in batch_results):
        watchlist_status = "WATCHLIST_PARTIAL_PROVIDER_LIMIT"
    elif pending or skipped or partial:
        watchlist_status = "WATCHLIST_PARTIAL_PENDING"
    if len(batch_results) > 1:
        final = dict(final)
        final["batch_results"] = batch_results
    final = dict(final)
    final["batch_status"] = final.get("status")
    final["watchlist_status"] = watchlist_status
    final["resume_all"] = resume_all
    final["watchlist_progress_path"] = str(progress_path)
    final["pending_symbols_before_run"] = list(progress.get("pending_symbols", symbols))
    final["pending_symbols_after_run"] = pending
    final["completed_symbols_global"] = completed
    final["full_coverage_symbols_global"] = full
    final["skipped_symbols_global"] = skipped
    final["failed_symbols_global"] = failed
    final["watchlist_completed_symbols"] = completed
    final["watchlist_pending_symbols"] = pending
    final["watchlist_failed_symbols"] = failed
    final["current_batch_ranking_report_path"] = final.get("ranking_report_path")
    final["aggregate_ranking_report_path"] = aggregate_ranking_report_path
    final["capture_state_paths_by_batch"] = capture_state_paths_by_batch
    final["ranking_report_paths_by_batch"] = ranking_report_paths_by_batch
    final["next_resume_command"] = _next_resume_command(
        capture_state_path=final.get("capture_state_path"),
        symbols=symbols,
        symbols_file=symbols_file,
        batch_size=batch_size,
        batch_index=1 if resume_all and pending else min((final.get("batch_index") or 1) + 1, len(split_symbol_batches(symbols, batch_size))),
        resume_all=resume_all,
        watchlist_progress_path=str(progress_path),
    ) if (pending or skipped or partial) else None
    watchlist_progress = {
        "watchlist_run_id": f"{watchlist_dataset_id}-PROGRESS",
        "symbols_file": symbols_file,
        "requested_symbols": symbols,
        "total_requested_symbols": len(symbols),
        "batch_size": batch_size,
        "batches": split_symbol_batches(symbols, batch_size),
        "per_symbol_global_status": per_symbol_global_status,
        "completed_symbols": completed,
        "full_coverage_symbols": full,
        "partial_symbols": partial,
        "skipped_symbols": skipped,
        "failed_symbols": failed,
        "pending_symbols": pending,
        "provider_limit_hit_count": provider_limit_hit_count,
        "last_completed_batch_index": int(final.get("batch_index") or 1),
        "next_batch_index": 1 if resume_all and pending else min((final.get("batch_index") or 1) + 1, len(split_symbol_batches(symbols, batch_size))),
        "next_pending_symbols": [symbol for symbol in symbols if symbol in pending or symbol in skipped or symbol in partial],
        "next_resume_command": final["next_resume_command"],
        "capture_state_paths_by_batch": capture_state_paths_by_batch,
        "ranking_report_paths_by_batch": ranking_report_paths_by_batch,
        "aggregate_ranking_report_path": aggregate_ranking_report_path,
        "can_resume_all": bool(pending or skipped or partial),
    }
    _write_watchlist_progress(progress_path, watchlist_progress)
    return final
