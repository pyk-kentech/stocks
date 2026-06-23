from __future__ import annotations

import json
import re

from stock_risk_mcp.cnn_fear_greed_client import fetch_cnn_fear_greed_payload
from stock_risk_mcp.cnn_fear_greed_guard import validate_cnn_fear_greed_metadata_safety
from stock_risk_mcp.cnn_fear_greed_models import (
    CNNFearGreedAuditRecord,
    CNNFearGreedCategory,
    CNNFearGreedCollectorConfig,
    CNNFearGreedCollectionMode,
    CNNFearGreedFeatureIntegrationReport,
    CNNFearGreedGapCategory,
    CNNFearGreedGapReport,
    CNNFearGreedHistoryPoint,
    CNNFearGreedHistoryReport,
    CNNFearGreedSnapshot,
    CNNFearGreedSnapshotReport,
    CNNFearGreedSourceHealthReport,
    hash_payload,
    redact_payload,
)


def _category_for_score(score: int | None) -> CNNFearGreedCategory:
    if score is None:
        return CNNFearGreedCategory.UNKNOWN
    if score <= 25:
        return CNNFearGreedCategory.EXTREME_FEAR
    if score <= 45:
        return CNNFearGreedCategory.FEAR
    if score <= 55:
        return CNNFearGreedCategory.NEUTRAL
    if score <= 75:
        return CNNFearGreedCategory.GREED
    return CNNFearGreedCategory.EXTREME_GREED


def _fear_bucket(category: CNNFearGreedCategory) -> str:
    if category in {CNNFearGreedCategory.EXTREME_FEAR, CNNFearGreedCategory.FEAR}:
        return "FEAR"
    if category == CNNFearGreedCategory.NEUTRAL:
        return "NEUTRAL"
    if category in {CNNFearGreedCategory.GREED, CNNFearGreedCategory.EXTREME_GREED}:
        return "GREED"
    return "UNKNOWN"


def _normalize_payload(raw_payload):
    if isinstance(raw_payload, (dict, list)):
        return raw_payload, "cnn-fg-v1"
    text = str(raw_payload).strip()
    try:
        return json.loads(text), "cnn-fg-v1"
    except json.JSONDecodeError:
        score_match = re.search(r'"score"\s*:\s*(\d{1,3})', text)
        label_match = re.search(r'"label"\s*:\s*"([^"]+)"', text)
        if score_match:
            return {
                "score": int(score_match.group(1)),
                "label": label_match.group(1) if label_match else None,
            }, "cnn-fg-html-fallback-v1"
        return {"_raw_text": text}, "cnn-fg-unknown-v1"


def _extract(raw_payload, source_url: str, collection_mode: CNNFearGreedCollectionMode, observed_schema_version: str) -> CNNFearGreedSnapshot:
    score = None
    label = None
    as_of = None
    available_at = None
    component_scores: dict[str, int] = {}
    history_points: list[CNNFearGreedHistoryPoint] = []

    if isinstance(raw_payload, dict):
        score_value = raw_payload.get("score")
        if isinstance(score_value, (int, float)):
            score = int(score_value)
        label = raw_payload.get("label") or raw_payload.get("category") or raw_payload.get("rating")
        as_of = raw_payload.get("as_of")
        available_at = raw_payload.get("available_at") or raw_payload.get("timestamp")
        components = raw_payload.get("components") or {}
        if isinstance(components, dict):
            component_scores = {
                str(key): int(value)
                for key, value in components.items()
                if isinstance(value, (int, float))
            }
        history = raw_payload.get("history") or []
        if isinstance(history, list):
            for item in history:
                if isinstance(item, dict) and item.get("as_of") is not None and isinstance(item.get("score"), (int, float)):
                    history_points.append(
                        CNNFearGreedHistoryPoint(as_of=item["as_of"], score=int(item["score"]))
                    )

    category = _category_for_score(score)
    if isinstance(label, str):
        normalized = label.strip().upper().replace(" ", "_")
        if normalized in CNNFearGreedCategory.__members__:
            category = CNNFearGreedCategory[normalized]

    snapshot = CNNFearGreedSnapshot(
        score=score,
        category=category,
        as_of=as_of,
        available_at=available_at,
        source_url=source_url,
        collection_mode=collection_mode,
        component_scores=component_scores,
        observed_schema_version=observed_schema_version,
        raw_payload_redacted=redact_payload(raw_payload),
    )
    return snapshot, history_points


