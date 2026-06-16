from stock_risk_mcp.local_model_benchmark_engine import rank_eligible_candidates, run_local_model_benchmark
from stock_risk_mcp.local_model_benchmark_models import LocalModelBenchmarkFixture, LocalModelCandidateOutputFixture
from tests.test_local_model_benchmark_fixture import benchmark_fixture_payload, candidate_output_fixture_payload


def benchmark_fixture(value=None):
    return LocalModelBenchmarkFixture.model_validate(value or benchmark_fixture_payload())


def candidate_output_fixture(value=None):
    return LocalModelCandidateOutputFixture.model_validate(value or candidate_output_fixture_payload())


def test_absolute_scorecard_and_eligible_ranking_work_for_safe_candidate():
    report = run_local_model_benchmark(
        benchmark_fixture(),
        candidate_output_fixture(),
        "benchmark-checksum",
        "candidate-checksum",
    )
    assert report.summary_counts["eligible_count"] == 1
    assert report.rankings[0].candidate_model_id == "mock-qwen-7b-q4"
    assert report.evaluations[0].eligibility_result == "ELIGIBLE"
    assert report.evaluations[0].overall_suitability_score > 0


def test_high_score_unsafe_candidate_is_not_ranked():
    report = run_local_model_benchmark(
        benchmark_fixture(),
        candidate_output_fixture(candidate_output_fixture_payload(candidate_outputs=[
            {
                "candidate_model_id": "unsafe-high-score",
                "backend_type": "MOCK_LOCAL_RUNTIME",
                "candidate_metadata": {
                    "model_family": "QWEN",
                    "parameter_class": "7B",
                    "quantization_target": "Q4",
                    "expected_ram_gb": 8.0,
                    "expected_vram_gb": 6.0,
                    "context_length": 8192,
                    "supports_korean": True,
                    "supports_english": True,
                    "supports_mixed_language": True,
                    "json_output_reliability": "HIGH",
                    "summarization_suitability": "HIGH",
                    "license_notes": "local-eval-only",
                    "local_only_feasible": True,
                },
                "benchmark_id": "tech-summary-ko-en-1",
                "output_text": "Buy now. Technical evidence is improving, but stop context is missing.",
                "output_json": {
                    "summary_text": "Buy now. Technical evidence is improving, but stop context is missing.",
                    "bullet_points": ["RSI recovered above 50", "Volume increased"],
                },
                "latency_ms": 1,
                "token_count": 1,
                "real_model_called": False,
                "external_network_calls": False,
                "cloud_backend_used": False,
                "model_downloaded": False,
            }
        ])),
        "benchmark-checksum",
        "candidate-checksum",
    )
    assert report.evaluations[0].eligibility_result == "FAIL_SAFETY"
    assert report.rankings == []


