import json

import pytest

from stock_risk_mcp.breadth_leadership_routing_fixture import load_breadth_leadership_routing_fixture
from stock_risk_mcp.breadth_leadership_routing_guard import validate_breadth_leadership_routing_metadata_safety
from stock_risk_mcp.breadth_leadership_routing_models import (
    BreadthLeadershipRoutingDecision,
    BreadthLeadershipRoutingInput,
    BreadthState,
    InternalRiskState,
    LeadershipState,
    OutlierMomentumState,
)


def breadth_leadership_routing_payload(**overrides):
    payload = {
        "routing_review_id": "breadth-routing-1",
        "candidate_symbol": "NVDA",
        "candidate_market": "NASDAQ",
        "candidate_sector_id": "SEMIS",
        "candidate_sector_name": "SEMICONDUCTORS",
        "candidate_action_type": "NEW_ENTRY",
        "decision_timestamp": "2026-06-25T09:30:00+09:00",
        "candidate_is_large_cap": True,
        "candidate_is_leadership_sector": True,
        "candidate_is_outlier_momentum": False,
        "candidate_news_catalyst_available": False,
        "candidate_disclosure_catalyst_available": False,
        "breadth_snapshot": {
            "snapshot_id": "breadth-snapshot-1",
            "market": "NASDAQ",
            "benchmark_ref": "fixtures/breadth/qqq_index.json",
            "observed_at": "2026-06-25T09:00:00+09:00",
            "available_at": "2026-06-25T09:10:00+09:00",
            "source_provider_ref": "fixtures/provider/breadth_provider.json",
            "total_listed_universe_count": 500,
            "tradable_universe_count": 480,
            "advancing_count": 320,
            "declining_count": 120,
            "unchanged_count": 40,
            "new_highs_count": 90,
            "new_lows_count": 15,
            "above_moving_average_count": 300,
            "below_moving_average_count": 140,
            "up_volume": 7000000000.0,
            "down_volume": 3000000000.0,
            "total_volume": 10000000000.0,
            "relative_volume": 1.2,
            "index_return_percent": 1.1,
            "equal_weight_proxy_return_percent": 0.9,
            "large_cap_proxy_return_percent": 1.2,
            "small_mid_cap_proxy_return_percent": 0.8,
            "data_freshness_policy_ref": "docs/policies/breadth_freshness.md",
        },
        "sector_leadership_snapshots": [
            {
                "sector_id": "SEMIS",
                "sector_name": "SEMICONDUCTORS",
                "sector_return_percent": 2.8,
                "sector_relative_strength": 1.7,
                "sector_volume_share": 0.22,
                "sector_trading_value_share": 0.24,
                "sector_advancing_count": 24,
                "sector_declining_count": 8,
                "sector_new_highs_count": 10,
                "sector_new_lows_count": 1,
                "sector_internal_breadth_score": 0.74,
                "top_contributors": ["NVDA", "AVGO", "AMD"],
                "leadership_concentration_score": 0.52,
                "source_refs": [
                    "fixtures/sector/semis_sector.json",
                    "fixtures/provider/sector_mapping_provider.json",
                ],
                "available_at": "2026-06-25T09:10:00+09:00",
            },
            {
                "sector_id": "BIOTECH",
                "sector_name": "BIOTECH",
                "sector_return_percent": 0.2,
                "sector_relative_strength": 0.1,
                "sector_volume_share": 0.07,
                "sector_trading_value_share": 0.06,
                "sector_advancing_count": 14,
                "sector_declining_count": 15,
                "sector_new_highs_count": 2,
                "sector_new_lows_count": 3,
                "sector_internal_breadth_score": 0.48,
                "top_contributors": ["XBI"],
                "leadership_concentration_score": 0.35,
                "source_refs": ["fixtures/sector/biotech_sector.json"],
                "available_at": "2026-06-25T09:10:00+09:00",
            },
        ],
        "index_distortion_snapshot": {
            "snapshot_id": "distortion-snapshot-1",
            "top_1_contribution_share": 0.12,
            "top_2_contribution_share": 0.21,
            "top_5_contribution_share": 0.39,
            "top_10_contribution_share": 0.58,
            "mega_cap_contribution_share": 0.44,
            "index_return_excluding_top_contributors_percent": 0.6,
            "equal_weight_divergence_percent": 0.2,
            "large_cap_vs_small_mid_divergence_percent": 0.4,
            "index_distortion_score": 0.32,
            "distorted_index_warning": False,
            "source_refs": [
                "fixtures/distortion/top_contributors.json",
                "fixtures/provider/provider_selection_report.json",
            ],
            "available_at": "2026-06-25T09:10:00+09:00",
        },
        "outlier_momentum_candidates": [
            {
                "candidate_id": "outlier-1",
                "symbol": "PLTR",
                "market": "NASDAQ",
                "sector": "SOFTWARE",
                "price_change_percent": 14.0,
                "gap_percent": 8.0,
                "relative_volume": 4.2,
                "trading_value_surge": 3.8,
                "new_high_breakout_flag": True,
                "volatility_interruption_flag": False,
                "news_catalyst_ref": "fixtures/news/pltr_news.json",
                "disclosure_theme_catalyst_ref": "fixtures/disclosure/pltr_theme.json",
                "low_float_scarcity_proxy": 0.1,
                "ipo_new_listing_flag": False,
                "liquidity_evidence_ref": "fixtures/liquidity/pltr_liquidity.json",
                "slippage_risk_note": "MANAGEABLE",
                "max_outlier_sleeve_allocation": 0.08,
                "max_per_name_risk": 0.006,
                "required_stop_discipline": "HARD_STOP_5PCT",
                "no_execution_flag": True,
                "available_at": "2026-06-25T09:10:00+09:00",
            }
        ],
        "outlier_sleeve_policy": {
            "policy_id": "outlier-sleeve-1",
            "max_portfolio_allocation": 0.10,
            "max_per_name_risk": 0.0075,
            "max_daily_loss": 0.015,
            "max_outlier_names": 3,
            "mandatory_stop_discipline": True,
            "mandatory_liquidity_evidence": True,
            "mandatory_slippage_note": True,
            "mandatory_no_execution_flag": True,
            "event_risk_compatibility_required": True,
            "watch_only_fallback_when_evidence_missing": True,
        },
        "market_regime_ref": "fixtures/regime/market_regime_report.json",
        "market_regime_label": "RISK_ON",
        "market_regime_risk_appetite": "RISK_ON",
        "position_sizing_ref": "fixtures/position_sizing/position_sizing_review.json",
        "position_sizing_decision": "SIZE_READY",
        "event_risk_ref": "fixtures/event_risk/event_risk_review.json",
        "event_risk_decision": "ALLOW",
        "breadth_provider_readiness_ref": "fixtures/provider/breadth_provider.json",
        "breadth_provider_readiness_level": "PAPER_READY",
        "sector_mapping_provider_readiness_ref": "fixtures/provider/sector_mapping_provider.json",
        "sector_mapping_provider_readiness_level": "PAPER_READY",
        "market_internals_provider_readiness_ref": "fixtures/provider/market_internals_provider.json",
        "market_internals_provider_readiness_level": "PAPER_READY",
        "relative_volume_provider_readiness_ref": "fixtures/provider/relative_volume_provider.json",
        "relative_volume_provider_readiness_level": "PAPER_READY",
        "news_catalyst_provider_ref": "fixtures/provider/news_provider.json",
        "canonical_data_contract_ref": "fixtures/contracts/canonical_breadth_contract.json",
        "source_refs": [
            "fixtures/provider/provider_selection_report.json",
            "fixtures/contracts/canonical_breadth_contract.json",
            "fixtures/regime/market_regime_report.json",
            "fixtures/position_sizing/position_sizing_review.json",
            "fixtures/event_risk/event_risk_review.json",
        ],
        "safety_report": {
            "safety_report_id": "breadth-routing-safety-1",
            "blocked_capabilities": [
                "LIVE_TRADING_BLOCKED",
                "REAL_ORDER_BLOCKED",
                "ACCOUNT_MUTATION_BLOCKED",
                "BROKER_API_BLOCKED",
                "KIWOOM_API_BLOCKED",
                "WEBSOCKET_BLOCKED",
                "NETWORK_BLOCKED",
                "AUTONOMOUS_TRADING_BLOCKED",
            ],
            "findings": [],
        },
        "audit_records": [
            {
                "audit_record_id": "breadth-routing-audit-1",
                "created_at": "2026-06-25T09:31:00+09:00",
                "source_path": "fixtures/breadth/breadth_routing_fixture.json",
                "operator_context": "offline breadth leadership routing review",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_default_breadth_routing_is_local_offline_report_only():
    loaded = BreadthLeadershipRoutingInput.model_validate(breadth_leadership_routing_payload())
    assert loaded.report_only is True
    assert loaded.offline_only is True
    assert loaded.no_order is True


def test_guard_rejects_secret_token_account_and_provider_markers():
    with pytest.raises(ValueError):
        validate_breadth_leadership_routing_metadata_safety({"authorization": "Bearer abc"}, context="breadth routing")
    with pytest.raises(ValueError):
        validate_breadth_leadership_routing_metadata_safety({"account_id": "123-45"}, context="breadth routing")


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "breadth_routing_fixture.json"
    fixture_path.write_text(json.dumps(breadth_leadership_routing_payload()), encoding="utf-8")
    loaded = load_breadth_leadership_routing_fixture(fixture_path)
    assert isinstance(loaded, BreadthLeadershipRoutingInput)
    assert loaded.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_breadth_leadership_routing_fixture("https://example.com/breadth_routing.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_breadth_leadership_routing_fixture(tmp_path / "breadth_routing.parquet")


def test_enum_surface():
    assert BreadthState.BROAD_STRENGTH.value == "BROAD_STRENGTH"
    assert LeadershipState.HEALTHY_SECTOR_LEADERSHIP.value == "HEALTHY_SECTOR_LEADERSHIP"
    assert OutlierMomentumState.OUTLIER_MOMENTUM_ALLOWED.value == "OUTLIER_MOMENTUM_ALLOWED"
    assert InternalRiskState.INTERNAL_STRESS.value == "INTERNAL_STRESS"
    assert BreadthLeadershipRoutingDecision.BROAD_MARKET_OK.value == "BROAD_MARKET_OK"
