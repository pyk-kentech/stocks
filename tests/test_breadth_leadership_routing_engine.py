from stock_risk_mcp.breadth_leadership_routing_engine import build_breadth_leadership_routing_review
from stock_risk_mcp.breadth_leadership_routing_models import (
    BreadthLeadershipRoutingDecision,
    BreadthLeadershipRoutingInput,
    BreadthState,
    LeadershipState,
    OutlierMomentumState,
)
from tests.test_breadth_leadership_routing_models import breadth_leadership_routing_payload


def _run(**overrides):
    payload = breadth_leadership_routing_payload()
    payload.update(overrides)
    return build_breadth_leadership_routing_review(BreadthLeadershipRoutingInput.model_validate(payload))


def test_broad_strength_fixture_produces_broad_market_ok():
    result = _run()
    assert result.summary_report.primary_decision == BreadthLeadershipRoutingDecision.BROAD_MARKET_OK
    assert result.summary_report.breadth_state in {BreadthState.BROAD_STRENGTH, BreadthState.HEALTHY}


def test_broad_weakness_does_not_automatically_block_all_trading():
    snapshot = breadth_leadership_routing_payload()["breadth_snapshot"]
    snapshot["advancing_count"] = 160
    snapshot["declining_count"] = 270
    snapshot["unchanged_count"] = 50
    snapshot["new_highs_count"] = 20
    snapshot["new_lows_count"] = 55
    snapshot["up_volume"] = 3500000000.0
    snapshot["down_volume"] = 6500000000.0
    result = _run(breadth_snapshot=snapshot)
    assert result.summary_report.primary_decision != BreadthLeadershipRoutingDecision.BLOCKED


def test_weak_breadth_plus_healthy_sector_leadership_routes_to_leadership_or_sector_only():
    snapshot = breadth_leadership_routing_payload()["breadth_snapshot"]
    snapshot["advancing_count"] = 190
    snapshot["declining_count"] = 240
    snapshot["unchanged_count"] = 50
    snapshot["new_highs_count"] = 28
    snapshot["new_lows_count"] = 38
    snapshot["up_volume"] = 4100000000.0
    snapshot["down_volume"] = 5900000000.0
    result = _run(breadth_snapshot=snapshot)
    assert result.summary_report.primary_decision in {
        BreadthLeadershipRoutingDecision.LEADERSHIP_ONLY,
        BreadthLeadershipRoutingDecision.SECTOR_ONLY,
    }


def test_crowded_leadership_and_index_distortion_reduce_or_block_chasing():
    snapshot = breadth_leadership_routing_payload()["breadth_snapshot"]
    snapshot["advancing_count"] = 180
    snapshot["declining_count"] = 250
    snapshot["unchanged_count"] = 50
    snapshot["index_return_percent"] = 1.5
    snapshot["equal_weight_proxy_return_percent"] = -0.4
    snapshot["small_mid_cap_proxy_return_percent"] = -1.1
    sectors = breadth_leadership_routing_payload()["sector_leadership_snapshots"]
    sectors[0]["sector_internal_breadth_score"] = 0.41
    sectors[0]["leadership_concentration_score"] = 0.88
    distortion = breadth_leadership_routing_payload()["index_distortion_snapshot"]
    distortion["top_2_contribution_share"] = 0.46
    distortion["top_5_contribution_share"] = 0.74
    distortion["mega_cap_contribution_share"] = 0.71
    distortion["equal_weight_divergence_percent"] = 1.9
    distortion["large_cap_vs_small_mid_divergence_percent"] = 2.3
    distortion["index_distortion_score"] = 0.89
    distortion["distorted_index_warning"] = True
    result = _run(breadth_snapshot=snapshot, sector_leadership_snapshots=sectors, index_distortion_snapshot=distortion)
    assert result.summary_report.leadership_state in {LeadershipState.CROWDED_LEADERSHIP, LeadershipState.INDEX_DISTORTION}
    assert result.summary_report.primary_decision in {
        BreadthLeadershipRoutingDecision.REDUCE_SIZE,
        BreadthLeadershipRoutingDecision.BLOCK_CHASING,
        BreadthLeadershipRoutingDecision.LARGE_CAP_ONLY,
    }
    assert {"CROWDED_LEADERSHIP", "INDEX_DISTORTION"} & set(result.downstream_constraint_report.constraints)


def test_non_leader_candidate_under_weak_breadth_becomes_watch_non_leaders():
    snapshot = breadth_leadership_routing_payload()["breadth_snapshot"]
    snapshot["advancing_count"] = 180
    snapshot["declining_count"] = 260
    snapshot["unchanged_count"] = 40
    result = _run(
        breadth_snapshot=snapshot,
        candidate_symbol="XBI",
        candidate_sector_id="BIOTECH",
        candidate_sector_name="BIOTECH",
        candidate_is_leadership_sector=False,
        candidate_is_large_cap=False,
    )
    assert result.summary_report.primary_decision == BreadthLeadershipRoutingDecision.WATCH_NON_LEADERS