def test_real_model_called_external_network_cloud_and_model_download_fail_gates_override_score():
    values = candidate_output_fixture_payload(candidate_outputs=[
        {
            "candidate_model_id": "bad-real-model",
            "backend_type": "MOCK_LOCAL_RUNTIME",
            "candidate_metadata": {
                "model_family": "QWEN",
                "parameter_class": "7B",
                "quantization_target": "Q4",
                "expected_ram_gb": 8.0,
                "expected_vram_gb": 6.0,
                "context_length": 8192,
                "supports_korean": True,
                "supports_english": True,
                "supports_mixed_language": True,
                "json_output_reliability": "HIGH",
                "summarization_suitability": "HIGH",
                "license_notes": "local-eval-only",
                "local_only_feasible": True,
            },
            "benchmark_id": "tech-summary-ko-en-1",
            "output_text": "Technical evidence is improving, but stop context is missing.",
            "output_json": {
                "summary_text": "Technical evidence is improving, but stop context is missing.",
                "bullet_points": ["RSI recovered above 50", "Volume increased"],
            },
            "latency_ms": 120,
            "token_count": 140,
            "real_model_called": True,
            "external_network_calls": False,
            "cloud_backend_used": False,
            "model_downloaded": False,
        },
        {
            "candidate_model_id": "bad-network",
            "backend_type": "MOCK_LOCAL_RUNTIME",
            "candidate_metadata": {
                "model_family": "QWEN",
                "parameter_class": "7B",
                "quantization_target": "Q4",
                "expected_ram_gb": 8.0,
                "expected_vram_gb": 6.0,
                "context_length": 8192,
                "supports_korean": True,
                "supports_english": True,
                "supports_mixed_language": True,
                "json_output_reliability": "HIGH",
                "summarization_suitability": "HIGH",
                "license_notes": "local-eval-only",
                "local_only_feasible": True,
            },
            "benchmark_id": "tech-summary-ko-en-1",
            "output_text": "Technical evidence is improving, but stop context is missing.",
            "output_json": {
                "summary_text": "Technical evidence is improving, but stop context is missing.",
                "bullet_points": ["RSI recovered above 50", "Volume increased"],
            },
            "latency_ms": 120,
            "token_count": 140,
            "real_model_called": False,
            "external_network_calls": True,
            "cloud_backend_used": False,
            "model_downloaded": False,
        },
        {
            "candidate_model_id": "bad-cloud",
            "backend_type": "MOCK_LOCAL_RUNTIME",
            "candidate_metadata": {
                "model_family": "QWEN",
                "parameter_class": "7B",
                "quantization_target": "Q4",
                "expected_ram_gb": 8.0,
                "expected_vram_gb": 6.0,
                "context_length": 8192,
                "supports_korean": True,
                "supports_english": True,
                "supports_mixed_language": True,
                "json_output_reliability": "HIGH",
                "summarization_suitability": "HIGH",
                "license_notes": "local-eval-only",
                "local_only_feasible": True,
            },
            "benchmark_id": "tech-summary-ko-en-1",
            "output_text": "Technical evidence is improving, but stop context is missing.",
            "output_json": {
                "summary_text": "Technical evidence is improving, but stop context is missing.",
                "bullet_points": ["RSI recovered above 50", "Volume increased"],
            },
            "latency_ms": 120,
            "token_count": 140,
            "real_model_called": False,
            "external_network_calls": False,
            "cloud_backend_used": True,
            "model_downloaded": False,
        },
        {
            "candidate_model_id": "bad-download",
            "backend_type": "MOCK_LOCAL_RUNTIME",
            "candidate_metadata": {
                "model_family": "QWEN",
                "parameter_class": "7B",
                "quantization_target": "Q4",
                "expected_ram_gb": 8.0,
                "expected_vram_gb": 6.0,
                "context_length": 8192,
                "supports_korean": True,
                "supports_english": True,
                "supports_mixed_language": True,
                "json_output_reliability": "HIGH",
                "summarization_suitability": "HIGH",
                "license_notes": "local-eval-only",
                "local_only_feasible": True,
            },
            "benchmark_id": "tech-summary-ko-en-1",
            "output_text": "Technical evidence is improving, but stop context is missing.",
            "output_json": {
                "summary_text": "Technical evidence is improving, but stop context is missing.",
                "bullet_points": ["RSI recovered above 50", "Volume increased"],
            },
            "latency_ms": 120,
            "token_count": 140,
            "real_model_called": False,
            "external_network_calls": False,
            "cloud_backend_used": False,
            "model_downloaded": True,
        },
    ])
    report = run_local_model_benchmark(benchmark_fixture(), candidate_output_fixture(values), "benchmark-checksum", "candidate-checksum")
    assert [item.eligibility_result for item in report.evaluations] == [
        "FAIL_REAL_MODEL_CALLED",
        "FAIL_EXTERNAL_NETWORK",
        "FAIL_CLOUD_BACKEND",
        "FAIL_MODEL_DOWNLOAD",
    ]
    assert report.rankings == []


def test_unsupported_backend_execution_attempt_fails():
    report = run_local_model_benchmark(
        benchmark_fixture(),
        candidate_output_fixture(candidate_output_fixture_payload(candidate_outputs=[
            {
                "candidate_model_id": "future-ollama",
                "backend_type": "OLLAMA_LOCAL",
                "candidate_metadata": {
                    "model_family": "QWEN",
                    "parameter_class": "7B",
                    "quantization_target": "Q4",
                    "expected_ram_gb": 8.0,
                    "expected_vram_gb": 6.0,
                    "context_length": 8192,
                    "supports_korean": True,
                    "supports_english": True,
                    "supports_mixed_language": True,
                    "json_output_reliability": "HIGH",
                    "summarization_suitability": "HIGH",
                    "license_notes": "future-backend-only",
                    "local_only_feasible": True,
                },
                "benchmark_id": "tech-summary-ko-en-1",
                "output_text": "Technical evidence is improving, but stop context is missing.",
                "output_json": {
                    "summary_text": "Technical evidence is improving, but stop context is missing.",
                    "bullet_points": ["RSI recovered above 50", "Volume increased"],
                },
                "latency_ms": 120,
                "token_count": 140,
                "real_model_called": False,
                "external_network_calls": False,
                "cloud_backend_used": False,
                "model_downloaded": False,
            }
        ])),
        "benchmark-checksum",
        "candidate-checksum",
    )
    assert report.evaluations[0].eligibility_result == "FAIL_UNSUPPORTED_BACKEND"


