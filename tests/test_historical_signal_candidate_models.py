import json

import pytest

from stock_risk_mcp.historical_signal_candidate_fixture import load_historical_signal_candidate_fixture
from stock_risk_mcp.historical_signal_candidate_guard import validate_historical_signal_candidate_metadata_safety
from stock_risk_mcp.historical_signal_candidate_models import (
    HistoricalSignalCandidate,
    HistoricalSignalCandidateAuditRecord,
    HistoricalSignalCandidateBatch,
    HistoricalSignalCandidateConfig,
    HistoricalSignalCandidateGapCategory,
    HistoricalSignalCandidateGapReport,
    HistoricalSignalCandidateInput,
    HistoricalSignalCandidateReport,
    HistoricalSignalCandidateSafetyReport,
    HistoricalSignalCandidateScore,
    HistoricalSignalCandidateSourceRef,
)


def historical_signal_candidate_fixture_payload():
    return {
        "schema_version": "5.9-historical-signal-candidate-input",
        "signal_candidate_input_id": "historical-signal-candidate-input-1",
        "signal_candidate_config": {
            "config_id": "historical-signal-candidate-config-1",
            "strategy_track": "DOMESTIC_KR",
        },
        "source_refs": [
            {
                "source_ref_id": "historical-signal-source-ref-1",
                "symbol": "005930",
                "timestamp": "2026-06-18T15:30:00+09:00",
                "source_model_id": "HISTORICAL-MODEL-RUN-REPORT-1",
                "source_experiment_id": "HISTORICAL-MODEL-EXPERIMENT-1",
                "source_metrics_report_id": "HISTORICAL-MODEL-METRICS-REPORT-1",
                "source_artifact_manifest_id": "HISTORICAL-MODEL-ARTIFACT-MANIFEST-1",
                "source_risk_review_id": "HISTORICAL-MODEL-RISK-REVIEW-REPORT-1",
                "source_promotion_block_id": "HISTORICAL-MODEL-PROMOTION-BLOCK-REPORT-1",
                "dataset_lineage_id": "DATASET-EXPORT-MANIFEST-1",
                "split_lineage_id": "DATASET-SPLIT-MANIFEST-1",
                "score": 0.76,
                "score_bucket": "HIGH",
                "confidence_bucket": "HIGH",
                "predicted_outcome_label": "OUTCOME_FAVORABLE",
                "horizon": "T_PLUS_5",
                "feature_schema_version": "5.4-HISTORICAL-DATASET-FEATURE-BLOCK",
                "label_schema_version": "5.4-HISTORICAL-DATASET-OUTCOME-BLOCK",
                "explanation_summary": "Offline observation candidate from sandbox metrics.",
                "source_manifest_ids": ["MANIFEST-1", "CALENDAR-MANIFEST-1"],
                "source_audit_record_ids": ["AUDIT-1"],
                "provider_provenance_ids": ["PROVENANCE-1"],
                "metadata": {"report_origin": "offline_fixture"},
            }
        ],
        "candidate_batch": {
            "candidate_batch_id": "historical-signal-candidate-batch-1",
            "signal_candidate_input_id": "historical-signal-candidate-input-1",
            "candidates": [],
            "accepted_candidate_count": 0,
            "rejected_candidate_count": 0,
        },
        "candidate_report": {
            "candidate_report_id": "historical-signal-candidate-report-1",
            "signal_candidate_input_id": "historical-signal-candidate-input-1",
            "candidate_count": 0,
            "accepted_candidate_count": 0,
            "rejected_candidate_count": 0,
            "gap_counts": {},
            "safety_flag_summary": {},
            "score_bucket_distribution": {},
            "confidence_bucket_distribution": {},
            "outcome_label_distribution": {},
            "lineage_coverage_summary": {},
            "blocked_execution_summary": {},
        },
        "safety_report": {
            "safety_report_id": "historical-signal-candidate-safety-report-1",
            "signal_candidate_input_id": "historical-signal-candidate-input-1",
            "blocked_runtime_signal_count": 0,
            "blocked_order_candidate_count": 0,
            "blocked_paper_trading_count": 0,
            "blocked_live_inference_count": 0,
            "blocked_deployment_count": 0,
            "blocked_broker_path_count": 0,
        },
        "gap_report": {
            "gap_report_id": "historical-signal-candidate-gap-report-1",
            "signal_candidate_input_id": "historical-signal-candidate-input-1",
            "gap_status": "NO_GAPS",
            "gap_categories": [],
            "blocking_gap_count": 0,
            "report_only_gap_count": 0,
            "gaps": [],
        },
        "audit_records": [
            {
                "audit_record_id": "historical-signal-candidate-audit-record-1",
                "signal_candidate_input_id": "historical-signal-candidate-input-1",
                "created_at": "2026-06-18T18:30:00+09:00",
                "operator_context": "TEST",
                "source_path": "fixtures/historical/historical_signal_candidate_fixture.json",
                "source_manifest_ids": ["MANIFEST-1", "CALENDAR-MANIFEST-1"],
                "source_audit_record_ids": ["AUDIT-1"],
                "provider_provenance_ids": ["PROVENANCE-1"],
            }
        ],
    }


