import copy

from stock_risk_mcp.historical_signal_candidate_engine import build_historical_signal_candidate_batch
from stock_risk_mcp.historical_signal_candidate_models import HistoricalSignalCandidateInput
from tests.test_historical_signal_candidate_models import historical_signal_candidate_fixture_payload


def build_input(payload=None):
    return HistoricalSignalCandidateInput.model_validate(payload or historical_signal_candidate_fixture_payload())


def _engine_payload():
    payload = historical_signal_candidate_fixture_payload()
    payload["source_refs"].append(
        {
            "source_ref_id": "historical-signal-source-ref-2",
            "symbol": "000660",
            "timestamp": "2026-06-18T15:30:00+09:00",
            "source_model_id": "HISTORICAL-MODEL-RUN-REPORT-2",
            "source_experiment_id": "HISTORICAL-MODEL-EXPERIMENT-2",
            "source_metrics_report_id": "HISTORICAL-MODEL-METRICS-REPORT-2",
            "source_artifact_manifest_id": "HISTORICAL-MODEL-ARTIFACT-MANIFEST-2",
            "source_risk_review_id": "HISTORICAL-MODEL-RISK-REVIEW-REPORT-2",
            "source_promotion_block_id": "HISTORICAL-MODEL-PROMOTION-BLOCK-REPORT-2",
            "dataset_lineage_id": "DATASET-EXPORT-MANIFEST-2",
            "split_lineage_id": "DATASET-SPLIT-MANIFEST-2",
            "score": 0.42,
            "score_bucket": "MEDIUM",
            "confidence_bucket": "MEDIUM",
            "predicted_outcome_label": "OUTCOME_NEUTRAL",
            "horizon": "T_PLUS_5",
            "feature_schema_version": "5.4-HISTORICAL-DATASET-FEATURE-BLOCK",
            "label_schema_version": "5.4-HISTORICAL-DATASET-OUTCOME-BLOCK",
            "explanation_summary": "Offline observation candidate from second sandbox artifact.",
            "source_manifest_ids": ["MANIFEST-2", "CALENDAR-MANIFEST-2"],
            "source_audit_record_ids": ["AUDIT-2"],
            "provider_provenance_ids": ["PROVENANCE-2"],
            "metadata": {"report_origin": "offline_fixture"},
        }
    )
    return payload


def test_build_historical_signal_candidate_generation_success_path():
    result = build_historical_signal_candidate_batch(build_input(_engine_payload()))

    assert result.candidate_batch.accepted_candidate_count == 2
    assert result.candidate_batch.rejected_candidate_count == 0
    assert len(result.candidate_batch.candidates) == 2


def test_build_historical_signal_candidate_report_generation_success_path():
    result = build_historical_signal_candidate_batch(build_input(_engine_payload()))

    assert result.candidate_report.candidate_count == 2
    assert result.candidate_report.accepted_candidate_count == 2
    assert result.candidate_report.rejected_candidate_count == 0


def test_build_historical_signal_candidate_safety_report_generation_success_path():
    result = build_historical_signal_candidate_batch(build_input(_engine_payload()))

    assert result.safety_report.no_runtime_trading_signal is True
    assert result.safety_report.no_order_candidate is True
    assert result.safety_report.no_paper_trading is True


def test_build_historical_signal_candidate_gap_report_generation_success_path():
    result = build_historical_signal_candidate_batch(build_input(_engine_payload()))

    assert result.gap_report.gap_status in {"NO_GAPS", "REPORT_ONLY_GAPS"}
    assert "SIGNAL_CANDIDATE_REPORT_GENERATED" in result.gap_report.gap_categories


def test_build_historical_signal_candidate_audit_record_generation_success_path():
    result = build_historical_signal_candidate_batch(build_input(_engine_payload()))

    assert result.audit_records
    assert result.audit_records[0].signal_candidate_input_id == result.signal_candidate_input_id


def test_build_historical_signal_candidate_reports_score_bucket_distribution():
    result = build_historical_signal_candidate_batch(build_input(_engine_payload()))

    assert result.candidate_report.score_bucket_distribution["HIGH"] == 1
    assert result.candidate_report.score_bucket_distribution["MEDIUM"] == 1


def test_build_historical_signal_candidate_reports_confidence_bucket_distribution():
    result = build_historical_signal_candidate_batch(build_input(_engine_payload()))

    assert result.candidate_report.confidence_bucket_distribution["HIGH"] == 1
    assert result.candidate_report.confidence_bucket_distribution["MEDIUM"] == 1


def test_build_historical_signal_candidate_reports_outcome_label_distribution():
    result = build_historical_signal_candidate_batch(build_input(_engine_payload()))

    assert result.candidate_report.outcome_label_distribution["OUTCOME_FAVORABLE"] == 1
    assert result.candidate_report.outcome_label_distribution["OUTCOME_NEUTRAL"] == 1


