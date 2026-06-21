import json

import pytest

from stock_risk_mcp.cli import main
from tests.test_historical_model_experiment_engine import _engine_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_historical_model_experiment_cli_commands_return_report_only_json_outputs(tmp_path, capsys):
    fixture_file = write(
        tmp_path / "historical_model_experiment_fixture.json",
        _engine_payload(),
    )
    register_file = tmp_path / "historical_model_experiment_registry_report.json"
    compare_file = tmp_path / "historical_model_comparison_report.json"
    risk_file = tmp_path / "historical_model_risk_review_report.json"
    promotion_file = tmp_path / "historical_model_promotion_block_report.json"
    safety_file = tmp_path / "historical_model_experiment_safety_report.json"

    register = run(
        capsys,
        ["historical-model-experiment-register", "--fixture-file", str(fixture_file), "--output-file", str(register_file)],
    )
    compare = run(
        capsys,
        ["historical-model-experiment-compare", "--fixture-file", str(fixture_file), "--output-file", str(compare_file)],
    )
    risk = run(
        capsys,
        ["historical-model-risk-review", "--fixture-file", str(fixture_file), "--output-file", str(risk_file)],
    )
    promotion = run(
        capsys,
        ["historical-model-promotion-block-report", "--fixture-file", str(fixture_file), "--output-file", str(promotion_file)],
    )
    safety = run(
        capsys,
        ["historical-model-experiment-safety-report", "--fixture-file", str(fixture_file), "--output-file", str(safety_file)],
    )

    assert register["status"] == "COMPLETED"
    assert compare["status"] == "COMPLETED"
    assert risk["status"] == "COMPLETED"
    assert promotion["status"] == "COMPLETED"
    assert safety["status"] == "COMPLETED"

    register_json = json.loads(register_file.read_text(encoding="utf-8"))
    compare_json = json.loads(compare_file.read_text(encoding="utf-8"))
    risk_json = json.loads(risk_file.read_text(encoding="utf-8"))
    promotion_json = json.loads(promotion_file.read_text(encoding="utf-8"))
    safety_json = json.loads(safety_file.read_text(encoding="utf-8"))

    assert register_json["report_only"] is True
    assert register_json["non_executable"] is True
    assert register_json["experiment_count"] == 1
    assert compare_json["report_only"] is True
    assert compare_json["safety_blocked"] is True
    assert "live_rank" not in str(compare_json).lower()
    assert risk_json["report_only"] is True
    assert risk_json["unsafe_artifact_metadata"] is False
    assert promotion_json["production_use_allowed"] is False
    assert promotion_json["live_inference_allowed"] is False
    assert promotion_json["runtime_trading_signal_allowed"] is False
    assert promotion_json["order_candidate_allowed"] is False
    assert promotion_json["paper_trading_allowed"] is False
    assert promotion_json["broker_path_allowed"] is False
    assert promotion_json["live_prod_allowed"] is False
    assert promotion_json["deployment_allowed"] is False
    assert safety_json["report_only"] is True
    assert safety_json["no_runtime_trading_signal"] is True
    assert safety_json["no_order_candidate"] is True
    assert safety_json["no_live_inference"] is True
    assert safety_json["no_deployment"] is True


@pytest.mark.parametrize(
    "command",
    [
        "historical-model-experiment-register",
        "historical-model-experiment-compare",
        "historical-model-risk-review",
        "historical-model-promotion-block-report",
        "historical-model-experiment-safety-report",
    ],
)
def test_historical_model_experiment_cli_missing_fixture_is_json_safe(command, tmp_path, capsys):
    result = run(capsys, [command, "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_historical_model_experiment_cli_preserves_safety_flags(tmp_path, capsys):
    fixture_file = write(
        tmp_path / "historical_model_experiment_fixture.json",
        _engine_payload(),
    )

    result = run(capsys, ["historical-model-experiment-safety-report", "--fixture-file", str(fixture_file)])

    assert result["read_only"] is True
    assert result["report_only"] is True
    assert result["non_executable"] is True
    assert result["local_file_only"] is True
    assert result["offline_only"] is True
    assert result["no_network"] is True
    assert result["no_provider_api"] is True
    assert result["no_order"] is True
    assert result["no_broker_path"] is True
    assert result["no_live_prod"] is True
    assert result["no_cloud_llm"] is True
    assert result["no_local_llm_runtime"] is True
    assert result["no_runtime_trading_signal"] is True
    assert result["no_order_candidate"] is True
    assert result["no_live_inference"] is True
    assert result["no_deployment"] is True


def test_historical_model_experiment_cli_preserves_promotion_block_boundary(tmp_path, capsys):
    fixture_file = write(
        tmp_path / "historical_model_experiment_fixture.json",
        _engine_payload(),
    )

    result = run(capsys, ["historical-model-promotion-block-report", "--fixture-file", str(fixture_file)])

    assert result["production_use_allowed"] is False
    assert result["live_inference_allowed"] is False
    assert result["runtime_trading_signal_allowed"] is False
    assert result["order_candidate_allowed"] is False
    assert result["paper_trading_allowed"] is False
    assert result["deployment_allowed"] is False