def test_historical_signal_candidate_models_accept_local_fixture_only_inputs(tmp_path):
    fixture_file = tmp_path / "historical_signal_candidate_fixture.json"
    fixture_file.write_text(json.dumps(historical_signal_candidate_fixture_payload()), encoding="utf-8")

    result = load_historical_signal_candidate_fixture(fixture_file)

    assert isinstance(result, HistoricalSignalCandidateInput)
    assert isinstance(result.signal_candidate_config, HistoricalSignalCandidateConfig)
    assert result.signal_candidate_config.no_paper_trading is True


def test_historical_signal_candidate_models_require_safety_flags():
    payload = historical_signal_candidate_fixture_payload()
    payload["signal_candidate_config"]["no_deployment"] = False

    with pytest.raises(ValueError, match="no_deployment"):
        HistoricalSignalCandidateInput.model_validate(payload)


def test_historical_signal_candidate_source_ref_construction():
    signal_input = HistoricalSignalCandidateInput.model_validate(historical_signal_candidate_fixture_payload())

    assert isinstance(signal_input.source_refs[0], HistoricalSignalCandidateSourceRef)


def test_historical_signal_candidate_score_construction():
    signal_input = HistoricalSignalCandidateInput.model_validate(historical_signal_candidate_fixture_payload())
    source_ref = signal_input.source_refs[0]
    score = HistoricalSignalCandidateScore.model_validate(
        {
            "score": source_ref.score,
            "score_bucket": source_ref.score_bucket,
            "confidence_bucket": source_ref.confidence_bucket,
            "predicted_outcome_label": source_ref.predicted_outcome_label,
            "horizon": source_ref.horizon,
        }
    )

    assert score.score == pytest.approx(0.76)
    assert score.score_bucket == "HIGH"


@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_historical_signal_candidate_score_rejects_out_of_range_values(value):
    with pytest.raises(ValueError, match="score"):
        HistoricalSignalCandidateScore.model_validate(
            {
                "score": value,
                "score_bucket": "HIGH",
                "confidence_bucket": "HIGH",
                "predicted_outcome_label": "OUTCOME_FAVORABLE",
                "horizon": "T_PLUS_5",
            }
        )


def test_historical_signal_candidate_construction():
    signal_input = HistoricalSignalCandidateInput.model_validate(historical_signal_candidate_fixture_payload())
    source_ref = signal_input.source_refs[0]
    candidate = HistoricalSignalCandidate.model_validate(
        {
            "candidate_id": "historical-signal-candidate-1",
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
            "score": {
                "score": source_ref.score,
                "score_bucket": source_ref.score_bucket,
                "confidence_bucket": source_ref.confidence_bucket,
                "predicted_outcome_label": source_ref.predicted_outcome_label,
                "horizon": source_ref.horizon,
            },
            "feature_schema_version": source_ref.feature_schema_version,
            "label_schema_version": source_ref.label_schema_version,
            "explanation_summary": source_ref.explanation_summary,
        }
    )

    assert isinstance(candidate, HistoricalSignalCandidate)
    assert candidate.no_runtime_trading_signal is True


def test_historical_signal_candidate_batch_construction():
    signal_input = HistoricalSignalCandidateInput.model_validate(historical_signal_candidate_fixture_payload())
    assert isinstance(signal_input.candidate_batch, HistoricalSignalCandidateBatch)


def test_historical_signal_candidate_report_construction():
    signal_input = HistoricalSignalCandidateInput.model_validate(historical_signal_candidate_fixture_payload())
    assert isinstance(signal_input.candidate_report, HistoricalSignalCandidateReport)


def test_historical_signal_candidate_safety_report_construction():
    signal_input = HistoricalSignalCandidateInput.model_validate(historical_signal_candidate_fixture_payload())
    assert isinstance(signal_input.safety_report, HistoricalSignalCandidateSafetyReport)


def test_historical_signal_candidate_gap_report_construction():
    signal_input = HistoricalSignalCandidateInput.model_validate(historical_signal_candidate_fixture_payload())
    assert isinstance(signal_input.gap_report, HistoricalSignalCandidateGapReport)


def test_historical_signal_candidate_audit_record_construction():
    signal_input = HistoricalSignalCandidateInput.model_validate(historical_signal_candidate_fixture_payload())
    assert isinstance(signal_input.audit_records[0], HistoricalSignalCandidateAuditRecord)


def test_historical_signal_candidate_fixture_loader_wraps_source_path_in_error(tmp_path):
    fixture_file = tmp_path / "historical_signal_candidate_fixture.txt"
    fixture_file.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match=str(fixture_file)):
        load_historical_signal_candidate_fixture(fixture_file)


