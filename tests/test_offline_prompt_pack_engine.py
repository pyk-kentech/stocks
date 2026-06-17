from stock_risk_mcp.offline_prompt_pack_engine import (
    build_prompt_pack_coverage_report,
    build_prompt_pack_gap_report,
    validate_prompt_pack,
)
from stock_risk_mcp.offline_prompt_pack_fixture import load_offline_prompt_pack_fixture
from tests.test_offline_prompt_pack_fixture import (
    domestic_trading_task_payload,
    overseas_profitability_task_payload,
    prompt_pack_payload,
    prompt_task_payload,
    write,
)


def load(tmp_path, payload):
    return load_offline_prompt_pack_fixture(write(tmp_path, "offline_prompt_pack_fixture.json", payload))


def test_offline_prompt_pack_engine_validates_track_aware_pack(tmp_path):
    payload = prompt_pack_payload(tasks=[
        prompt_task_payload(
            task_id="generic-en-1",
            language="ENGLISH",
            domain="MISSING_DATA",
            task_type="IDENTIFY_MISSING_DATA",
            safety_trap_tags=["UNSAFE_INSTRUCTION_REJECTION", "ADVISORY_BOUNDARY_REFUSAL", "JSON_ONLY_RESPONSE_ENFORCEMENT"],
        ),
        prompt_task_payload(
            task_id="generic-mixed-1",
            language="MIXED",
            domain="ASSUMPTION_CHALLENGE",
            task_type="CHALLENGE_ASSUMPTIONS",
            safety_trap_tags=["UNSAFE_INSTRUCTION_REJECTION", "ADVISORY_BOUNDARY_REFUSAL", "TRACK_MISSING_FAIL_CLOSED"],
        ),
        domestic_trading_task_payload(),
        overseas_profitability_task_payload(),
    ])
    report = validate_prompt_pack(load(tmp_path, payload))
    assert report.valid is True
    assert report.readiness_status.value == "PACK_READY_FOR_BENCHMARK_FEED"


def test_offline_prompt_pack_engine_rejects_duplicate_task_ids(tmp_path):
    task = prompt_task_payload()
    payload = prompt_pack_payload(tasks=[task, dict(task)])
    report = validate_prompt_pack(load(tmp_path, payload))
    assert report.valid is False
    assert any(issue.code == "DUPLICATE_TASK_ID" for issue in report.issues)


def test_offline_prompt_pack_engine_rejects_trading_task_missing_strategy_track(tmp_path):
    payload = prompt_pack_payload(tasks=[
        prompt_task_payload(
            task_id="trade-no-track",
            task_type="EXPLAIN_TRADE_PLAN_RISK",
            domain="RISK_EXPLANATION",
            task_context_class="TRACK_AWARE_ADVISORY",
            requires_market_profile=True,
        )
    ])
    report = validate_prompt_pack(load(tmp_path, payload))
    assert any(issue.code == "TRADING_TASK_MISSING_SUPPORTED_TRACKS" for issue in report.issues)


def test_offline_prompt_pack_engine_rejects_ambiguous_track_support(tmp_path):
    payload = prompt_pack_payload(tasks=[
        prompt_task_payload(
            task_id="trade-ambiguous-track",
            task_type="EXPLAIN_TRADE_PLAN_RISK",
            domain="RISK_EXPLANATION",
            task_context_class="TRACK_AWARE_ADVISORY",
            supported_tracks=["DOMESTIC_KR", "OVERSEAS_US"],
            requires_market_profile=True,
        )
    ])
    report = validate_prompt_pack(load(tmp_path, payload))
    assert any(issue.code == "AMBIGUOUS_TRACK_SUPPORT" for issue in report.issues)


def test_offline_prompt_pack_engine_rejects_missing_market_profile_requirement(tmp_path):
    payload = prompt_pack_payload(tasks=[
        prompt_task_payload(
            task_id="trade-no-market-profile",
            task_type="EXPLAIN_TRADE_PLAN_RISK",
            domain="RISK_EXPLANATION",
            task_context_class="TRACK_AWARE_ADVISORY",
            supported_tracks=["DOMESTIC_KR"],
            requires_market_profile=False,
        )
    ])
    report = validate_prompt_pack(load(tmp_path, payload))
    assert any(issue.code == "TRADING_TASK_MISSING_MARKET_PROFILE_REQUIREMENT" for issue in report.issues)


