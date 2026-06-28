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


def _batch_label(batch_index_one_based: int) -> str:
    return f"{batch_index_one_based:03d}"


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


def _build_batch_execution_plan(
    symbols: list[str],
    *,
    batch_size: int,
    batch_index: int,
    max_batches: int | None,
    resume_all: bool,
    per_symbol_global_status: dict[str, str],
) -> tuple[list[list[str]], list[dict[str, object]], list[str]]:
    original_batches = split_symbol_batches(symbols, batch_size)
    retry_queue_before_run = [
        symbol for symbol in symbols if per_symbol_global_status.get(symbol) not in {"FULL_COVERAGE", "COMPLETED"}
    ]
    if max_batches and max_batches > 0:
        original_batches = original_batches[: max_batches]
    if not original_batches:
        return [], [], retry_queue_before_run
    plan: list[dict[str, object]] = []
    if resume_all:
        for zero_based, full_batch_symbols in enumerate(original_batches):
            unresolved_symbols = [
                symbol for symbol in full_batch_symbols if per_symbol_global_status.get(symbol) not in {"FULL_COVERAGE", "COMPLETED"}
            ]
            if not unresolved_symbols:
                continue
            one_based = zero_based + 1
            plan.append(
                {
                    "batch_index_input": one_based,
                    "batch_label": _batch_label(one_based),
                    "batch_position_zero_based": zero_based,
                    "batch_symbols": list(full_batch_symbols),
                    "retry_symbols": list(unresolved_symbols),
                }
            )
    else:
        selected_zero_based = max(batch_index - 1, 0)
        if selected_zero_based < len(original_batches):
            one_based = selected_zero_based + 1
            plan.append(
                {
                    "batch_index_input": one_based,
                    "batch_label": _batch_label(one_based),
                    "batch_position_zero_based": selected_zero_based,
                    "batch_symbols": list(original_batches[selected_zero_based]),
                    "retry_symbols": list(original_batches[selected_zero_based]),
                }
            )
    return original_batches, plan, retry_queue_before_run


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
    ranking_report_paths_by_batch: dict[str, str],
    requested_symbols: list[str],
    batches: list[list[str]],
    per_symbol_global_status: dict[str, str],
) -> tuple[str | None, str | None]:
    rows: list[dict[str, object]] = []
    candidate_parameter_summary_by_family: dict[str, set[str]] = {}
    symbol_to_batch_index = {
        symbol: index
        for index, batch_symbols in enumerate(batches, start=1)
        for symbol in batch_symbols
    }
    for batch_label, ranking_path in sorted(ranking_report_paths_by_batch.items()):
        if not ranking_path or not Path(ranking_path).exists():
            continue
        payload = json.loads(Path(ranking_path).read_text(encoding="utf-8"))
        for family, summaries in payload.get("candidate_parameter_summary_by_family", {}).items():
            candidate_parameter_summary_by_family.setdefault(str(family), set()).update(str(item) for item in summaries)
        for row in payload.get("rows", []):
            merged = dict(row)
            merged["batch_index"] = int(batch_label)
            merged["batch_label"] = batch_label
            merged["ranking_available"] = True
            rows.append(merged)
    rows.sort(key=lambda item: (-float(item.get("score") or 0.0), int(item.get("batch_index") or 0), str(item.get("symbol") or ""), str(item.get("candidate_id") or "")))
    for index, row in enumerate(rows, start=1):
        row["global_rank"] = index
    ranked_symbols = {str(row.get("symbol") or "") for row in rows}
    for symbol in requested_symbols:
        if symbol in ranked_symbols:
            continue
        batch_index = symbol_to_batch_index.get(symbol)
        status = per_symbol_global_status.get(symbol) or "UNKNOWN"
        rows.append(
            {
                "symbol": symbol,
                "batch_index": batch_index,
                "batch_label": _batch_label(batch_index) if batch_index is not None else None,
                "strategy_family": None,
                "internal_family": None,
                "candidate_id": None,
                "parameter_set_id": None,
                "parameter_summary": None,
                "promotion_status": "NO_RANKING_AVAILABLE",
                "rejection_reasons": [],
                "actual_trade_count": None,
                "signal_count_before_filters": None,
                "entry_signal_count": None,
                "exit_signal_count": None,
                "profit_factor": None,
                "win_rate": None,
                "max_drawdown": None,
                "total_return": None,
                "average_trade_return": None,
                "coverage_status": status,
                "coverage_basis": None,
                "rank_score": None,
                "rank_score_components": {},
                "score": None,
                "global_rank": None,
                "ranking_available": False,
                "ranking_missing_reason": f"{status}_NO_TRAINING_RANKING",
            }
        )
    output_root = validate_safe_local_root(training_output_root) / watchlist_dataset_id.lower() / "reports"
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / "offline_strategy_watchlist_ranking.json"
    output_path.write_text(
        json.dumps(
            {
                "watchlist_dataset_id": watchlist_dataset_id,
                "candidate_parameter_summary_by_family": {
                    family: sorted(values) for family, values in sorted(candidate_parameter_summary_by_family.items())
                },
                "rows": rows,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    summary_path = output_root / "offline_strategy_watchlist_ranking_summary.json"
    available_rows = [row for row in rows if row.get("ranking_available", True)]
    best_candidate_by_symbol: dict[str, dict[str, object]] = {}
    best_candidate_by_family: dict[str, dict[str, object]] = {}
    best_candidate_by_symbol_and_family: dict[str, dict[str, object]] = {}
    rejected_count_by_reason: dict[str, int] = {}
    candidate_count_by_symbol: dict[str, int] = {}
    candidate_count_by_family: dict[str, int] = {}
    no_trades_count = 0
    zero_entry_signal_count = 0
    zero_entry_signal_count_by_family: dict[str, int] = {}
    missing_indicator_count_by_family: dict[str, int] = {}
    best_diagnostic_candidate_by_symbol: dict[str, dict[str, object]] = {}
    best_diagnostic_candidate_by_family: dict[str, dict[str, object]] = {}
    for row in available_rows:
        symbol = str(row.get("symbol") or "")
        family = str(row.get("strategy_family") or "")
        if symbol:
            candidate_count_by_symbol[symbol] = candidate_count_by_symbol.get(symbol, 0) + 1
        if family:
            candidate_count_by_family[family] = candidate_count_by_family.get(family, 0) + 1
            missing_indicator_count_by_family[family] = missing_indicator_count_by_family.get(family, 0) + len(row.get("missing_indicator_columns") or [])
        if int(row.get("entry_signal_count") or 0) == 0:
            zero_entry_signal_count += 1
            zero_entry_signal_count_by_family[family] = zero_entry_signal_count_by_family.get(family, 0) + 1
        for reason in row.get("rejection_reasons", []):
            rejected_count_by_reason[str(reason)] = rejected_count_by_reason.get(str(reason), 0) + 1
            if str(reason) == "NO_TRADES":
                no_trades_count += 1
        compact = {
            "symbol": symbol,
            "strategy_family": family,
            "candidate_id": row.get("candidate_id"),
            "parameter_set_id": row.get("parameter_set_id"),
            "parameter_summary": row.get("parameter_summary"),
            "promotion_status": row.get("promotion_status"),
            "rank_score": row.get("rank_score"),
        }
        if symbol and (symbol not in best_candidate_by_symbol or float(row.get("rank_score") or -10**9) > float(best_candidate_by_symbol[symbol].get("rank_score") or -10**9)):
            best_candidate_by_symbol[symbol] = compact
        if family and (family not in best_candidate_by_family or float(row.get("rank_score") or -10**9) > float(best_candidate_by_family[family].get("rank_score") or -10**9)):
            best_candidate_by_family[family] = compact
        key = f"{symbol}|{family}"
        if symbol and family and (key not in best_candidate_by_symbol_and_family or float(row.get("rank_score") or -10**9) > float(best_candidate_by_symbol_and_family[key].get("rank_score") or -10**9)):
            best_candidate_by_symbol_and_family[key] = compact
        diagnostic_score = (
            float(row.get("signal_count_before_filters") or 0) * 10.0
            + float(row.get("entry_signal_count") or 0) * 20.0
            + float(row.get("final_entry_condition_count") or 0) * 5.0
            - float(len(row.get("missing_indicator_columns") or [])) * 5.0
        )
        if symbol and (symbol not in best_diagnostic_candidate_by_symbol or diagnostic_score > float(best_diagnostic_candidate_by_symbol[symbol].get("diagnostic_score") or -10**9)):
            best_diagnostic_candidate_by_symbol[symbol] = {**compact, "diagnostic_score": diagnostic_score}
        if family and (family not in best_diagnostic_candidate_by_family or diagnostic_score > float(best_diagnostic_candidate_by_family[family].get("diagnostic_score") or -10**9)):
            best_diagnostic_candidate_by_family[family] = {**compact, "diagnostic_score": diagnostic_score}
    summary_path.write_text(
        json.dumps(
            {
                "watchlist_dataset_id": watchlist_dataset_id,
                "best_candidate_by_symbol": best_candidate_by_symbol,
                "best_candidate_by_family": best_candidate_by_family,
                "best_candidate_by_symbol_and_family": best_candidate_by_symbol_and_family,
                "best_diagnostic_candidate_by_symbol": best_diagnostic_candidate_by_symbol,
                "best_diagnostic_candidate_by_family": best_diagnostic_candidate_by_family,
                "rejected_count_by_reason": dict(sorted(rejected_count_by_reason.items())),
                "no_trades_count": no_trades_count,
                "zero_entry_signal_count": zero_entry_signal_count,
                "zero_entry_signal_count_by_family": dict(sorted(zero_entry_signal_count_by_family.items())),
                "missing_indicator_count_by_family": dict(sorted(missing_indicator_count_by_family.items())),
                "candidate_count_by_symbol": dict(sorted(candidate_count_by_symbol.items())),
                "candidate_count_by_family": dict(sorted(candidate_count_by_family.items())),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return str(output_path), str(summary_path)


def _global_status_sets(per_symbol_global_status: dict[str, str]) -> tuple[list[str], list[str], list[str], list[str], list[str]]:
    completed = sorted(symbol for symbol, status in per_symbol_global_status.items() if status == "COMPLETED")
    full = sorted(symbol for symbol, status in per_symbol_global_status.items() if status == "FULL_COVERAGE")
    partial = sorted(symbol for symbol, status in per_symbol_global_status.items() if status == "PARTIAL")
    skipped = sorted(symbol for symbol, status in per_symbol_global_status.items() if status == "SKIPPED")
    failed = sorted(symbol for symbol, status in per_symbol_global_status.items() if status == "FAILED")
    pending = sorted(symbol for symbol, status in per_symbol_global_status.items() if status == "PENDING")
    return completed, full, partial, skipped, failed, pending


def _find_next_retry_batch(batches: list[list[str]], per_symbol_global_status: dict[str, str]) -> dict[str, object] | None:
    for zero_based, batch_symbols in enumerate(batches):
        unresolved = [symbol for symbol in batch_symbols if per_symbol_global_status.get(symbol) not in {"FULL_COVERAGE", "COMPLETED"}]
        if unresolved:
            one_based = zero_based + 1
            return {
                "next_retry_batch_label": _batch_label(one_based),
                "next_retry_batch_index": one_based,
                "next_retry_batch_position_zero_based": zero_based,
                "next_retry_symbols": unresolved,
                "next_retry_batch_symbols": list(batch_symbols),
            }
    return None


def _contains_secret_marker(value: object) -> bool:
    markers = ("APPKEY", "SECRETKEY", "AUTHORIZATION", "BEARER ", "TOKEN", "SECRET")
    if isinstance(value, dict):
        return any(_contains_secret_marker(item) for item in value.values()) or any(_contains_secret_marker(key) for key in value.keys())
    if isinstance(value, list):
        return any(_contains_secret_marker(item) for item in value)
    if isinstance(value, str):
        upper = value.upper()
        if "<REDACTED>" in upper:
            return False
        return any(marker in upper for marker in markers)
    return False


def _validate_batch_identity(expected_symbols: list[str], capture_state_path: str | None) -> tuple[str, list[str], str | None]:
    if not capture_state_path:
        return "BATCH_IDENTITY_ERROR", [], "MISSING_CAPTURE_STATE_PATH"
    path = Path(capture_state_path)
    if not path.exists():
        return "BATCH_IDENTITY_ERROR", [], "CAPTURE_STATE_PATH_MISSING"
    payload = json.loads(path.read_text(encoding="utf-8"))
    capture_state_symbols = [str(item).strip().upper() for item in payload.get("requested_symbols", [])]
    if capture_state_symbols != expected_symbols:
        return "BATCH_IDENTITY_ERROR", capture_state_symbols, "CAPTURE_STATE_SYMBOLS_MISMATCH"
    return "BATCH_IDENTITY_OK", capture_state_symbols, None


def _validate_coverage_consistency(batch_results: list[dict[str, object]], per_symbol_global_status: dict[str, str]) -> tuple[str, list[str]]:
    errors: list[str] = []
    for batch in batch_results:
        full_symbols = set(batch.get("symbols_with_full_coverage", []))
        partial_symbols = set(batch.get("symbols_with_partial_coverage", []))
        for item in batch.get("symbol_results", []):
            symbol = str(item.get("requested_symbol") or "")
            coverage_status = str(item.get("cache_coverage_status") or "")
            post_backfill_status = str(item.get("post_backfill_coverage_status") or "")
            trading_ratio = item.get("trading_coverage_ratio")
            if (
                trading_ratio is not None
                and float(trading_ratio) < 0.999999
                and coverage_status == "TRADING_COVERAGE_GAP"
                and post_backfill_status == "FULL_TRADING_COVERAGE"
            ):
                errors.append(f"{symbol}:PARTIAL_RATIO_REPORTED_AS_FULL")
            if symbol in partial_symbols and post_backfill_status == "FULL_TRADING_COVERAGE":
                errors.append(f"{symbol}:PARTIAL_SET_WITH_FULL_STATUS")
            if post_backfill_status == "FULL_TRADING_COVERAGE" and symbol not in full_symbols and per_symbol_global_status.get(symbol) != "FULL_COVERAGE":
                errors.append(f"{symbol}:FULL_STATUS_NOT_REFLECTED_IN_FULL_COVERAGE_SET")
    return ("COVERAGE_CONSISTENCY_OK" if not errors else "COVERAGE_CONSISTENCY_ERROR"), errors


def _validate_watchlist_ledger(
    *,
    ledger_payload: dict[str, object],
    requested_symbols: list[str],
    batches: list[list[str]],
    per_symbol_global_status: dict[str, str],
) -> tuple[str, str, str, list[str]]:
    errors: list[str] = []
    accounted = (
        set(ledger_payload.get("completed_symbols", []))
        | set(ledger_payload.get("full_coverage_symbols", []))
        | set(ledger_payload.get("partial_symbols", []))
        | set(ledger_payload.get("skipped_symbols", []))
        | set(ledger_payload.get("failed_symbols", []))
        | set(ledger_payload.get("pending_symbols", []))
    )
    accounting_status = "ACCOUNTING_OK"
    if accounted != set(requested_symbols):
        accounting_status = "ACCOUNTING_ERROR"
        errors.append("REQUESTED_SYMBOL_ACCOUNTING_MISMATCH")
    batch_identity_status = "BATCH_IDENTITY_OK"
    capture_state_paths = dict(ledger_payload.get("capture_state_paths_by_batch", {}))
    for index, batch_symbols in enumerate(batches, start=1):
        path = capture_state_paths.get(_batch_label(index))
        if not path:
            continue
        identity_status, _symbols, reason = _validate_batch_identity(batch_symbols, path)
        if identity_status != "BATCH_IDENTITY_OK":
            batch_identity_status = "BATCH_IDENTITY_ERROR"
            errors.append(f"{_batch_label(index)}:{reason}")
    ranking_paths = dict(ledger_payload.get("ranking_report_paths_by_batch", {}))
    for path in capture_state_paths.values():
        if path and not Path(path).exists():
            errors.append(f"MISSING_CAPTURE_STATE_PATH:{path}")
    for path in ranking_paths.values():
        if path and not Path(path).exists():
            errors.append(f"MISSING_RANKING_REPORT_PATH:{path}")
    aggregate_path = ledger_payload.get("aggregate_ranking_report_path")
    if aggregate_path and not Path(str(aggregate_path)).exists():
        errors.append(f"MISSING_AGGREGATE_RANKING_REPORT_PATH:{aggregate_path}")
    if _contains_secret_marker(ledger_payload):
        errors.append("SECRET_MARKER_PRESENT")
    completed, full, partial, skipped, failed, pending = _global_status_sets(per_symbol_global_status)
    if ledger_payload.get("completed_symbols", []) != completed:
        errors.append("COMPLETED_SYMBOLS_BUCKET_MISMATCH")
    if ledger_payload.get("full_coverage_symbols", []) != full:
        errors.append("FULL_COVERAGE_SYMBOLS_BUCKET_MISMATCH")
    if ledger_payload.get("partial_symbols", []) != partial:
        errors.append("PARTIAL_SYMBOLS_BUCKET_MISMATCH")
    if ledger_payload.get("skipped_symbols", []) != skipped:
        errors.append("SKIPPED_SYMBOLS_BUCKET_MISMATCH")
    if ledger_payload.get("failed_symbols", []) != failed:
        errors.append("FAILED_SYMBOLS_BUCKET_MISMATCH")
    if ledger_payload.get("pending_symbols", []) != pending:
        errors.append("PENDING_SYMBOLS_BUCKET_MISMATCH")
    ledger_validation_status = "LEDGER_VALIDATION_OK" if not errors else "LEDGER_VALIDATION_ERROR"
    return accounting_status, batch_identity_status, ledger_validation_status, errors


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
    rate_limit_profile: str | None = "CONSERVATIVE",
    max_tr_per_second: int | None = None,
    max_tr_per_minute: int | None = None,
    max_tr_per_hour: int | None = None,
    min_request_interval_seconds: float | None = None,
    tr_rate_ledger_path: str | None = None,
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
    batches, execution_plan, retry_queue_before_run = _build_batch_execution_plan(
        symbols,
        batch_size=batch_size,
        batch_index=batch_index,
        max_batches=max_batches,
        resume_all=resume_all,
        per_symbol_global_status=per_symbol_global_status,
    )
    if not batches or not execution_plan:
        raise ValueError("no symbols resolved for capture")
    batch_results: list[dict[str, object]] = []
    capture_state_paths_by_batch: dict[str, str] = dict(progress.get("capture_state_paths_by_batch", {}))
    ranking_report_paths_by_batch: dict[str, str] = dict(progress.get("ranking_report_paths_by_batch", {}))
    provider_limit_hit_count = int(progress.get("provider_limit_hit_count") or 0)
    for plan in execution_plan:
        batch_symbols = list(plan["batch_symbols"])
        selected = int(plan["batch_position_zero_based"])
        batch_label = str(plan["batch_label"])
        batch_resume_state_path = str(capture_state_paths_by_batch.get(batch_label) or resume_from_capture_state or "")
        batch_pipeline = build_batch_pipeline(
            pipeline_input,
            batch_symbols,
            batch_index=int(plan["batch_index_input"]),
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
            rate_limit_profile=rate_limit_profile,
            max_tr_per_second=max_tr_per_second,
            max_tr_per_minute=max_tr_per_minute,
            max_tr_per_hour=max_tr_per_hour,
            min_request_interval_seconds=min_request_interval_seconds,
            tr_rate_ledger_path=tr_rate_ledger_path,
            max_symbols_per_run=max_symbols_per_run,
            stop_on_provider_limit=stop_on_provider_limit,
            resume_from_capture_state=batch_resume_state_path or None,
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
                "batch_index": int(plan["batch_index_input"]),
                "batch_index_input": int(plan["batch_index_input"]),
                "batch_label": batch_label,
                "batch_position_zero_based": selected,
                "batch_count": len(batches),
                "batch_symbols": batch_symbols,
                "retry_symbols": list(plan["retry_symbols"]),
                "next_resume_command": _next_resume_command(
                    capture_state_path=result.get("capture_state_path"),
                    symbols=symbols,
                    symbols_file=symbols_file,
                    batch_size=batch_size,
                    batch_index=int(plan["batch_index_input"]),
                    resume_all=resume_all,
                    watchlist_progress_path=str(progress_path),
                )
                if result.get("can_resume")
                else None,
                "capture_state_root": str(validate_safe_local_root(capture_state_root)) if capture_state_root else result.get("capture_state_root"),
            }
        )
        identity_status, capture_state_batch_symbols, identity_error_reason = _validate_batch_identity(batch_symbols, result.get("capture_state_path"))
        result["capture_state_batch_symbols"] = capture_state_batch_symbols
        result["batch_identity_status"] = identity_status
        result["batch_identity_error_reason"] = identity_error_reason
        batch_key = batch_label
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
        next_retry = _find_next_retry_batch(batches, per_symbol_global_status)
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
            "last_completed_batch_index": int(plan["batch_index_input"]),
            "next_batch_index": next_retry["next_retry_batch_index"] if next_retry else None,
            "next_pending_symbols": next_pending_symbols,
            "retry_queue_before_run": retry_queue_before_run,
            "next_retry_batch_label": next_retry["next_retry_batch_label"] if next_retry else None,
            "next_retry_batch_index": next_retry["next_retry_batch_index"] if next_retry else None,
            "next_retry_symbols": next_retry["next_retry_symbols"] if next_retry else [],
            "next_resume_command": _next_resume_command(
                capture_state_path=capture_state_paths_by_batch.get(str(next_retry["next_retry_batch_label"])) if next_retry else None,
                symbols=symbols,
                symbols_file=symbols_file,
                batch_size=batch_size,
                batch_index=int(next_retry["next_retry_batch_index"]) if next_retry else int(plan["batch_index_input"]),
                resume_all=resume_all,
                watchlist_progress_path=str(progress_path),
            )
            if next_retry
            else None,
            "capture_state_paths_by_batch": capture_state_paths_by_batch,
            "ranking_report_paths_by_batch": ranking_report_paths_by_batch,
            "aggregate_ranking_report_path": None,
            "can_resume_all": bool(next_retry),
        }
        accounting_status, watchlist_batch_identity_status, ledger_validation_status, ledger_validation_errors = _validate_watchlist_ledger(
            ledger_payload=watchlist_progress,
            requested_symbols=symbols,
            batches=batches,
            per_symbol_global_status=per_symbol_global_status,
        )
        watchlist_progress["accounting_status"] = accounting_status
        watchlist_progress["batch_identity_status"] = "BATCH_IDENTITY_ERROR" if (
            watchlist_batch_identity_status == "BATCH_IDENTITY_ERROR" or identity_status == "BATCH_IDENTITY_ERROR"
        ) else "BATCH_IDENTITY_OK"
        watchlist_progress["coverage_consistency_status"] = "COVERAGE_CONSISTENCY_OK"
        watchlist_progress["ledger_validation_status"] = ledger_validation_status
        watchlist_progress["ledger_validation_errors"] = ledger_validation_errors
        _write_watchlist_progress(progress_path, watchlist_progress)
        if result.get("provider_limit_hit"):
            break
    final = batch_results[-1]
    completed, full, partial, skipped, failed, pending = _global_status_sets(per_symbol_global_status)
    coverage_consistency_status, coverage_consistency_errors = _validate_coverage_consistency(batch_results, per_symbol_global_status)
    aggregate_ranking_report_path, aggregate_ranking_summary_path = _aggregate_ranking_reports(
        training_output_root=training_output_root,
        watchlist_dataset_id=watchlist_dataset_id,
        ranking_report_paths_by_batch=ranking_report_paths_by_batch,
        requested_symbols=symbols,
        batches=batches,
        per_symbol_global_status=per_symbol_global_status,
    )
    next_retry = _find_next_retry_batch(batches, per_symbol_global_status)
    watchlist_status = "WATCHLIST_FAILED"
    if coverage_consistency_status == "COVERAGE_CONSISTENCY_ERROR":
        watchlist_status = "WATCHLIST_FAILED"
    elif len(full) == len(symbols):
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
    final["pending_symbols_before_run"] = retry_queue_before_run if resume_all else list(progress.get("pending_symbols", symbols))
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
    final["aggregate_ranking_summary_path"] = aggregate_ranking_summary_path
    final["capture_state_paths_by_batch"] = capture_state_paths_by_batch
    final["ranking_report_paths_by_batch"] = ranking_report_paths_by_batch
    final["retry_queue_before_run"] = retry_queue_before_run
    final["next_retry_batch_label"] = next_retry["next_retry_batch_label"] if next_retry else None
    final["next_retry_batch_index"] = next_retry["next_retry_batch_index"] if next_retry else None
    final["next_retry_symbols"] = next_retry["next_retry_symbols"] if next_retry else []
    final["coverage_consistency_status"] = coverage_consistency_status
    final["coverage_consistency_errors"] = coverage_consistency_errors
    final["next_resume_command"] = _next_resume_command(
        capture_state_path=capture_state_paths_by_batch.get(str(next_retry["next_retry_batch_label"])) if next_retry else None,
        symbols=symbols,
        symbols_file=symbols_file,
        batch_size=batch_size,
        batch_index=int(next_retry["next_retry_batch_index"]) if next_retry else min((final.get("batch_index") or 1) + 1, len(batches)),
        resume_all=resume_all,
        watchlist_progress_path=str(progress_path),
    ) if next_retry else None
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
        "next_batch_index": next_retry["next_retry_batch_index"] if next_retry else None,
        "next_pending_symbols": [symbol for symbol in symbols if symbol in pending or symbol in skipped or symbol in partial],
        "retry_queue_before_run": retry_queue_before_run,
        "next_retry_batch_label": next_retry["next_retry_batch_label"] if next_retry else None,
        "next_retry_batch_index": next_retry["next_retry_batch_index"] if next_retry else None,
        "next_retry_symbols": next_retry["next_retry_symbols"] if next_retry else [],
        "next_resume_command": final["next_resume_command"],
        "capture_state_paths_by_batch": capture_state_paths_by_batch,
        "ranking_report_paths_by_batch": ranking_report_paths_by_batch,
        "aggregate_ranking_report_path": aggregate_ranking_report_path,
        "aggregate_ranking_summary_path": aggregate_ranking_summary_path,
        "can_resume_all": bool(next_retry),
    }
    accounting_status, batch_identity_status, ledger_validation_status, ledger_validation_errors = _validate_watchlist_ledger(
        ledger_payload=watchlist_progress,
        requested_symbols=symbols,
        batches=batches,
        per_symbol_global_status=per_symbol_global_status,
    )
    watchlist_progress["accounting_status"] = accounting_status
    watchlist_progress["batch_identity_status"] = batch_identity_status
    watchlist_progress["coverage_consistency_status"] = coverage_consistency_status
    watchlist_progress["ledger_validation_status"] = ledger_validation_status
    watchlist_progress["ledger_validation_errors"] = coverage_consistency_errors + ledger_validation_errors
    final["accounting_status"] = accounting_status
    final["batch_identity_status"] = batch_identity_status
    final["ledger_validation_status"] = ledger_validation_status
    final["ledger_validation_errors"] = coverage_consistency_errors + ledger_validation_errors
    _write_watchlist_progress(progress_path, watchlist_progress)
    return final
