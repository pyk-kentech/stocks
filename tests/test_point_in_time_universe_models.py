import json

import pytest

from stock_risk_mcp.point_in_time_universe_fixture import load_point_in_time_universe_fixture
from stock_risk_mcp.point_in_time_universe_guard import (
    validate_point_in_time_universe_metadata_safety,
)
from stock_risk_mcp.point_in_time_universe_models import (
    PointInTimeUniverseDecision,
    PointInTimeUniverseGateConfig,
    PointInTimeUniverseInput,
    SecurityLifecycleStatus,
)


def point_in_time_universe_payload(**overrides):
    payload = {
        "input_id": "pit-universe-input-1",
        "config": {
            "config_id": "pit-universe-config-1",
            "fixture_format": "json",
        },
        "universe_source": "POINT_IN_TIME_UNIVERSE",
        "universe_snapshots": [
            {
                "snapshot_id": "pit-snapshot-1",
                "trading_date": "2026-06-20",
                "market": "KRX",
                "symbol_universe": ["005930", "000660"],
                "inclusion_reason": "index constituent snapshot",
                "exclusion_reason": "",
                "index_membership_ref": "KOSPI200-20260620",
                "tradability_status": "TRADABLE",
                "available_at": "2026-06-20T08:00:00+09:00",
            }
        ],
        "security_lifecycle_records": [
            {
                "record_id": "life-1",
                "symbol": "005930",
                "status": "LISTED",
                "event_date": "2026-06-20",
                "available_at": "2026-06-20T08:00:00+09:00",
                "coverage_present": True,
            },
            {
                "record_id": "life-2",
                "symbol": "OLD1",
                "status": "DELISTED",
                "event_date": "2026-03-01",
                "available_at": "2026-03-01T08:00:00+09:00",
                "coverage_present": True,
            },
            {
                "record_id": "life-3",
                "symbol": "000660",
                "status": "SUSPENDED",
                "event_date": "2026-04-01",
                "available_at": "2026-04-01T08:00:00+09:00",
                "coverage_present": True,
            },
            {
                "record_id": "life-4",
                "symbol": "REN1",
                "status": "RENAMED",
                "event_date": "2026-02-01",
                "available_at": "2026-02-01T08:00:00+09:00",
                "coverage_present": True,
            },
        ],
        "available_at_coverage_complete": True,
        "corporate_action_coverage_complete": True,
        "index_membership_coverage_complete": True,
        "tradability_coverage_complete": True,
        "missing_date_gap_coverage_complete": True,
        "future_index_membership_leakage_detected": False,
        "current_constituent_replay_leakage_detected": False,
        "future_delisting_knowledge_leakage_detected": False,
        "symbol_survivorship_leakage_detected": False,
        "source_manifest_ids": ["MANIFEST-1"],
        "audit_records": [
            {
                "audit_record_id": "pit-audit-1",
                "created_at": "2026-06-23T00:00:00+09:00",
                "source_path": "fixtures/quant/point_in_time_universe_fixture.json",
                "operator_context": "offline point in time universe gate",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
        "safety_report": {
            "safety_report_id": "pit-universe-safety-1",
            "blocked_capabilities": [
                "LIVE_TRADING_BLOCKED",
                "REAL_ORDER_BLOCKED",
                "ACCOUNT_MUTATION_BLOCKED",
                "BROKER_API_BLOCKED",
                "NETWORK_BLOCKED",
                "AUTONOMOUS_TRADING_BLOCKED",
            ],
            "findings": [],
        },
    }
    payload.update(overrides)
    return payload


def test_default_gate_is_local_offline_report_only():
    config = PointInTimeUniverseGateConfig.model_validate(point_in_time_universe_payload()["config"])
    assert config.read_only is True
    assert config.report_only is True
    assert config.non_executable is True
    assert config.local_file_only is True
    assert config.offline_only is True


def test_security_lifecycle_statuses_are_represented():
    assert SecurityLifecycleStatus.DELISTED.value == "DELISTED"
    assert SecurityLifecycleStatus.SUSPENDED.value == "SUSPENDED"
    assert SecurityLifecycleStatus.RENAMED.value == "RENAMED"


def test_audit_record_is_redacted():
    loaded = PointInTimeUniverseInput.model_validate(point_in_time_universe_payload())
    audit = loaded.audit_records[0]
    assert audit.redaction_applied is True
    assert audit.contains_secret_material is False
    assert audit.contains_token_material is False
    assert audit.contains_account_material is False


def test_guard_rejects_raw_secret_token_account_markers():
    with pytest.raises(ValueError):
        validate_point_in_time_universe_metadata_safety(
            {"authorization": "Bearer abc"},
            context="pit universe",
        )


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "point_in_time_universe_fixture.json"
    fixture_path.write_text(json.dumps(point_in_time_universe_payload()), encoding="utf-8")
    loaded = load_point_in_time_universe_fixture(fixture_path)
    assert isinstance(loaded, PointInTimeUniverseInput)
    assert loaded.config.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_point_in_time_universe_fixture("https://example.com/pit.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_point_in_time_universe_fixture(tmp_path / "pit.parquet")


def test_decision_enum_supports_training_and_research_only():
    assert PointInTimeUniverseDecision.TRAINING_READY.value == "TRAINING_READY"
    assert PointInTimeUniverseDecision.RESEARCH_ONLY.value == "RESEARCH_ONLY"
