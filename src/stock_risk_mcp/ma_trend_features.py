import statistics
from stock_risk_mcp.technical_evidence_models import MAFeatures, TechnicalOHLCVPoint
def calculate_ma_features(points):
    closes=[p.close for p in points]
    def sma(n): return statistics.fmean(closes[-n:]) if len(closes)>=n else None
    a,b,c=sma(20),sma(50),sma(200)
    state="INSUFFICIENT_DATA" if None in (a,b,c) else "BULLISH" if a>b>c else "BEARISH" if a<b<c else "MIXED"
    latest=closes[-1] if closes else None
    return MAFeatures(ma20=a,ma50=b,ma200=c,ma_alignment_20_50_200=state,
        price_above_ma20=latest>a if a else None,price_above_ma50=latest>b if b else None,price_above_ma200=latest>c if c else None)
