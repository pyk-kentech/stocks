from __future__ import annotations

from stock_risk_mcp.historical_signal_candidate_guard import validate_historical_signal_candidate_metadata_safety
from stock_risk_mcp.historical_signal_candidate_models import (
    HistoricalSignalCandidate,
    HistoricalSignalCandidateGapCategory,
    HistoricalSignalCandidateInput,
    HistoricalSignalCandidateScore,
)


def build_historical_signal_candidate_batch(
    signal_input: HistoricalSignalCandidateInput,
) -> HistoricalSignalCandidateInput:
    gap_entries: list[dict[str, str]] = []
    candidates: list[HistoricalSignalCandidate] = []
    rejected_count = 0

    if not signal_input.source_refs:
        gap_entries.append(_gap("missing-input", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_MISSING_INPUT, "BLOCKING", "missing signal candidate input"))

    for source_ref in signal_input.source_refs:
        failure = False

        critical_refs = (
            ("source_experiment_id", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_MISSING_EXPERIMENT_REF, "missing experiment ref"),
            ("source_model_id", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_MISSING_MODEL_REF, "missing model ref"),
            ("source_metrics_report_id", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_MISSING_METRICS_REF, "missing metrics ref"),
            ("source_artifact_manifest_id", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_MISSING_ARTIFACT_REF, "missing artifact ref"),
            ("source_risk_review_id", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_MISSING_RISK_REVIEW_REF, "missing risk review ref"),
            ("source_promotion_block_id", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_MISSING_PROMOTION_BLOCK_REF, "missing promotion block ref"),
            ("dataset_lineage_id", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_MISSING_DATASET_LINEAGE, "missing dataset lineage"),
            ("split_lineage_id", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_MISSING_SPLIT_LINEAGE, "missing split lineage"),
        )
        for field_name, category, message in critical_refs:
            if not str(getattr(source_ref, field_name, "")).strip():
                gap_entries.append(_gap(f"{source_ref.source_ref_id}-{field_name}", category, "BLOCKING", message))
                failure = True

        try:
            validate_historical_signal_candidate_metadata_safety(
                {"metadata": getattr(source_ref, "metadata", {})},
                context="historical signal candidate",
            )
        except ValueError as exc:
            gap_entries.append(_unsafe_gap(source_ref.source_ref_id, str(exc)))
            failure = True

        try:
            score = HistoricalSignalCandidateScore.model_validate(
                {
                    "score": getattr(source_ref, "score"),
                    "score_bucket": getattr(source_ref, "score_bucket"),
                    "confidence_bucket": getattr(source_ref, "confidence_bucket"),
                    "predicted_outcome_label": getattr(source_ref, "predicted_outcome_label"),
                    "horizon": getattr(source_ref, "horizon"),
                }
            )
        except ValueError as exc:
            gap_entries.append(_score_gap(source_ref.source_ref_id, str(exc)))
            failure = True
            score = None

        if failure:
            rejected_count += 1
            continue

        candidates.append(
            HistoricalSignalCandidate.model_validate(
                {
                    "candidate_id": f"HISTORICAL-SIGNAL-CANDIDATE-{len(candidates) + 1}",
                    "source_ref_id": source_ref.source_ref_id,
                    "symbol": source_ref.symbol,
                    "timestamp": source_ref.timestamp,
                    "source_model_id": source_ref.source_model_id,
                    "source_experiment_id": source_ref.source_experiment_id,
                    "source_metrics_report_id": source_ref.source_metrics_report_id,
                    "source_artifact_manifest_id": source_ref.source_artifact_manifest_id,
                    "source_risk_review_id": source_ref.source_risk_review_id,
                    "source_promotion_block_id": source_ref.source_promotion_block_id,
                    "dataset_lineage_id": source_ref.dataset_lineage_id,
                    "split_lineage_id": source_ref.split_lineage_id,
                    "score": score.model_dump(mode="json"),
                    "feature_schema_version": source_ref.feature_schema_version,
                    "label_schema_version": source_ref.label_schema_version,
                    "explanation_summary": source_ref.explanation_summary,
                    "source_manifest_ids": source_ref.source_manifest_ids,
                    "source_audit_record_ids": source_ref.source_audit_record_ids,
                    "provider_provenance_ids": source_ref.provider_provenance_ids,
                }
            )
        )

    gap_entries.extend(
        [
            _gap("report-generated", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_REPORT_GENERATED, "REPORT_ONLY", "signal candidate report generated"),
            _gap("report-only", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_REPORT_ONLY, "REPORT_ONLY", "signal candidate layer remains report-only"),
            _gap("local-only", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_LOCAL_ONLY, "REPORT_ONLY", "signal candidate layer remains local-only"),
            _gap("offline-only", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_OFFLINE_ONLY, "REPORT_ONLY", "signal candidate layer remains offline-only"),
            _gap("non-executable", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_NON_EXECUTABLE, "REPORT_ONLY", "signal candidate layer remains non-executable"),
        ]
    )

    score_bucket_distribution: dict[str, int] = {}
    confidence_bucket_distribution: dict[str, int] = {}
    outcome_label_distribution: dict[str, int] = {}
    for candidate in candidates:
        _increment(score_bucket_distribution, candidate.score.score_bucket.value)
        _increment(confidence_bucket_distribution, candidate.score.confidence_bucket.value)
        _increment(outcome_label_distribution, candidate.score.predicted_outcome_label)

    lineage_complete = [
        candidate
        for candidate in candidates
        if all(
            [
                candidate.source_experiment_id,
                candidate.source_model_id,
                candidate.source_metrics_report_id,
                candidate.source_artifact_manifest_id,
                candidate.source_risk_review_id,
                candidate.source_promotion_block_id,
                candidate.dataset_lineage_id,
                candidate.split_lineage_id,
            ]
        )
    ]

    gap_counts: dict[str, int] = {}
    for entry in gap_entries:
        _increment(gap_counts, entry["gap_category"])

    safety_report = signal_input.safety_report.model_copy(
        update={
            "blocked_runtime_signal_count": gap_counts.get(HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_RUNTIME_SIGNAL_NOT_ALLOWED.value, 0),
            "blocked_order_candidate_count": gap_counts.get(HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_ORDER_CANDIDATE_NOT_ALLOWED.value, 0),
            "blocked_paper_trading_count": gap_counts.get(HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_PAPER_TRADING_NOT_ALLOWED.value, 0),
            "blocked_live_inference_count": gap_counts.get(HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_LIVE_INFERENCE_NOT_ALLOWED.value, 0),
            "blocked_deployment_count": gap_counts.get(HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_DEPLOYMENT_NOT_ALLOWED.value, 0),
            "blocked_broker_path_count": gap_counts.get(HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_BROKER_PATH_NOT_ALLOWED.value, 0),
        }
    )

    report = signal_input.candidate_report.model_copy(
        update={
            "candidate_count": len(signal_input.source_refs),
            "accepted_candidate_count": len(candidates),
            "rejected_candidate_count": rejected_count,
            "gap_counts": gap_counts,
            "safety_flag_summary": {
                "read_only": True,
                "report_only": True,
                "non_executable": True,
                "local_file_only": True,
                "offline_only": True,
            },
            "score_bucket_distribution": score_bucket_distribution,
            "confidence_bucket_distribution": confidence_bucket_distribution,
            "outcome_label_distribution": outcome_label_distribution,
            "lineage_coverage_summary": {
                "complete_lineage_count": len(lineage_complete),
                "missing_lineage_count": len(candidates) - len(lineage_complete),
            },
            "blocked_execution_summary": {
                "runtime_trading_signal_blocked": True,
                "order_candidate_blocked": True,
                "paper_trading_blocked": True,
                "live_inference_blocked": True,
                "deployment_blocked": True,
            },
        }
    )

    gap_report = signal_input.gap_report.model_copy(
        update={
            "gap_status": _gap_status(gap_entries),
            "gap_categories": [entry["gap_category"] for entry in gap_entries],
            "blocking_gap_count": len([entry for entry in gap_entries if entry["severity"] == "BLOCKING"]),
            "report_only_gap_count": len([entry for entry in gap_entries if entry["severity"] != "BLOCKING"]),
            "gaps": gap_entries,
        }
    )

    batch = signal_input.candidate_batch.model_copy(
        update={
            "candidates": candidates,
            "accepted_candidate_count": len(candidates),
            "rejected_candidate_count": rejected_count,
        }
    )

    return signal_input.model_copy(
        update={
            "candidate_batch": batch,
            "candidate_report": report,
            "safety_report": safety_report,
            "gap_report": gap_report,
            "audit_records": signal_input.audit_records,
        }
    )