def test_offline_prompt_pack_engine_rejects_missing_profitability_context_requirement(tmp_path):
    payload = prompt_pack_payload(tasks=[
        prompt_task_payload(
            task_id="profit-no-context",
            task_type="EXPLAIN_NET_PROFITABILITY",
            domain="RISK_EXPLANATION",
            task_context_class="TRACK_AWARE_PROFITABILITY_ADVISORY",
            supported_tracks=["OVERSEAS_US"],
            requires_market_profile=True,
            requires_profitability_context=True,
            required_profitability_fields=["NetProfitEstimate"],
            supports_report_only_mode=True,
        )
    ])
    report = validate_prompt_pack(load(tmp_path, payload))
    assert any(issue.code == "MISSING_PROFITABILITY_CONTEXT_REQUIREMENTS" for issue in report.issues)


def test_offline_prompt_pack_engine_rejects_actionable_output_from_report_only_context(tmp_path):
    payload = prompt_pack_payload(tasks=[
        prompt_task_payload(
            task_id="report-only-unsafe",
            task_type="EXPLAIN_NET_PROFITABILITY",
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
            allows_actionable_output=True,
        )
    ])
    report = validate_prompt_pack(load(tmp_path, payload))
    assert any(issue.code == "REPORT_ONLY_ACTIONABLE_OUTPUT_FORBIDDEN" for issue in report.issues)


def test_offline_prompt_pack_engine_rejects_domestic_overseas_assumption_leakage(tmp_path):
    payload = prompt_pack_payload(tasks=[
        prompt_task_payload(
            task_id="domestic-with-overseas-fx",
            task_type="EXPLAIN_TRADE_PLAN_RISK",
            domain="RISK_EXPLANATION",
            task_context_class="TRACK_AWARE_ADVISORY",
            supported_tracks=["DOMESTIC_KR"],
            requires_market_profile=True,
            market_assumption_tags=["DOMESTIC_FEE", "OVERSEAS_FX"],
        )
    ])
    report = validate_prompt_pack(load(tmp_path, payload))
    assert any(issue.code == "CROSS_TRACK_ASSUMPTION_LEAKAGE" for issue in report.issues)


def test_offline_prompt_pack_engine_rejects_unsafe_boundary_behavior(tmp_path):
    payload = prompt_pack_payload(
        safety_boundary={
            "order_intent_allowed": False,
            "order_draft_allowed": False,
            "execution_approval_allowed": False,
            "live_prod_allowed": False,
            "broker_access_allowed": False,
            "account_access_allowed": False,
            "credential_access_allowed": False,
            "network_access_allowed": False,
            "cloud_llm_allowed": False,
            "model_runtime_allowed": True,
        }
    )
    report = validate_prompt_pack(load(tmp_path, payload))
    assert any(issue.code == "MODEL_RUNTIME_FORBIDDEN" for issue in report.issues)


def test_offline_prompt_pack_engine_builds_coverage_and_gap_reports(tmp_path):
    payload = prompt_pack_payload(tasks=[
        prompt_task_payload(
            task_id="generic-en-1",
            language="ENGLISH",
            domain="MISSING_DATA",
            task_type="IDENTIFY_MISSING_DATA",
            safety_trap_tags=["UNSAFE_INSTRUCTION_REJECTION", "ADVISORY_BOUNDARY_REFUSAL", "JSON_ONLY_RESPONSE_ENFORCEMENT"],
        ),
        prompt_task_payload(
            task_id="generic-mixed-1",
            language="MIXED",
            domain="ASSUMPTION_CHALLENGE",
            task_type="CHALLENGE_ASSUMPTIONS",
            safety_trap_tags=["UNSAFE_INSTRUCTION_REJECTION", "ADVISORY_BOUNDARY_REFUSAL", "TRACK_MISSING_FAIL_CLOSED"],
        ),
        domestic_trading_task_payload(),
        overseas_profitability_task_payload(),
    ])
    fixture = load(tmp_path, payload)
    validation = validate_prompt_pack(fixture)
    coverage = build_prompt_pack_coverage_report(fixture, validation)
    gap = build_prompt_pack_gap_report(fixture, validation)
    assert coverage.total_task_count == 4
    assert gap.validation_passed is True
    assert gap.readiness_status.value == validation.readiness_status.value
