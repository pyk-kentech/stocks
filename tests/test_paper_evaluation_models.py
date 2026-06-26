import json
from pathlib import Path

from stock_risk_mcp.feature_store_integration_engine import build_feature_store_pipeline
from stock_risk_mcp.feature_store_models import FeatureStorePipelineInput
from stock_risk_mcp.paper_evaluation_fixture import load_paper_evaluation_fixture
from stock_risk_mcp.paper_evaluation_models import PaperEvaluationPipelineInput
from tests.test_feature_store_models import feature_store_payload


def paper_evaluation_payload():
    feature_store_result = build_feature_store_pipeline(
        FeatureStorePipelineInput.model_validate(feature_store_payload(dataset_id="paper-evaluation-test", pipeline_id="paper-evaluation-test")),
        repo_root=Path(__file__).resolve().parents[1],
    )
    return {
        "pipeline_id": "paper-evaluation-test",
        "dataset_id": "paper-evaluation-test",
        "training_dataset_manifest": feature_store_result.training_dataset_manifest.model_dump(mode="json"),
        "feature_rows": [row.model_dump(mode="json") for row in feature_store_result.feature_rows],
        "training_rows": [row.model_dump(mode="json") for row in feature_store_result.training_rows],
        "walk_forward_plan": feature_store_result.walk_forward_plan.model_dump(mode="json"),
        "leakage_report": feature_store_result.leakage_report.model_dump(mode="json"),
        "price_history_rows": [bar.model_dump(mode="json") for bar in FeatureStorePipelineInput.model_validate(feature_store_payload()).price_history_rows],
        "config": {
            "fill_policy": "NEXT_BAR_OPEN",
            "starting_cash": 10000000.0,
            "commission_bps": 5.0,
            "tax_bps": 15.0,
            "slippage_bps": 10.0,
            "spread_penalty_bps": 5.0,
        },
        "audit_records": [
            {
                "audit_record_id": "paper-evaluation-audit-test",
                "created_at": "2026-06-26T16:30:00+09:00",
                "source_path": "fixtures/paper_evaluation/paper_eval_fixture.json",
                "operator_context": "offline paper evaluation unit test",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
    }


def test_paper_evaluation_pipeline_input_is_local_and_safe():
    loaded = PaperEvaluationPipelineInput.model_validate(paper_evaluation_payload())
    assert loaded.no_network is True
    assert loaded.no_env_read is True
    assert loaded.no_broker_paper_api is True


def test_paper_evaluation_fixture_loader_reads_local_json(tmp_path):
    fixture_file = tmp_path / "paper_evaluation_fixture.json"
    fixture_file.write_text(json.dumps(paper_evaluation_payload()), encoding="utf-8")
    loaded = load_paper_evaluation_fixture(fixture_file)
    assert loaded.dataset_id == "PAPER-EVALUATION-TEST"


def test_paper_evaluation_intents_are_non_executable():
    loaded = PaperEvaluationPipelineInput.model_validate(paper_evaluation_payload())
    assert loaded.non_executable is True
