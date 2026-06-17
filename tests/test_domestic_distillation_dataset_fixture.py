import pytest

from stock_risk_mcp.domestic_shadow_advisory_context_engine import build_domestic_shadow_advisory_context_bundle
from stock_risk_mcp.domestic_shadow_advisory_context_fixture import load_domestic_shadow_advisory_context_fixture
from stock_risk_mcp.domestic_distillation_dataset_fixture import load_domestic_distillation_dataset_fixture
from stock_risk_mcp.domestic_distillation_dataset_models import DistillationDatasetPrimaryLabel
from tests.test_domestic_realtime_fixture import write
from tests.test_domestic_shadow_advisory_context_fixture import shadow_advisory_context_fixture_payload


def _advisory_context_bundle_payload(tmp_path, advisory_payload: dict | None = None):
    fixture = load_domestic_shadow_advisory_context_fixture(
        write(
            tmp_path,
            "domestic_shadow_advisory_context_fixture.json",
            advisory_payload or shadow_advisory_context_fixture_payload(tmp_path),
        )
    )
    return build_domestic_shadow_advisory_context_bundle(fixture).model_dump(mode="json")


def distillation_config_payload(
    *,
    strategy_track: str = "DOMESTIC_KR",
    training_only: bool = True,
    non_executable: bool = True,
):
    return {
        "config_id": "domestic-distillation-config-1",
        "strategy_track": strategy_track,
        "market_profile_id": "KRX",
        "explicit_training_only_opt_in": True,
        "record_unit_mode": "SUBSUMMARY_PRIMARY",
        "aggregate_record_inclusion_mode": "INCLUDE_OPTIONAL",
        "label_mode": "PRIMARY_AND_AUXILIARY",
        "prompt_stub_inclusion_mode": "INERT_ONLY",
        "split_metadata_mode": "ATTACH_ONLY",
        "leakage_prevention_mode": "FAIL_CLOSED",
        "training_only": training_only,
        "non_executable": non_executable,
        "runtime_decision_allowed": False,
        "llm_runtime_allowed": False,
        "cloud_llm_called": False,
        "local_model_runtime_called": False,
        "no_trade_instruction": True,
    }


def distillation_policy_payload(
    *,
    include_aggregate_record: bool = True,
    allowed_primary_labels: list[str] | None = None,
):
    return {
        "policy_id": "domestic-distillation-policy-1",
        "primary_record_source_modes": [
            "SCENARIO_FAMILY_RECORD",
            "REPLAY_WINDOW_RECORD",
            "OBSERVATION_HORIZON_RECORD",
        ],
        "aggregate_record_enabled": include_aggregate_record,
        "allowed_primary_labels": [
            "LABEL_FAVORABLE_OBSERVATION",
            "LABEL_ADVERSE_OBSERVATION",
            "LABEL_NEUTRAL_OBSERVATION",
            "LABEL_INCONCLUSIVE_OBSERVATION",
            "LABEL_REPORT_ONLY_CONTEXT",
            "LABEL_BLOCKED_QUALITY_CONTEXT",
            "LABEL_BLOCKED_PROFITABILITY_CONTEXT",
            "LABEL_BLOCKED_TECHNICAL_EVIDENCE_CONTEXT",
            "LABEL_BLOCKED_RISK_CONTEXT",
            "LABEL_BLOCKED_SAFETY_CONTEXT",
            "LABEL_INSUFFICIENT_CONTEXT",
        ]
        if allowed_primary_labels is None
        else allowed_primary_labels,
        "allowed_auxiliary_labels": [
            "AUX_REPORT_ONLY_CONTEXT",
            "AUX_LOW_SCENARIO_COVERAGE",
            "AUX_LOW_SYMBOL_COVERAGE",
            "AUX_LOW_OBSERVATION_HORIZON_COVERAGE",
            "AUX_SAFETY_BLOCK_PRESENT",
            "AUX_PROFITABILITY_BLOCK_PRESENT",
            "AUX_TECHNICAL_EVIDENCE_BLOCK_PRESENT",
            "AUX_RISK_BLOCK_PRESENT",
            "AUX_DATA_QUALITY_WARNING",
            "AUX_NON_ACTIONABLE_CONTEXT",
            "AUX_TRAINING_ONLY_CONTEXT",
        ],
        "forbidden_label_patterns": [
            "BUY",
            "SELL",
            "ENTRY",
            "EXIT",
            "ORDER",
            "TRADE_SUCCESS",
            "PROFIT_TRADE",
            "LOSS_TRADE",
            "EXECUTION_RESULT",
            "APPROVED_ENTRY",
            "EXECUTE",
        ],
        "prompt_stub_safety_wording_requirements": [
            "This is training-only context.",
            "Do not provide trade instructions.",
            "Do not output buy/sell/order/execution advice.",
        ],
        "minimum_label_distribution_count": 1,
        "minimum_scenario_coverage_count": 1,
        "minimum_symbol_coverage_count": 1,
        "minimum_observation_horizon_coverage_count": 1,
        "leakage_policy_markers": ["FAIL_CLOSED", "NO_RUNTIME_DECISION", "NO_PROMPT_EXECUTION"],
    }