def test_historical_signal_candidate_fixture_rejects_parquet():
    payload = historical_signal_candidate_fixture_payload()
    payload["audit_records"][0]["source_path"] = "fixtures/historical/historical_signal_candidate_fixture.parquet"

    with pytest.raises(ValueError, match="parquet"):
        HistoricalSignalCandidateInput.model_validate(payload)


@pytest.mark.parametrize("label", ["BUY", "SELL", "ENTRY", "EXIT"])
def test_historical_signal_candidate_rejects_trading_action_labels(label):
    payload = historical_signal_candidate_fixture_payload()
    payload["source_refs"][0]["predicted_outcome_label"] = label

    with pytest.raises(ValueError, match="outcome label"):
        HistoricalSignalCandidateInput.model_validate(payload)


@pytest.mark.parametrize(
    ("metadata", "match"),
    [
        ({"runtime_signal": "yes"}, "runtime_signal"),
        ({"order_candidate": "yes"}, "order_candidate"),
        ({"order_intent": "yes"}, "order"),
        ({"position_size": "100"}, "position"),
        ({"paper_trading": "yes"}, "paper_trading"),
        ({"broker_account": "yes"}, "broker"),
        ({"live_inference": "yes"}, "live_inference"),
        ({"deployment_path": "registry/model"}, "deployment"),
        ({"network_provider": "tcp://local"}, "provider"),
        ({"cloud_llm": "gemini"}, "cloud_llm"),
        ({"local_llm_runtime": "ollama"}, "local_llm"),
        ({"live_prod": "prod"}, "live_prod"),
        ({"api_token": "secret"}, "credential"),
    ],
)
def test_historical_signal_candidate_guard_rejects_unsafe_markers(metadata, match):
    with pytest.raises(ValueError, match=match):
        validate_historical_signal_candidate_metadata_safety(metadata, context="historical signal candidate")


def test_historical_signal_candidate_gap_categories_exist():
    expected = {
        "SIGNAL_CANDIDATE_REPORT_GENERATED",
        "SIGNAL_CANDIDATE_REPORT_ONLY",
        "SIGNAL_CANDIDATE_LOCAL_ONLY",
        "SIGNAL_CANDIDATE_OFFLINE_ONLY",
        "SIGNAL_CANDIDATE_NON_EXECUTABLE",
        "SIGNAL_CANDIDATE_MISSING_INPUT",
        "SIGNAL_CANDIDATE_MISSING_EXPERIMENT_REF",
        "SIGNAL_CANDIDATE_MISSING_MODEL_REF",
        "SIGNAL_CANDIDATE_MISSING_METRICS_REF",
        "SIGNAL_CANDIDATE_MISSING_ARTIFACT_REF",
        "SIGNAL_CANDIDATE_MISSING_RISK_REVIEW_REF",
        "SIGNAL_CANDIDATE_MISSING_PROMOTION_BLOCK_REF",
        "SIGNAL_CANDIDATE_MISSING_DATASET_LINEAGE",
        "SIGNAL_CANDIDATE_MISSING_SPLIT_LINEAGE",
        "SIGNAL_CANDIDATE_INVALID_SCORE",
        "SIGNAL_CANDIDATE_INVALID_CONFIDENCE_BUCKET",
        "SIGNAL_CANDIDATE_INVALID_OUTCOME_LABEL",
        "SIGNAL_CANDIDATE_RUNTIME_SIGNAL_NOT_ALLOWED",
        "SIGNAL_CANDIDATE_ORDER_CANDIDATE_NOT_ALLOWED",
        "SIGNAL_CANDIDATE_BUY_SELL_WORDING_NOT_ALLOWED",
        "SIGNAL_CANDIDATE_ORDER_FIELD_NOT_ALLOWED",
        "SIGNAL_CANDIDATE_POSITION_FIELD_NOT_ALLOWED",
        "SIGNAL_CANDIDATE_PAPER_TRADING_NOT_ALLOWED",
        "SIGNAL_CANDIDATE_BROKER_PATH_NOT_ALLOWED",
        "SIGNAL_CANDIDATE_LIVE_INFERENCE_NOT_ALLOWED",
        "SIGNAL_CANDIDATE_DEPLOYMENT_NOT_ALLOWED",
        "SIGNAL_CANDIDATE_NETWORK_NOT_ALLOWED",
        "SIGNAL_CANDIDATE_PROVIDER_API_NOT_ALLOWED",
        "SIGNAL_CANDIDATE_CLOUD_LLM_NOT_ALLOWED",
        "SIGNAL_CANDIDATE_LOCAL_LLM_RUNTIME_NOT_ALLOWED",
        "SIGNAL_CANDIDATE_LIVE_PROD_NOT_ALLOWED",
        "SIGNAL_CANDIDATE_PARQUET_NOT_ALLOWED",
    }

    assert expected.issubset({item.value for item in HistoricalSignalCandidateGapCategory})
