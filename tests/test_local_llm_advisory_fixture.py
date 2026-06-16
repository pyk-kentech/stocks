import json

import pytest

from stock_risk_mcp.local_llm_advisory_fixture import load_local_llm_advisory_fixture


def fixture_payload(task_type="SUMMARIZE_TECHNICAL_EVIDENCE", backend=None, inputs=None, safety=None):
    return {
        "schema_version": "3.8-local-llm-advisory-fixture",
        "run_id": "local-llm-advisory-run-1",
        "created_at": "2026-01-22T16:00:00+00:00",
        "task_type": task_type,
        "backend": backend or {
            "backend_type": "DISABLED",
            "model_name": "disabled",
            "model_version": "0",
            "runtime_metadata": {},
        },
        "prompt_metadata": {
            "prompt_id": "tech-summary-v1",
            "prompt_version": "1.0.0",
            "prompt_checksum": "sha256:abc",
        },
        "inputs": inputs or {
            "ticker": "abc",
            "title": "Technical evidence summary",
            "text_blocks": ["RSI recovered above 50", "Price is above 20 EMA"],
        },
        "safety": safety or {
            "advisory_only": True,
            "may_create_order": False,
            "may_bypass_gates": False,
        },
    }


def write(tmp_path, name, value):
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_local_llm_advisory_fixture_normalizes_tickers_and_enforces_flags(tmp_path):
    fixture = load_local_llm_advisory_fixture(write(tmp_path, "local_llm_advisory_fixture.json", fixture_payload()))
    assert fixture.inputs.ticker == "ABC"
    assert fixture.safety.advisory_only is True
    assert fixture.backend.backend_type.value == "DISABLED"


def test_local_llm_advisory_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_local_llm_advisory_fixture(write(tmp_path, "local_llm_advisory_fixture.txt", fixture_payload()))


@pytest.mark.parametrize("change", [
    lambda value: value.update(created_at="2026-01-22T16:00:00"),
    lambda value: value["backend"].update(backend_type="OPENAI"),
    lambda value: value["backend"].update(runtime_metadata={"endpoint_url": "http://localhost"}),
    lambda value: value["inputs"].update(text_blocks=["ok", ""]),
    lambda value: value["safety"].update(advisory_only=False),
    lambda value: value["safety"].update(may_create_order=True),
])
def test_local_llm_advisory_fixture_rejects_invalid_values(tmp_path, change):
    value = fixture_payload()
    change(value)
    with pytest.raises(ValueError):
        load_local_llm_advisory_fixture(write(tmp_path, "local_llm_advisory_fixture.json", value))
