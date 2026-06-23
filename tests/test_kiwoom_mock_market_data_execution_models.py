import json

import pytest

from stock_risk_mcp.kiwoom_mock_market_data_execution_engine import (
    build_kiwoom_mock_market_data_execution_gap_report,
)
from stock_risk_mcp.kiwoom_mock_market_data_execution_fixture import (
    load_kiwoom_mock_market_data_execution_fixture,
)
from stock_risk_mcp.kiwoom_mock_market_data_execution_guard import (
    validate_kiwoom_mock_market_data_execution_metadata_safety,
)
from stock_risk_mcp.kiwoom_mock_market_data_execution_models import (
    KiwoomMockMarketDataExecutionConfig,
    KiwoomMockMarketDataExecutionGapReport,
    KiwoomMockMarketDataExecutionSafetyReport,
    KiwoomMockMarketDataResponse,
)


def kiwoom_mock_market_data_execution_fixture_payload(
    *,
    preflight_readiness_decision: str = "DRAFT_READY",
    documented_category: str = "QUOTE",
    documented_path: str = "/api/dostk/mrkcond",
    documented_mock_domain: str = "https://mockapi.kiwoom.com",
) -> dict:
    return {
        "schema_version": "v6.9-kiwoom-mock-market-data-execution-adapter",
        "fixture_format": "json",
        "config_id": "kiwoom-mock-market-data-execution-config-1",
        "mock_domain": documented_mock_domain,
        "documented_category": documented_category,
        "documented_path": documented_path,
        "preflight_readiness_decision": preflight_readiness_decision,
        "token_reference_label": "KIWOOM_MOCK_ACCESS_TOKEN_REF",
        "timeout_seconds": 5,
        "max_retry_count": 1,
        "retry_backoff_seconds": 0.0,
        "explicit_opt_in_required": True,
        "redact_output": True,
        "persist_token_to_disk": False,
        "allow_token_refresh": False,
        "oauth_draft_boundary_ref": "docs/superpowers/plans/2026-06-18-kiwoom-mock-oauth-token-draft-boundary-design.md",
        "transport_boundary_ref": "docs/superpowers/plans/2026-06-18-kiwoom-mock-api-transport-request-envelope-boundary-design.md",
        "preflight_boundary_ref": "docs/superpowers/plans/2026-06-18-kiwoom-mock-api-execution-readiness-preflight-gate-design.md",
        "oauth_execution_boundary_ref": "docs/superpowers/plans/2026-06-18-kiwoom-mock-oauth-execution-adapter-design.md",
        "safety_report": {
            "safety_report_id": "kiwoom-mock-market-data-execution-safety-report-1",
            "blocked_capabilities": [
                "PRODUCTION_DOMAIN_BLOCKED",
                "ACCOUNT_PATH_BLOCKED",
                "ORDER_PATH_BLOCKED",
                "WEBSOCKET_BLOCKED",
                "LIVE_PROD_BLOCKED",
            ],
            "findings": [],
        },
        "gap_report": {
            "gap_report_id": "kiwoom-mock-market-data-execution-gap-report-1",
            "gap_status": "UNRESOLVED_FUTURE_STAGES",
            "gap_categories": [
                "REAL_MARKET_DATA_STAGE_NOT_IMPLEMENTED",
                "ACCOUNT_STAGE_NOT_IMPLEMENTED",
                "ORDER_STAGE_NOT_IMPLEMENTED",
            ],
            "blocking_gap_count": 3,
            "report_only_gap_count": 0,
            "gaps": [
                "real market data stage deferred",
                "account stage deferred",
                "order stage deferred",
            ],
        },
        "audit_records": [
            {
                "audit_record_id": "kiwoom-mock-market-data-execution-audit-record-1",
                "created_at": "2026-06-23T00:00:00+09:00",
                "source_path": "fixtures/kiwoom/kiwoom_mock_market_data_execution_fixture.json",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
                "evidence_refs": ["KIWOOM-REST-EVIDENCE-PACK", "KIWOOM-CAPABILITY-MATRIX"],
            }
        ],
    }


def test_default_execution_is_disabled():
    config = KiwoomMockMarketDataExecutionConfig.model_validate(
        kiwoom_mock_market_data_execution_fixture_payload()
    )
    assert config.disabled_by_default is True
    assert config.mock_only is True
    assert config.read_only_market_data_execution_only is True
    assert config.non_executable_without_opt_in is True


def test_production_domain_is_blocked():
    payload = kiwoom_mock_market_data_execution_fixture_payload(
        documented_mock_domain="https://api.kiwoom.com"
    )
    with pytest.raises(ValueError, match="production domain"):
        KiwoomMockMarketDataExecutionConfig.model_validate(payload)


def test_only_preflight_draft_ready_can_proceed():
    payload = kiwoom_mock_market_data_execution_fixture_payload(
        preflight_readiness_decision="GAP"
    )
    with pytest.raises(ValueError, match="preflight"):
        KiwoomMockMarketDataExecutionConfig.model_validate(payload)


@pytest.mark.parametrize(
    ("data", "pattern"),
    [
        ({"secretkey": "raw-secret"}, "secret"),
        ({"access_token": "raw-token"}, "token"),
        ({"authorization": "Bearer abc"}, "authorization"),
        ({"account_number": "123456"}, "account"),
    ],
)
def test_raw_secret_token_account_markers_are_rejected(data, pattern):
    with pytest.raises(ValueError, match=pattern):
        validate_kiwoom_mock_market_data_execution_metadata_safety(data, context="test")


def test_sanitized_response_object_is_report_only():
    response = KiwoomMockMarketDataResponse(
        response_object_id="kiwoom-mock-market-data-response-1",
        documented_category="QUOTE",
        documented_path="/api/dostk/mrkcond",
        symbol="005930",
        payload={"last_price": 70000, "condition_match": True},
        sanitized=True,
        raw_token_exposed=False,
        persisted_to_disk=False,
    )
    dumped = response.model_dump(mode="json")
    assert dumped["sanitized"] is True
    assert "authorization" not in json.dumps(dumped).lower()


def test_safety_report_blocks_non_readonly_paths():
    report = KiwoomMockMarketDataExecutionSafetyReport.model_validate(
        kiwoom_mock_market_data_execution_fixture_payload()["safety_report"]
    )
    assert "ACCOUNT_PATH_BLOCKED" in report.blocked_capabilities
    assert "ORDER_PATH_BLOCKED" in report.blocked_capabilities


def test_gap_report_lists_future_stages():
    report = build_kiwoom_mock_market_data_execution_gap_report(
        KiwoomMockMarketDataExecutionConfig.model_validate(
            kiwoom_mock_market_data_execution_fixture_payload()
        )
    )
    assert isinstance(report, KiwoomMockMarketDataExecutionGapReport)
    assert "REAL_MARKET_DATA_STAGE_NOT_IMPLEMENTED" in [item.value for item in report.gap_categories]


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "kiwoom_mock_market_data_execution_fixture.json"
    fixture_path.write_text(
        json.dumps(kiwoom_mock_market_data_execution_fixture_payload()),
        encoding="utf-8",
    )
    loaded = load_kiwoom_mock_market_data_execution_fixture(fixture_path)
    assert loaded.config_id == "KIWOOM-MOCK-MARKET-DATA-EXECUTION-CONFIG-1"


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_kiwoom_mock_market_data_execution_fixture("https://mockapi.kiwoom.com/market.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_kiwoom_mock_market_data_execution_fixture(tmp_path / "market.parquet")