def distillation_dataset_fixture_payload(
    tmp_path,
    *,
    config: dict | None = None,
    policy: dict | None = None,
    advisory_payload: dict | None = None,
):
    bundle = _advisory_context_bundle_payload(tmp_path, advisory_payload)
    return {
        "schema_version": "4.10-domestic-distillation-dataset-fixture",
        "run_id": "domestic-distillation-run-1",
        "created_at": "2026-06-17T12:00:00+09:00",
        "training_only_distillation_config": config or distillation_config_payload(),
        "training_only_distillation_input_set": {
            "input_set_id": "domestic-distillation-input-set-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_summary": {"market_id": "KRX", "country": "KR", "base_currency": "KRW"},
            "advisory_context_bundle": bundle,
            "source_outcome_review_report_id": bundle["source_outcome_review_report_id"],
            "source_paper_shadow_journal_id": bundle["source_paper_shadow_journal_id"],
            "source_promotion_gate_id": bundle["source_promotion_gate_id"],
            "supported_advisory_task_names": bundle["supported_advisory_task_names"],
            "scenario_family_coverage": [item["section_key"] for item in bundle["scenario_family_sub_summaries"]],
            "symbol_coverage": sorted(bundle["symbol_coverage_summary"]["symbol_counts"].keys()),
            "observation_horizon_coverage": [item["section_key"] for item in bundle["observation_horizon_sub_summaries"]],
            "outcome_label_summary": bundle["outcome_label_summary"],
            "blocked_report_only_non_actionable_summary": bundle["blocked_report_only_non_actionable_summary"],
            "risk_summary": bundle["risk_summary"],
            "data_quality_summary": bundle["data_quality_summary"],
            "training_only": True,
            "non_executable": True,
            "prompt_stubs": [],
            "prompt_stub_execution_requested": False,
            "runtime_decision_requested": False,
        },
        "training_only_distillation_policy": policy or distillation_policy_payload(),
    }


def test_domestic_distillation_dataset_fixture_loads_valid_input(tmp_path):
    fixture = load_domestic_distillation_dataset_fixture(
        write(tmp_path, "domestic_distillation_dataset_fixture.json", distillation_dataset_fixture_payload(tmp_path))
    )
    assert fixture.training_only_distillation_config.strategy_track.value == "DOMESTIC_KR"
    assert fixture.training_only_distillation_input_set.advisory_context_bundle.bundle_id


def test_domestic_distillation_dataset_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_domestic_distillation_dataset_fixture(
            write(tmp_path, "domestic_distillation_dataset_fixture.txt", distillation_dataset_fixture_payload(tmp_path))
        )


def test_domestic_distillation_dataset_fixture_rejects_missing_strategy_track(tmp_path):
    payload = distillation_dataset_fixture_payload(tmp_path)
    del payload["training_only_distillation_config"]["strategy_track"]
    with pytest.raises(ValueError, match="strategy_track"):
        load_domestic_distillation_dataset_fixture(
            write(tmp_path, "domestic_distillation_dataset_fixture.json", payload)
        )


def test_domestic_distillation_dataset_fixture_rejects_missing_market_profile(tmp_path):
    payload = distillation_dataset_fixture_payload(tmp_path)
    del payload["training_only_distillation_input_set"]["market_profile_summary"]
    with pytest.raises(ValueError, match="market_profile"):
        load_domestic_distillation_dataset_fixture(
            write(tmp_path, "domestic_distillation_dataset_fixture.json", payload)
        )


def test_domestic_distillation_dataset_fixture_rejects_missing_advisory_context_bundle(tmp_path):
    payload = distillation_dataset_fixture_payload(tmp_path)
    del payload["training_only_distillation_input_set"]["advisory_context_bundle"]
    with pytest.raises(ValueError, match="advisory_context_bundle"):
        load_domestic_distillation_dataset_fixture(
            write(tmp_path, "domestic_distillation_dataset_fixture.json", payload)
        )


def test_domestic_distillation_dataset_fixture_rejects_missing_training_only_marker(tmp_path):
    payload = distillation_dataset_fixture_payload(tmp_path)
    del payload["training_only_distillation_config"]["training_only"]
    with pytest.raises(ValueError, match="training_only"):
        load_domestic_distillation_dataset_fixture(
            write(tmp_path, "domestic_distillation_dataset_fixture.json", payload)
        )


def test_domestic_distillation_dataset_fixture_rejects_missing_non_executable_marker(tmp_path):
    payload = distillation_dataset_fixture_payload(tmp_path)
    del payload["training_only_distillation_config"]["non_executable"]
    with pytest.raises(ValueError, match="non_executable"):
        load_domestic_distillation_dataset_fixture(
            write(tmp_path, "domestic_distillation_dataset_fixture.json", payload)
        )


def test_domestic_distillation_dataset_fixture_rejects_overseas_track(tmp_path):
    payload = distillation_dataset_fixture_payload(
        tmp_path,
        config=distillation_config_payload(strategy_track="OVERSEAS_US"),
    )
    with pytest.raises(ValueError, match="DOMESTIC_KR"):
        load_domestic_distillation_dataset_fixture(
            write(tmp_path, "domestic_distillation_dataset_fixture.json", payload)
        )


def test_domestic_distillation_dataset_fixture_rejects_unsafe_trigger_attempt(tmp_path):
    payload = distillation_dataset_fixture_payload(tmp_path)
    payload["training_only_distillation_input_set"]["data_quality_summary"]["data_quality_flags"] = [
        "UNSAFE_TRIGGER_ATTEMPT"
    ]
    with pytest.raises(ValueError, match="unsafe trigger"):
        load_domestic_distillation_dataset_fixture(
            write(tmp_path, "domestic_distillation_dataset_fixture.json", payload)
        )


def test_domestic_distillation_dataset_fixture_exposes_primary_label_enum():
    assert DistillationDatasetPrimaryLabel.LABEL_FAVORABLE_OBSERVATION.value == "LABEL_FAVORABLE_OBSERVATION"
