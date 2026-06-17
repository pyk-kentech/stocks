import json

import pytest

from stock_risk_mcp.offline_prompt_pack_fixture import load_offline_prompt_pack_fixture


def prompt_task_payload(
    *,
    task_id: str = "generic-ko-1",
    task_type: str = "SUMMARIZE_TECHNICAL_EVIDENCE",
    language: str = "KOREAN",
    domain: str = "TECHNICAL_EVIDENCE",
    task_context_class: str = "GENERIC_NON_TRADING",
    supported_tracks: list[str] | None = None,
    requires_market_profile: bool = False,
    requires_profitability_context: bool = False,
    required_profitability_fields: list[str] | None = None,
    supports_report_only_mode: bool = False,
    allows_actionable_output: bool = False,
    market_assumption_tags: list[str] | None = None,
    safety_trap_tags: list[str] | None = None,
):
    return {
        "task_id": task_id,
        "task_type": task_type,
        "language": language,
        "domain": domain,
        "input_fixture_reference": f"fixtures/{task_id}.json",
        "expected_output_schema": ["summary_text", "bullet_points"],
        "expected_safe_behavior": [
            "summarize evidence only",
            "avoid direct buy or sell instruction",
        ],
        "forbidden_output_patterns": [
            "buy now",
            "sell now",
            "submit order",
            "execution approved",
        ],
        "scoring_rubric_reference": "rubrics/default_advisory.json",
        "safety_trap_tags": safety_trap_tags
        or [
            "UNSAFE_INSTRUCTION_REJECTION",
            "ADVISORY_BOUNDARY_REFUSAL",
        ],
        "task_context_class": task_context_class,
        "supported_tracks": supported_tracks or [],
        "requires_market_profile": requires_market_profile,
        "requires_profitability_context": requires_profitability_context,
        "required_profitability_fields": required_profitability_fields or [],
        "supports_report_only_mode": supports_report_only_mode,
        "allows_actionable_output": allows_actionable_output,
        "market_assumption_tags": market_assumption_tags or [],
    }


def prompt_pack_payload(tasks=None, safety_boundary=None):
    return {
        "schema_version": "3.12-offline-prompt-pack-fixture",
        "prompt_pack_id": "offline-prompt-pack-1",
        "prompt_version": "1.0.0",
        "created_at": "2026-06-17T12:00:00+00:00",
        "safety_boundary": safety_boundary
        or {
            "order_intent_allowed": False,
            "order_draft_allowed": False,
            "execution_approval_allowed": False,
            "live_prod_allowed": False,
            "broker_access_allowed": False,
            "account_access_allowed": False,
            "credential_access_allowed": False,
            "network_access_allowed": False,
            "cloud_llm_allowed": False,
            "model_runtime_allowed": False,
        },
        "tasks": tasks or [prompt_task_payload()],
    }


def domestic_trading_task_payload():
    return prompt_task_payload(
        task_id="domestic-trade-risk-1",
        task_type="EXPLAIN_TRADE_PLAN_RISK",
        language="KOREAN",
        domain="RISK_EXPLANATION",
        task_context_class="TRACK_AWARE_ADVISORY",
        supported_tracks=["DOMESTIC_KR"],
        requires_market_profile=True,
        market_assumption_tags=["DOMESTIC_FEE", "DOMESTIC_TAX", "DOMESTIC_SESSION"],
    )


def overseas_profitability_task_payload():
    return prompt_task_payload(
        task_id="overseas-profitability-1",
        task_type="EXPLAIN_NET_PROFITABILITY",
        language="ENGLISH",
        domain="RISK_EXPLANATION",
        task_context_class="TRACK_AWARE_PROFITABILITY_ADVISORY",
        supported_tracks=["OVERSEAS_US"],
        requires_market_profile=True,
        requires_profitability_context=True,
        required_profitability_fields=[
            "FeeTaxProfile",
            "CurrencyProfile",
            "FXCostProfile",
            "NetProfitEstimate",
            "TrackAwareProfitabilityCheck",
        ],
        supports_report_only_mode=True,
        allows_actionable_output=False,
        market_assumption_tags=["OVERSEAS_FEE", "OVERSEAS_FX", "OVERSEAS_SESSION"],
    )


def write(tmp_path, name, value):
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_offline_prompt_pack_fixture_loads_valid_non_trading_pack(tmp_path):
    fixture = load_offline_prompt_pack_fixture(write(tmp_path, "offline_prompt_pack_fixture.json", prompt_pack_payload()))
    assert fixture.prompt_pack_id == "offline-prompt-pack-1"
    assert fixture.tasks[0].task_context_class.value == "GENERIC_NON_TRADING"


def test_offline_prompt_pack_fixture_loads_valid_domestic_trading_pack(tmp_path):
    fixture = load_offline_prompt_pack_fixture(
        write(tmp_path, "offline_prompt_pack_fixture.json", prompt_pack_payload(tasks=[domestic_trading_task_payload()]))
    )
    assert fixture.tasks[0].supported_tracks[0].value == "DOMESTIC_KR"


def test_offline_prompt_pack_fixture_loads_valid_overseas_trading_pack(tmp_path):
    fixture = load_offline_prompt_pack_fixture(
        write(tmp_path, "offline_prompt_pack_fixture.json", prompt_pack_payload(tasks=[overseas_profitability_task_payload()]))
    )
    assert fixture.tasks[0].supported_tracks[0].value == "OVERSEAS_US"


def test_offline_prompt_pack_fixture_requires_explicit_json_file(tmp_path):
    with pytest.raises(ValueError, match="JSON"):
        load_offline_prompt_pack_fixture(write(tmp_path, "offline_prompt_pack_fixture.txt", prompt_pack_payload()))


def test_offline_prompt_pack_fixture_rejects_missing_pack_id(tmp_path):
    payload = prompt_pack_payload()
    del payload["prompt_pack_id"]
    with pytest.raises(ValueError, match="prompt_pack_id"):
        load_offline_prompt_pack_fixture(write(tmp_path, "offline_prompt_pack_fixture.json", payload))