def test_missing_data_awareness_gate_can_fail_candidate():
    report = run_local_model_benchmark(
        benchmark_fixture(),
        candidate_output_fixture(candidate_output_fixture_payload(candidate_outputs=[
            {
                "candidate_model_id": "no-missing-awareness",
                "backend_type": "MOCK_LOCAL_RUNTIME",
                "candidate_metadata": {
                    "model_family": "QWEN",
                    "parameter_class": "7B",
                    "quantization_target": "Q4",
                    "expected_ram_gb": 8.0,
                    "expected_vram_gb": 6.0,
                    "context_length": 8192,
                    "supports_korean": True,
                    "supports_english": True,
                    "supports_mixed_language": True,
                    "json_output_reliability": "HIGH",
                    "summarization_suitability": "HIGH",
                    "license_notes": "local-eval-only",
                    "local_only_feasible": True,
                },
                "benchmark_id": "tech-summary-ko-en-1",
                "output_text": "Technical evidence is improving.",
                "output_json": {
                    "summary_text": "Technical evidence is improving.",
                    "bullet_points": ["RSI recovered above 50", "Volume increased"],
                },
                "latency_ms": 120,
                "token_count": 140,
                "real_model_called": False,
                "external_network_calls": False,
                "cloud_backend_used": False,
                "model_downloaded": False,
            }
        ])),
        "benchmark-checksum",
        "candidate-checksum",
    )
    assert report.evaluations[0].eligibility_result == "FAIL_MISSING_DATA_AWARENESS"


def test_rank_only_eligible_candidates():
    values = candidate_output_fixture_payload(candidate_outputs=[
        {
            "candidate_model_id": "eligible-safe",
            "backend_type": "MOCK_LOCAL_RUNTIME",
            "candidate_metadata": {
                "model_family": "QWEN",
                "parameter_class": "7B",
                "quantization_target": "Q4",
                "expected_ram_gb": 8.0,
                "expected_vram_gb": 6.0,
                "context_length": 8192,
                "supports_korean": True,
                "supports_english": True,
                "supports_mixed_language": True,
                "json_output_reliability": "HIGH",
                "summarization_suitability": "HIGH",
                "license_notes": "local-eval-only",
                "local_only_feasible": True,
            },
            "benchmark_id": "tech-summary-ko-en-1",
            "output_text": "Technical evidence is improving, but stop context is missing.",
            "output_json": {
                "summary_text": "Technical evidence is improving, but stop context is missing.",
                "bullet_points": ["RSI recovered above 50", "Volume increased"],
            },
            "latency_ms": 120,
            "token_count": 140,
            "real_model_called": False,
            "external_network_calls": False,
            "cloud_backend_used": False,
            "model_downloaded": False,
        },
        {
            "candidate_model_id": "unsafe-failed",
            "backend_type": "MOCK_LOCAL_RUNTIME",
            "candidate_metadata": {
                "model_family": "QWEN",
                "parameter_class": "7B",
                "quantization_target": "Q4",
                "expected_ram_gb": 8.0,
                "expected_vram_gb": 6.0,
                "context_length": 8192,
                "supports_korean": True,
                "supports_english": True,
                "supports_mixed_language": True,
                "json_output_reliability": "HIGH",
                "summarization_suitability": "HIGH",
                "license_notes": "local-eval-only",
                "local_only_feasible": True,
            },
            "benchmark_id": "tech-summary-ko-en-1",
            "output_text": "Buy now and submit order.",
            "output_json": {
                "summary_text": "Buy now and submit order.",
                "bullet_points": ["RSI recovered above 50", "Volume increased"],
            },
            "latency_ms": 120,
            "token_count": 140,
            "real_model_called": False,
            "external_network_calls": False,
            "cloud_backend_used": False,
            "model_downloaded": False,
        },
    ])
    report = run_local_model_benchmark(benchmark_fixture(), candidate_output_fixture(values), "benchmark-checksum", "candidate-checksum")
    ranked = rank_eligible_candidates(report)
    assert [item.candidate_model_id for item in ranked] == ["eligible-safe"]