def test_build_historical_signal_candidate_reports_lineage_coverage_summary():
    result = build_historical_signal_candidate_batch(build_input(_engine_payload()))

    assert result.candidate_report.lineage_coverage_summary["complete_lineage_count"] == 2
    assert result.candidate_report.lineage_coverage_summary["missing_lineage_count"] == 0


def test_build_historical_signal_candidate_reports_missing_experiment_ref_gap():
    signal_input = build_input(_engine_payload())
    source_ref = signal_input.source_refs[0].model_copy(update={"source_experiment_id": ""})
    signal_input = signal_input.model_copy(update={"source_refs": [source_ref, signal_input.source_refs[1]]})

    result = build_historical_signal_candidate_batch(signal_input)

    assert any(item["gap_category"] == "SIGNAL_CANDIDATE_MISSING_EXPERIMENT_REF" for item in result.gap_report.gaps)


def test_build_historical_signal_candidate_reports_missing_model_ref_gap():
    signal_input = build_input(_engine_payload())
    source_ref = signal_input.source_refs[0].model_copy(update={"source_model_id": ""})
    signal_input = signal_input.model_copy(update={"source_refs": [source_ref, signal_input.source_refs[1]]})

    result = build_historical_signal_candidate_batch(signal_input)

    assert any(item["gap_category"] == "SIGNAL_CANDIDATE_MISSING_MODEL_REF" for item in result.gap_report.gaps)


def test_build_historical_signal_candidate_reports_missing_metrics_ref_gap():
    signal_input = build_input(_engine_payload())
    source_ref = signal_input.source_refs[0].model_copy(update={"source_metrics_report_id": ""})
    signal_input = signal_input.model_copy(update={"source_refs": [source_ref, signal_input.source_refs[1]]})

    result = build_historical_signal_candidate_batch(signal_input)

    assert any(item["gap_category"] == "SIGNAL_CANDIDATE_MISSING_METRICS_REF" for item in result.gap_report.gaps)


def test_build_historical_signal_candidate_reports_missing_artifact_ref_gap():
    signal_input = build_input(_engine_payload())
    source_ref = signal_input.source_refs[0].model_copy(update={"source_artifact_manifest_id": ""})
    signal_input = signal_input.model_copy(update={"source_refs": [source_ref, signal_input.source_refs[1]]})

    result = build_historical_signal_candidate_batch(signal_input)

    assert any(item["gap_category"] == "SIGNAL_CANDIDATE_MISSING_ARTIFACT_REF" for item in result.gap_report.gaps)


def test_build_historical_signal_candidate_reports_missing_risk_review_ref_gap():
    signal_input = build_input(_engine_payload())
    source_ref = signal_input.source_refs[0].model_copy(update={"source_risk_review_id": ""})
    signal_input = signal_input.model_copy(update={"source_refs": [source_ref, signal_input.source_refs[1]]})

    result = build_historical_signal_candidate_batch(signal_input)

    assert any(item["gap_category"] == "SIGNAL_CANDIDATE_MISSING_RISK_REVIEW_REF" for item in result.gap_report.gaps)


def test_build_historical_signal_candidate_reports_missing_promotion_block_ref_gap():
    signal_input = build_input(_engine_payload())
    source_ref = signal_input.source_refs[0].model_copy(update={"source_promotion_block_id": ""})
    signal_input = signal_input.model_copy(update={"source_refs": [source_ref, signal_input.source_refs[1]]})

    result = build_historical_signal_candidate_batch(signal_input)

    assert any(item["gap_category"] == "SIGNAL_CANDIDATE_MISSING_PROMOTION_BLOCK_REF" for item in result.gap_report.gaps)


def test_build_historical_signal_candidate_reports_missing_dataset_lineage_gap():
    signal_input = build_input(_engine_payload())
    source_ref = signal_input.source_refs[0].model_copy(update={"dataset_lineage_id": ""})
    signal_input = signal_input.model_copy(update={"source_refs": [source_ref, signal_input.source_refs[1]]})

    result = build_historical_signal_candidate_batch(signal_input)

    assert any(item["gap_category"] == "SIGNAL_CANDIDATE_MISSING_DATASET_LINEAGE" for item in result.gap_report.gaps)


def test_build_historical_signal_candidate_reports_missing_split_lineage_gap():
    signal_input = build_input(_engine_payload())
    source_ref = signal_input.source_refs[0].model_copy(update={"split_lineage_id": ""})
    signal_input = signal_input.model_copy(update={"source_refs": [source_ref, signal_input.source_refs[1]]})

    result = build_historical_signal_candidate_batch(signal_input)

    assert any(item["gap_category"] == "SIGNAL_CANDIDATE_MISSING_SPLIT_LINEAGE" for item in result.gap_report.gaps)


