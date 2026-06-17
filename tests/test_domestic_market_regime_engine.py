from stock_risk_mcp.domestic_market_regime_engine import (
    build_market_regime_classification,
    build_market_regime_context_reference,
    build_market_regime_gap_report,
    build_market_regime_report,
    build_market_regime_safety_report,
)
from stock_risk_mcp.domestic_market_regime_fixture import load_domestic_market_regime_fixture
from tests.test_domestic_market_regime_fixture import market_regime_fixture_payload
from tests.test_domestic_realtime_fixture import write


def _load(tmp_path, payload):
    return load_domestic_market_regime_fixture(
        write(tmp_path, "domestic_market_regime_fixture.json", payload)
    )


def _classify(tmp_path, payload):
    return build_market_regime_classification(_load(tmp_path, payload))


def test_domestic_market_regime_classifies_risk_on(tmp_path):
    classification = _classify(tmp_path, market_regime_fixture_payload())
    assert classification.primary_regime_label.value == "REGIME_RISK_ON"


def test_domestic_market_regime_classifies_risk_off(tmp_path):
    payload = market_regime_fixture_payload()
    payload["market_regime_input_set"]["risk_evidence"]["risk_off_warning_score"] = 0.88
    payload["market_regime_input_set"]["risk_evidence"]["stress_marker_count"] = 3
    payload["market_regime_input_set"]["breadth_evidence"]["breadth_proxy_pct"] = 0.32
    classification = _classify(tmp_path, payload)
    assert classification.primary_regime_label.value == "REGIME_RISK_OFF"


def test_domestic_market_regime_classifies_index_uptrend(tmp_path):
    payload = market_regime_fixture_payload()
    payload["market_regime_input_set"]["risk_evidence"]["risk_off_warning_score"] = 0.42
    classification = _classify(tmp_path, payload)
    assert "REGIME_INDEX_UPTREND" in {label.value for label in classification.secondary_regime_labels}


def test_domestic_market_regime_classifies_index_downtrend(tmp_path):
    payload = market_regime_fixture_payload()
    payload["market_regime_input_set"]["index_evidence"]["short_return_pct"] = -1.7
    payload["market_regime_input_set"]["index_evidence"]["medium_return_pct"] = -2.4
    payload["market_regime_input_set"]["risk_evidence"]["risk_off_warning_score"] = 0.41
    classification = _classify(tmp_path, payload)
    assert classification.primary_regime_label.value == "REGIME_INDEX_DOWNTREND"


def test_domestic_market_regime_classifies_sector_momentum(tmp_path):
    classification = _classify(tmp_path, market_regime_fixture_payload())
    assert "REGIME_SECTOR_MOMENTUM" in {label.value for label in classification.secondary_regime_labels}


def test_domestic_market_regime_classifies_sector_rotation(tmp_path):
    payload = market_regime_fixture_payload()
    payload["market_regime_input_set"]["risk_evidence"]["risk_off_warning_score"] = 0.42
    payload["market_regime_input_set"]["sector_evidence"]["leadership_concentration_pct"] = 0.38
    payload["market_regime_input_set"]["sector_evidence"]["rotation_proxy"] = 0.81
    classification = _classify(tmp_path, payload)
    assert classification.primary_regime_label.value == "REGIME_SECTOR_ROTATION"


def test_domestic_market_regime_classifies_breadth_weak(tmp_path):
    payload = market_regime_fixture_payload()
    payload["market_regime_input_set"]["risk_evidence"]["risk_off_warning_score"] = 0.42
    payload["market_regime_input_set"]["breadth_evidence"]["breadth_proxy_pct"] = 0.34
    classification = _classify(tmp_path, payload)
    assert classification.primary_regime_label.value == "REGIME_BREADTH_WEAK"


def test_domestic_market_regime_classifies_volatility_spike(tmp_path):
    payload = market_regime_fixture_payload()
    payload["market_regime_input_set"]["risk_evidence"]["risk_off_warning_score"] = 0.42
    payload["market_regime_input_set"]["volatility_evidence"]["volatility_expansion_proxy_ratio"] = 1.52
    classification = _classify(tmp_path, payload)
    assert classification.primary_regime_label.value == "REGIME_VOLATILITY_SPIKE"


def test_domestic_market_regime_classifies_liquidity_thin(tmp_path):
    payload = market_regime_fixture_payload()
    payload["market_regime_input_set"]["risk_evidence"]["risk_off_warning_score"] = 0.42
    payload["market_regime_input_set"]["liquidity_evidence"]["turnover_proxy_ratio"] = 0.48
    payload["market_regime_input_set"]["liquidity_evidence"]["volume_expansion_proxy_ratio"] = 0.63
    classification = _classify(tmp_path, payload)
    assert classification.primary_regime_label.value == "REGIME_LIQUIDITY_THIN"