def _increment(bucket: dict[str, int], key: str):
    bucket[key] = bucket.get(key, 0) + 1


def _gap_status(gap_entries: list[dict[str, str]]) -> str:
    if any(entry["severity"] == "BLOCKING" for entry in gap_entries):
        return "BLOCKING_GAPS"
    if gap_entries:
        return "REPORT_ONLY_GAPS"
    return "NO_GAPS"


def _gap(gap_id: str, category: HistoricalSignalCandidateGapCategory, severity: str, message: str) -> dict[str, str]:
    return {
        "gap_id": gap_id.upper(),
        "gap_category": category.value,
        "severity": severity,
        "message": message,
    }


def _score_gap(source_ref_id: str, reason: str) -> dict[str, str]:
    lowered = reason.lower()
    if "confidence_bucket" in lowered:
        return _gap(f"{source_ref_id}-invalid-confidence", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_INVALID_CONFIDENCE_BUCKET, "BLOCKING", "invalid confidence bucket")
    if "outcome label" in lowered or "predicted_outcome_label" in lowered:
        return _gap(f"{source_ref_id}-invalid-outcome-label", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_INVALID_OUTCOME_LABEL, "BLOCKING", "invalid outcome label")
    return _gap(f"{source_ref_id}-invalid-score", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_INVALID_SCORE, "BLOCKING", "invalid score")


