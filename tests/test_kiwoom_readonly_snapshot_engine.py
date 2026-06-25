from stock_risk_mcp.kiwoom_readonly_snapshot_engine import build_kiwoom_readonly_domestic_stock_snapshot
from stock_risk_mcp.kiwoom_readonly_snapshot_models import KiwoomReadonlySnapshotConfig, KiwoomReadonlySnapshotReadiness
from tests.test_kiwoom_readonly_snapshot_models import kiwoom_readonly_snapshot_payload


def _config(**overrides):
    payload = kiwoom_readonly_snapshot_payload()
    payload.update(overrides)
    return KiwoomReadonlySnapshotConfig.model_validate(payload)


def test_snapshot_engine_builds_provider_independent_snapshot():
    result = build_kiwoom_readonly_domestic_stock_snapshot(_config())
    snapshot = result.domestic_stock_snapshot_report.snapshots[0]
    assert result.summary_report.readiness == KiwoomReadonlySnapshotReadiness.SNAPSHOT_READY
    assert snapshot.provider_symbol == "005930"
    assert snapshot.reference_price == 80500
    assert snapshot.latest_close_price == 80500
    assert snapshot.theme_names == ["AI반도체"]
    assert snapshot.leading_theme_names == ["AI반도체"]
    assert snapshot.related_etf_codes == ["069500"]


def test_snapshot_engine_marks_conflict_when_quote_and_close_diverge():
    payload = kiwoom_readonly_snapshot_payload()
    payload["canonical_quote_records"][0]["last_price"] = 80600
    result = build_kiwoom_readonly_domestic_stock_snapshot(KiwoomReadonlySnapshotConfig.model_validate(payload))
    assert result.summary_report.readiness == KiwoomReadonlySnapshotReadiness.CONFLICT
    assert result.conflict_report.conflict_count == 1


def test_snapshot_engine_marks_partial_when_available_at_missing():
    result = build_kiwoom_readonly_domestic_stock_snapshot(_config(available_at=None))
    assert result.summary_report.readiness == KiwoomReadonlySnapshotReadiness.PARTIAL
    assert any(entry.gap_category == "MISSING_AVAILABLE_AT" for entry in result.gap_report.gap_entries)


def test_snapshot_engine_marks_stale_when_input_source_is_stale():
    payload = kiwoom_readonly_snapshot_payload()
    payload["canonical_quote_records"][0]["stale_flag"] = True
    result = build_kiwoom_readonly_domestic_stock_snapshot(KiwoomReadonlySnapshotConfig.model_validate(payload))
    assert result.summary_report.readiness == KiwoomReadonlySnapshotReadiness.STALE
    assert result.freshness_report.stale_source_count >= 1


def test_snapshot_engine_data_gap_when_no_instrument_keys_exist():
    result = build_kiwoom_readonly_domestic_stock_snapshot(
        _config(
            canonical_ohlcv_records=[],
            canonical_rank_signals=[],
            canonical_outlier_signals=[],
            canonical_quote_records=[],
            canonical_orderbook_records=[],
            canonical_liquidity_hints=[],
            canonical_basic_info_records=[],
            canonical_investor_flow_signals=[],
            canonical_program_flow_signals=[],
            canonical_theme_membership_signals=[],
        )
    )
    assert result.summary_report.readiness == KiwoomReadonlySnapshotReadiness.DATA_GAP
    assert result.domestic_stock_snapshot_report.snapshots == []


def test_snapshot_engine_output_remains_report_only_and_non_executable():
    result = build_kiwoom_readonly_domestic_stock_snapshot(_config())
    dumped = result.model_dump_json()
    assert "order_id" not in dumped.lower()
    assert result.safety_report.report_only is True
