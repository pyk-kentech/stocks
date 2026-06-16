import json

import pytest

from stock_risk_mcp.local_model_decision_report_fixture import load_local_model_benchmark_pack_fixture


def benchmark_report_payload(
    run_id: str,
    candidate_model_id: str = "mock-qwen-7b-q4",
    eligibility_result: str = "ELIGIBLE",
    language_tags: list[str] | None = None,
    domain_tags: list[str] | None = None,
    overall_score: float = 0.85,
):
    return {
        "schema_version": "3.10-local-model-benchmark-report",
        "benchmark_fixture_checksum": f"benchmark-{run_id}",
        "candidate_output_fixture_checksum": f"candidate-{run_id}",
        "run_id": run_id,
        "created_at": "2026-06-17T12:00:00+00:00",
        "evaluations": [
            {
                "candidate_model_id": candidate_model_id,
                "backend_type": "MOCK_LOCAL_RUNTIME",
                "benchmark_id": f"benchmark-{run_id}",
                "eligibility_result": eligibility_result,
                "schema_validity_score": 1.0,
                "safety_score": 1.0,
                "advisory_boundary_score": 1.0,
                "missing_data_awareness_score": 1.0,
                "language_handling_score": 1.0,
                "json_reliability_score": 1.0,
                "hallucination_risk_score": 1.0,
                "local_advisory_suitability_score": 1.0,
                "overall_suitability_score": overall_score,
                "parse_success": True,
                "matched_forbidden_patterns": [],
                "matched_safe_behavior": ["summarize evidence only", "mention uncertainty if stop context is missing"],
                "fail_gate_reasons": [],
                "advisory_only": True,
                "audit_metadata": {
                    "latency_ms": 120,
                    "token_count": 140,
                    "backend_type": "MOCK_LOCAL_RUNTIME",
                    "language_tags": language_tags or ["KOREAN"],
                    "domain_tags": domain_tags or ["TECHNICAL_EVIDENCE"],
                },
            }
        ],
        "rankings": [
            {
                "rank": 1,
                "candidate_model_id": candidate_model_id,
                "benchmark_id": f"benchmark-{run_id}",
                "overall_suitability_score": overall_score,
                "safety_score": 1.0,
                "advisory_boundary_score": 1.0,
                "eligibility_result": eligibility_result,
            }
        ] if eligibility_result == "ELIGIBLE" else [],
        "summary_counts": {
            "total_candidate_outputs": 1,
            "eligible_count": 1 if eligibility_result == "ELIGIBLE" else 0,
            "fail_schema_count": 1 if eligibility_result == "FAIL_SCHEMA" else 0,
            "fail_safety_count": 1 if eligibility_result == "FAIL_SAFETY" else 0,
            "fail_advisory_boundary_count": 1 if eligibility_result == "FAIL_ADVISORY_BOUNDARY" else 0,
            "fail_execution_authority_hallucination_count": 1 if eligibility_result == "FAIL_EXECUTION_AUTHORITY_HALLUCINATION" else 0,
            "fail_real_model_called_count": 1 if eligibility_result == "FAIL_REAL_MODEL_CALLED" else 0,
            "fail_external_network_count": 1 if eligibility_result == "FAIL_EXTERNAL_NETWORK" else 0,
            "fail_cloud_backend_count": 1 if eligibility_result == "FAIL_CLOUD_BACKEND" else 0,
            "fail_model_download_count": 1 if eligibility_result == "FAIL_MODEL_DOWNLOAD" else 0,
            "fail_unsupported_backend_count": 1 if eligibility_result == "FAIL_UNSUPPORTED_BACKEND" else 0,
            "fail_missing_data_awareness_count": 1 if eligibility_result == "FAIL_MISSING_DATA_AWARENESS" else 0,
            "ranked_eligible_count": 1 if eligibility_result == "ELIGIBLE" else 0,
        },
        "metadata_json": {
            "benchmark_offline_only": True,
            "real_model_called": False,
            "external_network_calls": False,
            "cloud_backend_used": False,
            "model_downloaded": False,
            "orders_created": False,
            "order_intents_created": False,
            "order_drafts_created": False,
            "execution_approved": False,
            "gates_bypassed": False,
            "production_policy_changed": False,
        },
    }


def benchmark_pack_fixture_payload(report_files=None):
    return {
        "schema_version": "3.11-local-model-benchmark-pack-fixture",
        "pack_id": "local-model-pack-1",
        "created_at": "2026-06-17T12:00:00+00:00",
        "pack_type": "DECISION_PACK",
        "required_language_tags": ["KOREAN", "ENGLISH", "MIXED"],
        "required_domain_tags": [
            "TECHNICAL_EVIDENCE",
            "RISK_EXPLANATION",
            "MISSING_DATA",
            "ASSUMPTION_CHALLENGE",
        ],
        "benchmark_report_files": report_files or [
            "report_ko.json",
            "report_en.json",
            "report_mixed.json",
        ],
    }


def write(tmp_path, name, value):
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_local_model_benchmark_pack_fixture_loads_valid_schema(tmp_path):
    fixture = load_local_model_benchmark_pack_fixture(write(tmp_path, "local_model_benchmark_pack_fixture.json", benchmark_pack_fixture_payload()))
    assert fixture.pack_type.value == "DECISION_PACK"
    assert fixture.required_language_tags[0].value == "KOREAN"


def test_local_model_benchmark_pack_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_local_model_benchmark_pack_fixture(write(tmp_path, "pack.txt", benchmark_pack_fixture_payload()))


@pytest.mark.parametrize("change", [
    lambda value: value.update(created_at="2026-06-17T12:00:00"),
    lambda value: value.update(pack_type="FREEFORM"),
    lambda value: value.update(required_language_tags=["KOREAN"]),
    lambda value: value.update(required_domain_tags=["TECHNICAL_EVIDENCE"]),
    lambda value: value.update(benchmark_report_files=[]),
])
def test_local_model_benchmark_pack_fixture_rejects_invalid_values(tmp_path, change):
    value = benchmark_pack_fixture_payload()
    change(value)
    with pytest.raises(ValueError):
        load_local_model_benchmark_pack_fixture(write(tmp_path, "local_model_benchmark_pack_fixture.json", value))
