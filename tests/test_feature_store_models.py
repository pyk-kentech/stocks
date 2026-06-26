import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from stock_risk_mcp.feature_store_fixture import load_feature_store_fixture
from stock_risk_mcp.feature_store_guard import validate_feature_store_metadata_safety
from stock_risk_mcp.feature_store_models import FeatureStorePipelineInput, FeatureStoreReadinessStatus


def feature_store_payload(**overrides):
    base = datetime(2026, 6, 2, 15, 35, tzinfo=timezone(timedelta(hours=9)))
    source_kinds = [
        "V8_DOMESTIC_STOCK_SNAPSHOT",
        "V9_MACRO_REGIME_SNAPSHOT",
        "V9_REGIME_CLASSIFICATION",
        "V9_MACRO_EVENT_WINDOW",
        "V7_POINT_IN_TIME_UNIVERSE_CONTEXT",
        "V7_WALK_FORWARD_GUARD_CONTEXT",
        "V7_TRAINING_PROMOTION_CONTEXT",
        "V7_POSITION_SIZING_CONTEXT",
        "V7_EVENT_RISK_CONTEXT",
        "V7_OUTLIER_ROUTING_CONTEXT",
    ]
    namespaces = {
        "V8_DOMESTIC_STOCK_SNAPSHOT": "domestic.price",
        "V9_MACRO_REGIME_SNAPSHOT": "macro.usdkrw",
        "V9_REGIME_CLASSIFICATION": "macro.regime_classification",
        "V9_MACRO_EVENT_WINDOW": "macro.event_window",
        "V7_POINT_IN_TIME_UNIVERSE_CONTEXT": "risk.training_guard_context",
        "V7_WALK_FORWARD_GUARD_CONTEXT": "risk.training_guard_context",
        "V7_TRAINING_PROMOTION_CONTEXT": "risk.training_guard_context",
        "V7_POSITION_SIZING_CONTEXT": "risk.position_sizing_context",
        "V7_EVENT_RISK_CONTEXT": "risk.event_risk_context",
        "V7_OUTLIER_ROUTING_CONTEXT": "risk.outlier_routing_context",
    }
    source_feature_inputs = []
    for index in range(20):
        observed = base + timedelta(days=index)
        kind = source_kinds[index % len(source_kinds)]
        source_feature_inputs.append(
            {
                "source_row_id": f"row-005930-{index:02d}",
                "source_kind": kind,
                "instrument_id": "005930",
                "market": "KRX",
                "currency": "KRW",
                "feature_asof": observed.isoformat(),
                "available_at": observed.isoformat(),
                "snapshot_at": observed.isoformat(),
                "feature_namespace": namespaces[kind],
                "feature_values": {
                    "close_price": 80000.0 + (index * 100.0),
                    "volatility_20d": 0.18 + (index * 0.001),
                    "context_score": round(index / 10.0, 4),
                },
                "source_ref": {
                    "source_id": f"src-{index:02d}",
                    "source_kind": kind,
                    "sanitized_basename": f"source_{index:02d}.json",
                    "relative_path": f"fixtures/feature_store/source_{index:02d}.json",
                    "available_at": observed.isoformat(),
                },
            }
        )
    price_history_rows = []
    for index in range(25):
        observed = base + timedelta(days=index)
        close_price = 80000.0 + (index * 150.0)
        price_history_rows.append(
            {
                "instrument_id": "005930",
                "observed_at": (observed - timedelta(minutes=5)).isoformat(),
                "available_at": observed.isoformat(),
                "open_price": close_price - 100.0,
                "high_price": close_price + 250.0,
                "low_price": close_price - 200.0,
                "close_price": close_price,
                "volume": 1000000 + (index * 1000),
                "source_ref": {
                    "source_id": f"bar-{index:02d}",
                    "source_kind": "V8_CAPTURED_KIWOOM_CHART_HISTORY",
                    "sanitized_basename": f"bar_{index:02d}.json",
                    "relative_path": f"fixtures/feature_store/bar_{index:02d}.json",
                    "available_at": observed.isoformat(),
                },
            }
        )
    payload = {
        "pipeline_id": "feature-store-test",
        "dataset_id": "feature-store-test",
        "dataset_profile": "SMOKE_PROFILE",
        "store_root": "local_data/feature_store/test-fixture",
        "requested_backends": ["IN_MEMORY", "JSON"],
        "partition_spec": {"partition_keys": ["DATASET_ID", "MARKET", "DATE", "SPLIT"]},
        "source_feature_inputs": source_feature_inputs,
        "price_history_rows": price_history_rows,
        "label_specs": [
            {
                "label_name": "FORWARD_RETURN",
                "label_horizon": "1D",
                "label_horizon_policy": "TRADING_SESSION",
                "derivation_method": "LOCAL_PRICE_HISTORY_FORWARD_RETURN",
                "label_direction": "LONG",
                "anchor_price_policy": "LAST_AVAILABLE_CLOSE",
            }
        ],
        "audit_records": [
            {
                "audit_record_id": "feature-store-audit-test",
                "created_at": "2026-06-26T16:00:00+09:00",
                "source_path": "fixtures/feature_store/feature_store_fixture.json",
                "operator_context": "offline feature store unit test",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
    }
    merged = deepcopy(payload)
    merged.update(overrides)
    return merged


def test_feature_store_pipeline_input_defaults_are_local_and_safe():
    loaded = FeatureStorePipelineInput.model_validate(feature_store_payload())
    assert loaded.no_network is True
    assert loaded.no_env_read is True
    assert loaded.no_order is True
    assert loaded.dataset_profile.value == "SMOKE_PROFILE"


def test_feature_store_fixture_loader_reads_local_json(tmp_path):
    fixture_file = tmp_path / "feature_store_fixture.json"
    fixture_file.write_text(json.dumps(feature_store_payload()), encoding="utf-8")
    loaded = load_feature_store_fixture(fixture_file)
    assert loaded.dataset_id == "FEATURE-STORE-TEST"


def test_feature_store_metadata_safety_rejects_order_markers():
    with pytest.raises(ValueError):
        validate_feature_store_metadata_safety({"note": "buy now"}, context="feature store")


def test_feature_store_readiness_enum_contains_blocked_leakage():
    assert FeatureStoreReadinessStatus.BLOCKED_LEAKAGE.value == "BLOCKED_LEAKAGE"
