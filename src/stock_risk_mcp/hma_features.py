from stock_risk_mcp.technical_evidence_models import HMAFeatures
def _wma(values,n):
    if len(values)<n:return None
    return sum(v*w for v,w in zip(values[-n:],range(1,n+1)))/sum(range(1,n+1))
def calculate_hma_features(points):
    closes=[p.close for p in points]; raw=[]
    for i in range(len(closes)):
        half=_wma(closes[:i+1],50); full=_wma(closes[:i+1],100)
        raw.append(None if half is None or full is None else 2*half-full)
    valid=[x for x in raw if x is not None]; series=[]
    for i in range(len(valid)): series.append(_wma(valid[:i+1],10))
    values=[x for x in series if x is not None]
    if len(values)<2:return HMAFeatures()
    slope=values[-1]-values[-2]; tolerance=closes[-1]*.001; state="FLAT" if abs(slope)<=tolerance else "BULLISH" if slope>0 else "BEARISH"
    return HMAFeatures(hma100=values[-1],hma100_slope=slope,hma100_trend_state=state)
