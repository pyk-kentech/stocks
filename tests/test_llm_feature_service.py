import sqlite3

import pytest

from stock_risk_mcp.llm_feature_service import run_feature_store, run_signal_evaluation
from tests.test_llm_feature_fixture import outcome_payload, signal_payload, write


def test_service_is_db_free_by_default_and_writes_optional_output(tmp_path):
    signal_file = write(tmp_path, "signals.json", signal_payload())
    output = tmp_path / "feature.json"
    result = run_feature_store(signal_file, output_file=output)
    assert result.signal_count == 1
    assert output.exists()
    assert not (tmp_path / "audit.sqlite3").exists()


def test_optional_service_audit_is_append_only_and_safe(tmp_path):
    signal_file = write(tmp_path, "signals.json", signal_payload())
    outcome_file = write(tmp_path, "outcomes.json", outcome_payload())
    db = tmp_path / "audit.sqlite3"

    run_feature_store(signal_file, db_path=db)
    run_signal_evaluation(signal_file, outcome_file, db_path=db)

    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM llm_prompt_versions").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM llm_model_versions").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM llm_feature_signals").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM llm_signal_evaluations").fetchone()[0] == 3
        prompt_json = connection.execute("SELECT prompt_json FROM llm_prompt_versions").fetchone()[0]
        model_json = connection.execute("SELECT model_json FROM llm_model_versions").fetchone()[0]
    assert "system_instructions" not in prompt_json
    assert "runtime_metadata" not in model_json

    with pytest.raises(sqlite3.IntegrityError):
        run_feature_store(signal_file, db_path=db)
