from stock_risk_mcp.technical_evidence_models import MACDFeatures, TechnicalOHLCVPoint

def _ema(values, period):
    alpha = 2 / (period + 1); out = [values[0]]
    for value in values[1:]: out.append(alpha * value + (1 - alpha) * out[-1])
    return out

def calculate_macd_features(points: list[TechnicalOHLCVPoint]) -> MACDFeatures:
    if len(points) < 26: return MACDFeatures()
    closes = [p.close for p in points]; fast = _ema(closes, 12); slow = _ema(closes, 26)
    line = [a-b for a,b in zip(fast, slow)]; signal = _ema(line, 9); hist = [a-b for a,b in zip(line, signal)]
    slope = hist[-1]-hist[-2] if len(hist)>1 else None
    acceleration = slope-(hist[-2]-hist[-3]) if len(hist)>2 else None
    return MACDFeatures(macd_line=line[-1], macd_signal=signal[-1], macd_histogram=hist[-1],
        macd_histogram_slope=slope, macd_histogram_acceleration=acceleration,
        macd_golden_cross=len(line)>1 and line[-2] <= signal[-2] and line[-1] > signal[-1],
        macd_dead_cross=len(line)>1 and line[-2] >= signal[-2] and line[-1] < signal[-1],
        macd_bullish_reacceleration=hist[-1]>0 and (slope or 0)>0 and (acceleration or 0)>0, histogram_series=hist)