def run_cnn_fear_greed_collection(
    config: CNNFearGreedCollectorConfig,
    *,
    transport=None,
) -> CNNFearGreedCollectorConfig:
    if config.min_collection_interval_seconds < 3600:
        raise ValueError("low-frequency collection policy requires at least 3600 seconds")
    if config.max_requests_per_run > 1:
        raise ValueError("low-frequency collection policy allows at most one request per run")
    if config.execute_collection or config.acknowledge_collection or config.allow_real_network:
        if not (config.execute_collection and config.acknowledge_collection and config.allow_real_network) and transport is None:
            raise ValueError("real collection requires --execute and --acknowledge-cnn-fear-greed-collection")

    validate_cnn_fear_greed_metadata_safety(
        {"source_url": config.source_url, "mock_payload": config.mock_payload},
        context="cnn fear greed",
    )
    raw_payload, collection_mode = fetch_cnn_fear_greed_payload(config, transport=transport)
    normalized_payload, observed_schema_version = _normalize_payload(raw_payload)
    snapshot, history_points = _extract(
        normalized_payload,
        config.source_url,
        collection_mode,
        observed_schema_version,
    )

    warnings: list[str] = []
    gap_categories = [CNNFearGreedGapCategory.COLLECTION_REPORT_GENERATED]
    status = "HEALTHY"
    if snapshot.score is None:
        warnings.append("schema mismatch detected while parsing cnn fear and greed payload")
        gap_categories.extend(
            [
                CNNFearGreedGapCategory.SCHEMA_MISMATCH,
                CNNFearGreedGapCategory.SOURCE_HEALTH_WARNING,
            ]
        )
        status = "DEGRADED"

    snapshot_report = CNNFearGreedSnapshotReport(
        report_id=f"{config.config_id}-SNAPSHOT-REPORT",
        snapshot=snapshot,
    )
    history_report = CNNFearGreedHistoryReport(
        report_id=f"{config.config_id}-HISTORY-REPORT",
        history_points=history_points,
    )
    feature_integration_report = CNNFearGreedFeatureIntegrationReport(
        report_id=f"{config.config_id}-FEATURE-INTEGRATION-REPORT",
        cnn_fear_greed_score=snapshot.score,
        cnn_fear_greed_category=snapshot.category.value,
        cnn_fear_greed_available_at=snapshot.available_at.isoformat() if snapshot.available_at else None,
        cnn_fear_greed_source_ref=snapshot.source_url,
        sentiment_fear_bucket=_fear_bucket(snapshot.category),
    )
    source_health_report = CNNFearGreedSourceHealthReport(
        report_id=f"{config.config_id}-SOURCE-HEALTH-REPORT",
        status=status,
        schema_mismatch_detected=status == "DEGRADED",
        warning_count=len(warnings),
        warnings=warnings,
    )
    gap_report = CNNFearGreedGapReport(
        gap_report_id=f"{config.config_id}-GAP-REPORT",
        gap_categories=gap_categories,
        warnings=warnings,
    )
    audit_report = CNNFearGreedAuditRecord(
        audit_record_id=f"{config.config_id}-AUDIT-REPORT",
        source_url=config.source_url,
        collection_mode=collection_mode,
        redaction_applied=True,
        contains_secret_material=False,
        raw_payload_sha256=hash_payload(normalized_payload),
    )
    return config.model_copy(
        update={
            "transport_mode": collection_mode,
            "snapshot_report": snapshot_report,
            "history_report": history_report,
            "feature_integration_report": feature_integration_report,
            "source_health_report": source_health_report,
            "gap_report": gap_report,
            "audit_report": audit_report,
        }
    )