def test_build_historical_signal_candidate_rejects_unsafe_metadata():
    signal_input = build_input(_engine_payload())
    source_ref = signal_input.source_refs[0].model_copy(update={"metadata": {"runtime_signal": "unsafe"}})
    signal_input = signal_input.model_copy(update={"source_refs": [source_ref, signal_input.source_refs[1]]})

    result = build_historical_signal_candidate_batch(signal_input)

    assert any(item["gap_category"] == "SIGNAL_CANDIDATE_RUNTIME_SIGNAL_NOT_ALLOWED" for item in result.gap_report.gaps)


def test_build_historical_signal_candidate_rejects_invalid_score():
    signal_input = build_input(_engine_payload())
    source_ref = signal_input.source_refs[0].model_copy(update={"score": 1.5})
    signal_input = signal_input.model_copy(update={"source_refs": [source_ref, signal_input.source_refs[1]]})

    result = build_historical_signal_candidate_batch(signal_input)

    assert any(item["gap_category"] == "SIGNAL_CANDIDATE_INVALID_SCORE" for item in result.gap_report.gaps)


def test_build_historical_signal_candidate_rejects_trading_action_label():
    signal_input = build_input(_engine_payload())
    source_ref = signal_input.source_refs[0].model_copy(update={"predicted_outcome_label": "BUY"})
    signal_input = signal_input.model_copy(update={"source_refs": [source_ref, signal_input.source_refs[1]]})

    result = build_historical_signal_candidate_batch(signal_input)

    assert any(item["gap_category"] == "SIGNAL_CANDIDATE_INVALID_OUTCOME_LABEL" for item in result.gap_report.gaps)


def test_build_historical_signal_candidate_rejects_order_candidate_marker():
    signal_input = build_input(_engine_payload())
    source_ref = signal_input.source_refs[0].model_copy(update={"metadata": {"order_candidate": "unsafe"}})
    signal_input = signal_input.model_copy(update={"source_refs": [source_ref, signal_input.source_refs[1]]})

    result = build_historical_signal_candidate_batch(signal_input)

    assert any(item["gap_category"] == "SIGNAL_CANDIDATE_ORDER_CANDIDATE_NOT_ALLOWED" for item in result.gap_report.gaps)


def test_build_historical_signal_candidate_rejects_paper_trading_marker():
    signal_input = build_input(_engine_payload())
    source_ref = signal_input.source_refs[0].model_copy(update={"metadata": {"paper_trading": "unsafe"}})
    signal_input = signal_input.model_copy(update={"source_refs": [source_ref, signal_input.source_refs[1]]})

    result = build_historical_signal_candidate_batch(signal_input)

    assert any(item["gap_category"] == "SIGNAL_CANDIDATE_PAPER_TRADING_NOT_ALLOWED" for item in result.gap_report.gaps)


def test_build_historical_signal_candidate_rejects_broker_path_marker():
    signal_input = build_input(_engine_payload())
    source_ref = signal_input.source_refs[0].model_copy(update={"metadata": {"broker_path": "unsafe"}})
    signal_input = signal_input.model_copy(update={"source_refs": [source_ref, signal_input.source_refs[1]]})

    result = build_historical_signal_candidate_batch(signal_input)

    assert any(item["gap_category"] == "SIGNAL_CANDIDATE_BROKER_PATH_NOT_ALLOWED" for item in result.gap_report.gaps)


def test_build_historical_signal_candidate_rejects_live_inference_marker():
    signal_input = build_input(_engine_payload())
    source_ref = signal_input.source_refs[0].model_copy(update={"metadata": {"live_inference": "unsafe"}})
    signal_input = signal_input.model_copy(update={"source_refs": [source_ref, signal_input.source_refs[1]]})

    result = build_historical_signal_candidate_batch(signal_input)

    assert any(item["gap_category"] == "SIGNAL_CANDIDATE_LIVE_INFERENCE_NOT_ALLOWED" for item in result.gap_report.gaps)


def test_build_historical_signal_candidate_rejects_deployment_marker():
    signal_input = build_input(_engine_payload())
    source_ref = signal_input.source_refs[0].model_copy(update={"metadata": {"deployment_path": "unsafe"}})
    signal_input = signal_input.model_copy(update={"source_refs": [source_ref, signal_input.source_refs[1]]})

    result = build_historical_signal_candidate_batch(signal_input)

    assert any(item["gap_category"] == "SIGNAL_CANDIDATE_DEPLOYMENT_NOT_ALLOWED" for item in result.gap_report.gaps)