def _unsafe_gap(source_ref_id: str, reason: str) -> dict[str, str]:
    lowered = reason.lower()
    mapping = (
        ("runtime_signal", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_RUNTIME_SIGNAL_NOT_ALLOWED, "runtime signal not allowed"),
        ("order_candidate", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_ORDER_CANDIDATE_NOT_ALLOWED, "order candidate not allowed"),
        ("buy_sell", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_BUY_SELL_WORDING_NOT_ALLOWED, "buy/sell wording not allowed"),
        ("position", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_POSITION_FIELD_NOT_ALLOWED, "position field not allowed"),
        ("paper_trading", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_PAPER_TRADING_NOT_ALLOWED, "paper trading not allowed"),
        ("broker", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_BROKER_PATH_NOT_ALLOWED, "broker path not allowed"),
        ("live_inference", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_LIVE_INFERENCE_NOT_ALLOWED, "live inference not allowed"),
        ("deployment", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_DEPLOYMENT_NOT_ALLOWED, "deployment not allowed"),
        ("provider", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_PROVIDER_API_NOT_ALLOWED, "provider api not allowed"),
        ("api", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_PROVIDER_API_NOT_ALLOWED, "provider api not allowed"),
        ("network", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_NETWORK_NOT_ALLOWED, "network not allowed"),
        ("cloud_llm", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_CLOUD_LLM_NOT_ALLOWED, "cloud llm not allowed"),
        ("local_llm", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_LOCAL_LLM_RUNTIME_NOT_ALLOWED, "local llm runtime not allowed"),
        ("live_prod", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_LIVE_PROD_NOT_ALLOWED, "live/prod not allowed"),
        ("parquet", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_PARQUET_NOT_ALLOWED, "parquet not allowed"),
        ("order", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_ORDER_FIELD_NOT_ALLOWED, "order field not allowed"),
        ("credential", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_ORDER_FIELD_NOT_ALLOWED, "credentials not allowed"),
    )
    for needle, category, message in mapping:
        if needle in lowered:
            return _gap(f"{source_ref_id}-{needle}", category, "BLOCKING", message)
    return _gap(f"{source_ref_id}-unsafe", HistoricalSignalCandidateGapCategory.SIGNAL_CANDIDATE_ORDER_FIELD_NOT_ALLOWED, "BLOCKING", "unsafe metadata not allowed")