def test_domestic_market_regime_classifies_choppy_market(tmp_path):
    payload = market_regime_fixture_payload()
    payload["market_regime_input_set"]["risk_evidence"]["risk_off_warning_score"] = 0.42
    payload["market_regime_input_set"]["index_evidence"]["short_return_pct"] = 0.12
    payload["market_regime_input_set"]["index_evidence"]["medium_return_pct"] = 0.24
    payload["market_regime_input_set"]["breadth_evidence"]["breadth_proxy_pct"] = 0.51
    payload["market_regime_input_set"]["sector_evidence"]["leadership_concentration_pct"] = 0.41
    payload["market_regime_input_set"]["sector_evidence"]["rotation_proxy"] = 0.44
    classification = _classify(tmp_path, payload)
    assert classification.primary_regime_label.value == "REGIME_CHOPPY_MARKET"


def test_domestic_market_regime_classifies_insufficient_data(tmp_path):
    payload = market_regime_fixture_payload()
    payload["market_regime_input_set"]["index_evidence"]["short_return_pct"] = None
    payload["market_regime_input_set"]["index_evidence"]["medium_return_pct"] = None
    payload["market_regime_input_set"]["sector_evidence"]["sector_return_distribution"] = {}
    payload["market_regime_input_set"]["breadth_evidence"]["breadth_proxy_pct"] = None
    classification = _classify(tmp_path, payload)
    assert classification.primary_regime_label.value == "REGIME_INSUFFICIENT_DATA"


def test_domestic_market_regime_classifies_report_only_stale(tmp_path):
    payload = market_regime_fixture_payload(explicit_report_only=True)
    payload["market_regime_input_set"]["data_quality_flags"] = ["AUXILIARY_METADATA_STALE"]
    classification = _classify(tmp_path, payload)
    assert classification.primary_regime_label.value == "REGIME_REPORT_ONLY"
    assert classification.report_only is True


def test_domestic_market_regime_primary_label_required(tmp_path):
    classification = _classify(tmp_path, market_regime_fixture_payload())
    assert classification.primary_regime_label.value


def test_domestic_market_regime_secondary_labels_supported(tmp_path):
    classification = _classify(tmp_path, market_regime_fixture_payload())
    assert classification.secondary_regime_labels


def test_domestic_market_regime_generates_evidence_strength_bucket(tmp_path):
    classification = _classify(tmp_path, market_regime_fixture_payload())
    assert classification.evidence_strength_bucket.value in {"EVIDENCE_STRONG", "EVIDENCE_MODERATE", "EVIDENCE_WEAK", "EVIDENCE_INSUFFICIENT"}


def test_domestic_market_regime_preserves_data_quality_flags(tmp_path):
    payload = market_regime_fixture_payload(data_quality_flags=["QUALITY_WARNING"])
    report = build_market_regime_report(_load(tmp_path, payload))
    assert "QUALITY_WARNING" in report.data_quality_flags


def test_domestic_market_regime_builds_gap_report(tmp_path):
    payload = market_regime_fixture_payload()
    payload["market_regime_input_set"]["sector_evidence"]["sector_return_distribution"] = {}
    report = build_market_regime_gap_report(_load(tmp_path, payload))
    assert "INSUFFICIENT_REGIME_EVIDENCE" in report.gap_categories


def test_domestic_market_regime_builds_safety_report(tmp_path):
    report = build_market_regime_safety_report(_load(tmp_path, market_regime_fixture_payload()))
    assert report.safety_boundary.signal_generation_allowed is False
    assert report.safety_boundary.cloud_llm_allowed is False


def test_domestic_market_regime_stale_core_evidence_fails_closed(tmp_path):
    payload = market_regime_fixture_payload()
    payload["market_regime_input_set"]["index_evidence"]["stale"] = True
    report = build_market_regime_gap_report(_load(tmp_path, payload))
    assert "STALE_REGIME_EVIDENCE" in report.gap_categories


def test_domestic_market_regime_detects_executable_wording(tmp_path):
    payload = market_regime_fixture_payload()
    payload["market_regime_input_set"]["source_trace_references"] = ["BUY_MARKET_SIGNAL"]
    report = build_market_regime_gap_report(_load(tmp_path, payload))
    assert "EXECUTABLE_WORDING_DETECTED" in report.gap_categories


def test_domestic_market_regime_builds_context_reference(tmp_path):
    fixture = _load(tmp_path, market_regime_fixture_payload())
    reference = build_market_regime_context_reference(fixture)
    assert reference.source_evidence_snapshot_id
    assert reference.primary_regime_label.value
