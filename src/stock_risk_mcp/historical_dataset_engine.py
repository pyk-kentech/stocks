from __future__ import annotations

import csv
import json
from pathlib import Path

from stock_risk_mcp.historical_dataset_guard import (
    validate_historical_dataset_feature_outcome_boundary,
    validate_historical_dataset_metadata_safety,
)
from stock_risk_mcp.historical_dataset_models import (
    HistoricalDatasetAssemblyInput,
    HistoricalDatasetExportManifest,
    HistoricalDatasetFeatureBlock,
    HistoricalDatasetGapCategory,
    HistoricalDatasetGapEntry,
    HistoricalDatasetOutcomeBlock,
    HistoricalDatasetQualityReport,
    HistoricalDatasetRecord,
    HistoricalDatasetSafetyReport,
)


FEATURE_SCHEMA_VERSION = "5.4-HISTORICAL-DATASET-FEATURE-BLOCK"
OUTCOME_SCHEMA_VERSION = "5.4-HISTORICAL-DATASET-OUTCOME-BLOCK"


def build_historical_dataset_assembly(
    dataset_input: HistoricalDatasetAssemblyInput,
) -> HistoricalDatasetAssemblyInput:
    scanner_before = dataset_input.scanner_replay_input.model_dump(mode="json")
    gap_entries: list[HistoricalDatasetGapEntry] = []
    warnings: list[str] = []
    records: list[HistoricalDatasetRecord] = []

    replay_windows = {window.window_id: window for window in dataset_input.replay_window_bundle.windows}
    outcome_windows = {
        window.window_id: window for window in dataset_input.historical_outcome_observation_input.observation_windows
    }
    stream_events = {event.replay_event_id: event for event in dataset_input.replay_event_stream.events}
    labels_by_metric_set = {
        label.metric_set_id: label for label in dataset_input.historical_outcome_observation_input.label_report.labels
    }
    scanner_context = dataset_input.scanner_replay_input.replay_context
    candidate_seeds = list(dataset_input.scanner_replay_input.candidate_seeds)
    metric_sets = list(dataset_input.historical_outcome_observation_input.metric_sets)

    if not replay_windows:
        gap_entries.append(
            _gap_entry(
                dataset_input,
                "missing-replay-window",
                HistoricalDatasetGapCategory.DATASET_MISSING_REPLAY_WINDOW,
                "BLOCKING",
                "missing replay window",
            )
        )
    if not metric_sets:
        gap_entries.append(
            _gap_entry(
                dataset_input,
                "missing-outcome-observation",
                HistoricalDatasetGapCategory.DATASET_MISSING_OUTCOME_OBSERVATION,
                "BLOCKING",
                "missing outcome observation",
            )
        )
    if scanner_context is None or not getattr(scanner_context, "context_id", None):
        gap_entries.append(
            _gap_entry(
                dataset_input,
                "missing-scanner-context",
                HistoricalDatasetGapCategory.DATASET_MISSING_SCANNER_CONTEXT,
                "BLOCKING",
                "missing scanner context",
            )
        )

    for index, metric_set in enumerate(metric_sets, start=1):
        outcome_window = outcome_windows.get(metric_set.window_id)
        if outcome_window is None:
            gap_entries.append(
                _gap_entry(
                    dataset_input,
                    f"missing-outcome-window-{metric_set.metric_set_id}",
                    HistoricalDatasetGapCategory.DATASET_MISSING_OUTCOME_OBSERVATION,
                    "BLOCKING",
                    f"missing outcome observation window for metric set {metric_set.metric_set_id}",
                )
            )
            continue

        replay_window = replay_windows.get(outcome_window.replay_window_id or "")
        if replay_window is None:
            gap_entries.append(
                _gap_entry(
                    dataset_input,
                    f"missing-replay-window-{metric_set.metric_set_id}",
                    HistoricalDatasetGapCategory.DATASET_MISSING_REPLAY_WINDOW,
                    "BLOCKING",
                    f"missing replay window for metric set {metric_set.metric_set_id}",
                )
            )
            continue

        scanner_seed = next(
            (
                seed
                for seed in candidate_seeds
                if seed.source_window_id == replay_window.window_id
            ),
            None,
        )
        replay_symbol, replay_market = _replay_identity(replay_window.event_ids, stream_events, scanner_seed)

        feature_summary = scanner_context.attached_event_context_summary or "known-at-replay"
        try:
            validate_historical_dataset_feature_outcome_boundary(
                {"feature_block": {"known_event_context_summary": feature_summary or ""}},
                context="historical dataset",
            )
        except ValueError as exc:
            gap_entries.append(
                _gap_entry(
                    dataset_input,
                    f"feature-leakage-{metric_set.metric_set_id}",
                    HistoricalDatasetGapCategory.DATASET_FEATURE_OUTCOME_LEAKAGE_DETECTED,
                    "BLOCKING",
                    str(exc),
                )
            )
            continue

        feature_block = HistoricalDatasetFeatureBlock.model_validate(
            {
                "block_id": f"FEATURE-BLOCK-{index}",
                "replay_context_id": scanner_context.context_id,
                "scanner_replay_input_id": dataset_input.scanner_replay_input.replay_input_id,
                "known_event_context_summary": feature_summary,
                "attached_market_event_count": scanner_context.attached_market_event_count,
                "attached_corporate_event_count": scanner_context.attached_corporate_event_count,
            }
        )
        outcome_block = HistoricalDatasetOutcomeBlock.model_validate(
            {
                "block_id": f"OUTCOME-BLOCK-{index}",
                "outcome_observed_after_anchor": True,
                "outcome_label": (
                    labels_by_metric_set[metric_set.metric_set_id].label_type.value
                    if metric_set.metric_set_id in labels_by_metric_set
                    else None
                ),
                "forward_return_pct": metric_set.forward_return_pct,
                "max_favorable_excursion_pct": metric_set.max_favorable_excursion_pct,
                "max_adverse_excursion_pct": metric_set.max_adverse_excursion_pct,
                "sessions_observed": metric_set.sessions_observed,
                "missing_session_count": metric_set.missing_session_count,
                "early_close_count": metric_set.early_close_count,
            }
        )

        if not replay_window.source_manifest_ids:
            gap_entries.append(
                _gap_entry(
                    dataset_input,
                    f"missing-lineage-{metric_set.metric_set_id}",
                    HistoricalDatasetGapCategory.DATASET_SOURCE_LINEAGE_MISSING,
                    "REPORT_ONLY",
                    f"missing source lineage for replay window {replay_window.window_id}",
                )
            )

        records.append(
            HistoricalDatasetRecord.model_validate(
                {
                    "record_id": f"DATASET-RECORD-{index}",
                    "strategy_track": dataset_input.assembly_config.strategy_track.value,
                    "market_profile_id": replay_window.market_profile_id,
                    "symbol": replay_symbol,
                    "market": replay_market,
                    "replay_session_date": replay_window.session_date.isoformat(),
                    "replay_event_ids": replay_window.event_ids,
                    "replay_window_id": replay_window.window_id,
                    "scanner_replay_candidate_seed_id": scanner_seed.seed_id if scanner_seed is not None else None,
                    "outcome_observation_id": dataset_input.historical_outcome_observation_input.observation_input_id,
                    "feature_block": feature_block.model_dump(mode="json"),
                    "outcome_block": outcome_block.model_dump(mode="json"),
                    "source_manifest_ids": replay_window.source_manifest_ids,
                    "source_audit_record_ids": replay_window.source_audit_record_ids,
                    "provider_provenance_ids": replay_window.provider_provenance_ids,
                }
            )
        )

    validate_historical_dataset_metadata_safety(
        [audit.operator_context for audit in dataset_input.audit_records],
        context="historical dataset",
    )

    if records:
        gap_entries.append(
            _gap_entry(
                dataset_input,
                "record-generated",
                HistoricalDatasetGapCategory.DATASET_RECORD_GENERATED,
                "REPORT_ONLY",
                "historical dataset record generated",
            )
        )
    gap_entries.append(
        _gap_entry(
            dataset_input,
            "report-only",
            HistoricalDatasetGapCategory.DATASET_REPORT_ONLY,
            "REPORT_ONLY",
            "historical dataset assembly remains report-only and non-executable",
        )
    )

    quality_report = _build_quality_report(dataset_input, records, gap_entries, warnings)
    gap_report = _build_gap_report(dataset_input, gap_entries)
    safety_report = HistoricalDatasetSafetyReport.model_validate(dataset_input.safety_report.model_dump(mode="json"))
    export_manifest = _build_export_manifest(dataset_input, records, quality_report, gap_report, safety_report)

    updated = dataset_input.model_copy(
        update={
            "records": records,
            "quality_report": quality_report,
            "gap_report": gap_report,
            "safety_report": safety_report,
            "export_manifest": export_manifest,
        }
    )
    scanner_after = updated.scanner_replay_input.model_dump(mode="json")
    if scanner_before != scanner_after:
        raise ValueError("scanner replay input must not be mutated during dataset assembly")
    return updated


