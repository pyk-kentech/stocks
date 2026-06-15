import json

import pytest

from stock_risk_mcp.llm_feature_fixture import load_llm_outcome_fixture, load_llm_signal_fixture


def signal_payload(signals=None):
    return {
        "schema_version": "3.4-signals",
        "run_id": "run-1",
        "created_at": "2026-01-01T16:00:00+00:00",
        "prompt_version": {
            "prompt_version_id": "prompt-v1", "name": "theme", "version": "1",
            "prompt_checksum": "sha256:abc", "created_at": "2026-01-01T00:00:00+00:00",
        },
        "model_version": {
            "model_version_id": "model-v1", "backend": "LOCAL_FIXTURE",
            "model_name": "fixture", "model_version": "1",
            "runtime_metadata": {"quantization": "fixture"},
        },
        "signals": signals or [{
            "ticker": "abc", "as_of_time": "2026-01-01T15:30:00+00:00",
            "source_ids": ["news-1", "news-1"], "event_type": "PRODUCT_LAUNCH",
            "theme_tags": ["SEMICONDUCTOR", "AI"], "direction": "POSITIVE",
            "catalyst_strength_score": .8, "risk_language_score": .2,
            "uncertainty_score": .25, "related_tickers": ["xyz", "XYZ"],
            "summary": "advisory", "evidence_refs": ["e-1"],
            "may_create_order": False, "may_bypass_gates": False,
        }],
    }


def outcome_payload(snapshots=None):
    return {
        "schema_version": "3.4-outcomes",
        "created_at": "2026-01-07T16:00:00+00:00",
        "snapshots": snapshots or [{
            "ticker": "ABC", "as_of_time": "2026-01-01T15:30:00+00:00",
            "reference_price": 100,
            "horizons": [{
                "horizon": "1D", "outcome_time": "2026-01-02T16:00:00+00:00",
                "future_price": 105, "return_pct": 5, "max_drawdown_pct": 2,
            }],
        }],
    }


def write(tmp_path, name, value):
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_signal_fixture_normalizes_lists_and_versions(tmp_path):
    fixture = load_llm_signal_fixture(write(tmp_path, "signals.json", signal_payload()))
    signal = fixture.signals[0]
    assert signal.ticker == "ABC"
    assert signal.source_ids == ["news-1"]
    assert signal.theme_tags == ["AI", "SEMICONDUCTOR"]
    assert signal.related_tickers == ["XYZ"]


def test_loaders_require_explicit_json_files(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_llm_signal_fixture(write(tmp_path, "signals.txt", signal_payload()))
    with pytest.raises(ValueError, match="JSON"):
        load_llm_outcome_fixture(write(tmp_path, "outcomes.txt", outcome_payload()))


@pytest.mark.parametrize("change", [
    lambda value: value["signals"][0].update(may_create_order=True),
    lambda value: value["signals"][0].update(may_create_order=0),
    lambda value: value["signals"][0].update(may_bypass_gates=True),
    lambda value: value["signals"][0].update(catalyst_strength_score=True),
    lambda value: value["signals"][0].update(as_of_time="2026-01-01T15:30:00"),
    lambda value: value["model_version"].update(backend="OPENAI"),
    lambda value: value["model_version"].update(runtime_metadata={"nested": {"token": "x"}}),
    lambda value: value["signals"].append(dict(value["signals"][0])),
])
def test_signal_fixture_rejects_unsafe_or_duplicate_values(tmp_path, change):
    value = signal_payload()
    change(value)
    with pytest.raises(ValueError):
        load_llm_signal_fixture(write(tmp_path, "signals.json", value))


@pytest.mark.parametrize("change", [
    lambda value: value["snapshots"][0]["horizons"][0].update(outcome_time="2026-01-01T15:00:00+00:00"),
    lambda value: value["snapshots"][0]["horizons"][0].update(return_pct=4),
    lambda value: value["snapshots"][0]["horizons"][0].update(future_price=True),
    lambda value: value["snapshots"][0]["horizons"][0].update(max_drawdown_pct=101),
    lambda value: value["snapshots"].append(dict(value["snapshots"][0])),
])
def test_outcome_fixture_rejects_lookahead_inconsistency_and_duplicates(tmp_path, change):
    value = outcome_payload()
    change(value)
    with pytest.raises(ValueError):
        load_llm_outcome_fixture(write(tmp_path, "outcomes.json", value))