def test_rising_index_with_deteriorating_breadth_emits_divergence_warning():
    snapshot = breadth_leadership_routing_payload()["breadth_snapshot"]
    snapshot["advancing_count"] = 170
    snapshot["declining_count"] = 260
    snapshot["unchanged_count"] = 50
    snapshot["index_return_percent"] = 1.2
    snapshot["equal_weight_proxy_return_percent"] = -0.2
    result = _run(breadth_snapshot=snapshot)
    assert result.equal_weight_divergence_report.divergence_warning is True


def test_valid_outlier_momentum_fixture_can_be_allowed():
    outlier = breadth_leadership_routing_payload()["outlier_momentum_candidates"][0]
    outlier["symbol"] = "PLTR"
    result = _run(
        candidate_symbol="PLTR",
        candidate_sector_id="SOFTWARE",
        candidate_sector_name="SOFTWARE",
        candidate_is_large_cap=False,
        candidate_is_leadership_sector=False,
        candidate_is_outlier_momentum=True,
        candidate_news_catalyst_available=True,
        candidate_disclosure_catalyst_available=True,
        outlier_momentum_candidates=[outlier],
    )
    assert result.summary_report.outlier_momentum_state in {
        OutlierMomentumState.OUTLIER_MOMENTUM_ALLOWED,
        OutlierMomentumState.OUTLIER_WATCH,
    }
    assert result.summary_report.primary_decision in {
        BreadthLeadershipRoutingDecision.OUTLIER_MOMENTUM_ALLOWED,
        BreadthLeadershipRoutingDecision.OUTLIER_MOMENTUM_RESTRICTED,
    }


def test_outlier_without_liquidity_evidence_is_restricted_or_gap():
    outlier = breadth_leadership_routing_payload()["outlier_momentum_candidates"][0]
    outlier["liquidity_evidence_ref"] = None
    result = _run(
        candidate_symbol="PLTR",
        candidate_sector_id="SOFTWARE",
        candidate_sector_name="SOFTWARE",
        candidate_is_large_cap=False,
        candidate_is_leadership_sector=False,
        candidate_is_outlier_momentum=True,
        candidate_news_catalyst_available=True,
        candidate_disclosure_catalyst_available=True,
        outlier_momentum_candidates=[outlier],
    )
    assert result.summary_report.primary_decision in {
        BreadthLeadershipRoutingDecision.OUTLIER_MOMENTUM_RESTRICTED,
        BreadthLeadershipRoutingDecision.DATA_GAP,
    }


def test_event_risk_block_new_entry_is_not_overridden():
    result = _run(event_risk_decision="BLOCK_NEW_ENTRY")
    assert result.summary_report.primary_decision == BreadthLeadershipRoutingDecision.BLOCKED


def test_position_sizing_risk_budget_block_is_not_overridden():
    result = _run(position_sizing_decision="RISK_BUDGET_LIMITED")
    assert result.summary_report.primary_decision == BreadthLeadershipRoutingDecision.BLOCKED


def test_missing_available_at_causes_gap_or_blocked():
    snapshot = breadth_leadership_routing_payload()["breadth_snapshot"]
    snapshot["available_at"] = None
    result = _run(breadth_snapshot=snapshot)
    assert result.summary_report.primary_decision in {
        BreadthLeadershipRoutingDecision.DATA_GAP,
        BreadthLeadershipRoutingDecision.BLOCKED,
    }


def test_impossible_counts_are_blocked():
    snapshot = breadth_leadership_routing_payload()["breadth_snapshot"]
    snapshot["advancing_count"] = 300
    snapshot["declining_count"] = 200
    snapshot["unchanged_count"] = 40
    result = _run(breadth_snapshot=snapshot)
    assert result.summary_report.primary_decision == BreadthLeadershipRoutingDecision.BLOCKED


def test_future_breadth_or_sector_or_outlier_leakage_blocks():
    snapshot = breadth_leadership_routing_payload()["breadth_snapshot"]
    snapshot["available_at"] = "2026-06-25T10:00:00+09:00"
    result = _run(breadth_snapshot=snapshot)
    assert result.summary_report.primary_decision == BreadthLeadershipRoutingDecision.BLOCKED


def test_missing_provider_readiness_causes_data_gap():
    result = _run(breadth_provider_readiness_ref=None, breadth_provider_readiness_level="GAP")
    assert result.summary_report.primary_decision == BreadthLeadershipRoutingDecision.DATA_GAP


def test_training_feature_report_emits_v75_v76_compatible_fields():
    result = _run()
    report = result.training_feature_integration_report
    assert report.routing_feature_snapshot_id
    assert report.primary_routing_decision
    assert report.available_at_present is True
    assert report.training_feature_ready is True


def test_output_remains_report_only_and_audit_redacted():
    result = _run()
    assert result.summary_report.report_only is True
    assert result.audit_records[0].redaction_applied is True