def export_historical_dataset_json(dataset_input: HistoricalDatasetAssemblyInput, output_path) -> None:
    output = _validated_output_path(output_path)
    output.write_text(dataset_input.model_dump_json(indent=2), encoding="utf-8")


def export_historical_dataset_jsonl(dataset_input: HistoricalDatasetAssemblyInput, output_path) -> None:
    output = _validated_output_path(output_path)
    lines = [json.dumps(record.model_dump(mode="json"), ensure_ascii=True) for record in dataset_input.records]
    output.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def export_historical_dataset_csv(dataset_input: HistoricalDatasetAssemblyInput, output_path) -> None:
    output = _validated_output_path(output_path)
    fieldnames = [
        "record_id",
        "strategy_track",
        "market_profile_id",
        "symbol",
        "market",
        "replay_session_date",
        "replay_window_id",
        "scanner_replay_candidate_seed_id",
        "outcome_observation_id",
        "feature_known_event_context_summary",
        "feature_attached_market_event_count",
        "feature_attached_corporate_event_count",
        "outcome_label",
        "outcome_forward_return_pct",
        "outcome_max_favorable_excursion_pct",
        "outcome_max_adverse_excursion_pct",
        "outcome_sessions_observed",
        "outcome_missing_session_count",
        "outcome_early_close_count",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in dataset_input.records:
            writer.writerow(
                {
                    "record_id": record.record_id,
                    "strategy_track": record.strategy_track.value,
                    "market_profile_id": record.market_profile_id,
                    "symbol": record.symbol,
                    "market": record.market,
                    "replay_session_date": record.replay_session_date.isoformat(),
                    "replay_window_id": record.replay_window_id,
                    "scanner_replay_candidate_seed_id": record.scanner_replay_candidate_seed_id or "",
                    "outcome_observation_id": record.outcome_observation_id or "",
                    "feature_known_event_context_summary": record.feature_block.known_event_context_summary or "",
                    "feature_attached_market_event_count": record.feature_block.attached_market_event_count,
                    "feature_attached_corporate_event_count": record.feature_block.attached_corporate_event_count,
                    "outcome_label": record.outcome_block.outcome_label or "",
                    "outcome_forward_return_pct": record.outcome_block.forward_return_pct,
                    "outcome_max_favorable_excursion_pct": record.outcome_block.max_favorable_excursion_pct,
                    "outcome_max_adverse_excursion_pct": record.outcome_block.max_adverse_excursion_pct,
                    "outcome_sessions_observed": record.outcome_block.sessions_observed,
                    "outcome_missing_session_count": record.outcome_block.missing_session_count,
                    "outcome_early_close_count": record.outcome_block.early_close_count,
                }
            )


def _validated_output_path(output_path) -> Path:
    path = Path(output_path)
    lowered = str(path).strip().lower()
    if lowered.endswith(".parquet"):
        raise ValueError("parquet remains unsupported")
    return path


def _replay_identity(event_ids, stream_events, scanner_seed=None):
    for event_id in event_ids:
        event = stream_events.get(event_id)
        if event is not None:
            return event.symbol, event.market
    if scanner_seed is not None:
        return scanner_seed.symbol, scanner_seed.market
    return "UNKNOWN", "UNKNOWN"


def _gap_entry(
    dataset_input: HistoricalDatasetAssemblyInput,
    suffix: str,
    category: HistoricalDatasetGapCategory,
    severity: str,
    message: str,
) -> HistoricalDatasetGapEntry:
    return HistoricalDatasetGapEntry.model_validate(
        {
            "gap_id": f"{dataset_input.assembly_input_id}-{suffix}",
            "gap_category": category.value,
            "severity": severity,
            "message": message,
        }
    )


def _build_quality_report(
    dataset_input: HistoricalDatasetAssemblyInput,
    records: list[HistoricalDatasetRecord],
    gap_entries: list[HistoricalDatasetGapEntry],
    warnings: list[str],
) -> HistoricalDatasetQualityReport:
    return HistoricalDatasetQualityReport.model_validate(
        {
            "quality_report_id": dataset_input.quality_report.quality_report_id,
            "record_count": len(records),
            "valid_record_count": len(records),
            "symbol_count": len({record.symbol for record in records}),
            "market_count": len({record.market for record in records}),
            "missing_lineage_count": sum(
                1 for gap in gap_entries if gap.gap_category == HistoricalDatasetGapCategory.DATASET_SOURCE_LINEAGE_MISSING
            ),
            "missing_feature_count": sum(
                1 for gap in gap_entries if gap.gap_category == HistoricalDatasetGapCategory.DATASET_MISSING_FEATURE_BLOCK
            ),
            "missing_outcome_count": sum(
                1 for gap in gap_entries if gap.gap_category == HistoricalDatasetGapCategory.DATASET_MISSING_OUTCOME_OBSERVATION
            ),
            "leakage_risk_count": sum(
                1
                for gap in gap_entries
                if gap.gap_category == HistoricalDatasetGapCategory.DATASET_FEATURE_OUTCOME_LEAKAGE_DETECTED
            ),
            "safety_blocked_count": sum(1 for gap in gap_entries if gap.severity != "REPORT_ONLY"),
            "warning_count": len(warnings),
            "warnings": warnings,
            "source_manifest_ids": dataset_input.quality_report.source_manifest_ids,
            "source_audit_record_ids": dataset_input.quality_report.source_audit_record_ids,
            "provider_provenance_ids": dataset_input.quality_report.provider_provenance_ids,
        }
    )


def _build_gap_report(
    dataset_input: HistoricalDatasetAssemblyInput,
    gap_entries: list[HistoricalDatasetGapEntry],
):
    blocking_count = sum(1 for gap in gap_entries if gap.severity != "REPORT_ONLY")
    report_only_count = sum(1 for gap in gap_entries if gap.severity == "REPORT_ONLY")
    gap_status = "NO_GAPS" if not gap_entries else ("BLOCKING_GAPS" if blocking_count else "REPORT_ONLY_GAPS")
    return dataset_input.gap_report.model_copy(
        update={
            "gap_status": gap_status,
            "gap_categories": [gap.gap_category for gap in gap_entries if gap.gap_category is not None],
            "blocking_gap_count": blocking_count,
            "report_only_gap_count": report_only_count,
            "gaps": gap_entries,
        }
    )


def _build_export_manifest(
    dataset_input: HistoricalDatasetAssemblyInput,
    records: list[HistoricalDatasetRecord],
    quality_report: HistoricalDatasetQualityReport,
    gap_report,
    safety_report,
) -> HistoricalDatasetExportManifest:
    session_dates = sorted(record.replay_session_date for record in records)
    return HistoricalDatasetExportManifest.model_validate(
        {
            "manifest_id": dataset_input.export_manifest.manifest_id,
            "export_format": dataset_input.assembly_config.export_formats[0],
            "local_output_path": dataset_input.audit_records[0].source_path if dataset_input.audit_records else None,
            "record_count": len(records),
            "symbol_count": len({record.symbol for record in records}),
            "market_count": len({record.market for record in records}),
            "date_range_start": session_dates[0].isoformat() if session_dates else None,
            "date_range_end": session_dates[-1].isoformat() if session_dates else None,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "outcome_schema_version": OUTCOME_SCHEMA_VERSION,
            "quality_report_id": quality_report.quality_report_id,
            "gap_report_id": gap_report.gap_report_id,
            "safety_report_id": safety_report.safety_report_id,
            "export_formats": dataset_input.export_manifest.export_formats,
            "source_manifest_ids": sorted({item for record in records for item in record.source_manifest_ids}),
            "source_audit_record_ids": sorted({item for record in records for item in record.source_audit_record_ids}),
            "provider_provenance_ids": sorted({item for record in records for item in record.provider_provenance_ids}),
        }
    )
