import pytest

from stock_risk_mcp.atr_features import calculate_atr_features
from stock_risk_mcp.hma_features import calculate_hma_features
from stock_risk_mcp.ma_trend_features import calculate_ma_features
from stock_risk_mcp.macd_features import calculate_macd_features
from stock_risk_mcp.rsi_features import calculate_rsi_features
from stock_risk_mcp.volume_features import calculate_volume_features
from stock_risk_mcp.divergence_features import calculate_divergence_features
from stock_risk_mcp.technical_evidence_models import TechnicalOHLCVPoint


def points(count=220, volumes=None):
    return [TechnicalOHLCVPoint(timestamp=f"2026-01-01T00:{i // 60:02d}:{i % 60:02d}+00:00", open=100+i, high=101+i, low=99+i, close=100+i, volume=(volumes or [1000]*count)[i]) for i in range(count)]


def test_known_trending_features():
    bars = points()
    macd = calculate_macd_features(bars)
    rsi = calculate_rsi_features(bars)
    ma = calculate_ma_features(bars)
    hma = calculate_hma_features(bars)
    atr = calculate_atr_features(bars)
    assert macd.macd_line is not None and macd.macd_histogram is not None
    assert rsi.rsi_level == pytest.approx(100)
    assert ma.ma20 == pytest.approx(sum(range(300, 320))/20)
    assert ma.ma_alignment_20_50_200 == "BULLISH"
    assert hma.hma100_slope > 0
    assert atr.atr14 == pytest.approx(2)
    assert atr.atr_stop_distance == pytest.approx(4)


def test_volume_and_insufficient_features():
    volumes = [1000]*20 + [2000]
    volume = calculate_volume_features(points(21, volumes))
    assert volume.volume_ratio == pytest.approx(2)
    assert volume.volume_spike_confirmation
    short = points(10)
    assert calculate_ma_features(short).ma20 is None
    assert calculate_rsi_features(short).rsi_level is None
    assert calculate_macd_features(short).macd_line is None


def test_basic_divergence_detects_aligned_swings():
    closes = [10, 9, 8, 9, 10, 9, 7, 9, 10]
    rsi = [50, 40, 30, 40, 50, 45, 35, 45, 50]
    result = calculate_divergence_features(closes, rsi)
    assert result.bullish_rsi_divergence is True
