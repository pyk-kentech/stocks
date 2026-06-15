from stock_risk_mcp.technical_evidence_models import ATRFeatures
def calculate_atr_features(points,period=14):
    if len(points)<=period:return ATRFeatures()
    tr=[max(b.high-b.low,abs(b.high-a.close),abs(b.low-a.close)) for a,b in zip(points,points[1:])]
    atr=sum(tr[:period])/period
    for value in tr[period:]:atr=(atr*(period-1)+value)/period
    stop=2*atr;pct=stop/points[-1].close*100
    return ATRFeatures(atr14=atr,atr_stop_distance=stop,stop_distance_pct=pct,excessive_risk=pct>12)
