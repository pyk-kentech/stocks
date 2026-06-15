from stock_risk_mcp.technical_evidence_models import RSIFeatures, TechnicalOHLCVPoint

def calculate_rsi_features(points: list[TechnicalOHLCVPoint], period=14) -> RSIFeatures:
    closes=[p.close for p in points]; series:[float|None]=[None]*len(closes)
    if len(closes)<=period: return RSIFeatures(rsi_series=series)
    deltas=[b-a for a,b in zip(closes,closes[1:])]; gain=sum(max(x,0) for x in deltas[:period])/period; loss=sum(max(-x,0) for x in deltas[:period])/period
    def value(): return 100 if loss==0 and gain>0 else 50 if loss==0 else 100-(100/(1+gain/loss))
    series[period]=value()
    for i,delta in enumerate(deltas[period:], start=period+1):
        gain=(gain*(period-1)+max(delta,0))/period; loss=(loss*(period-1)+max(-delta,0))/period; series[i]=value()
    current=series[-1]; previous=series[-2]
    return RSIFeatures(rsi_level=current, rsi_50_reclaim=previous is not None and previous<50<=current,
        rsi_50_loss=previous is not None and previous>=50>current, rsi_overbought=current is not None and current>=70,
        rsi_oversold=current is not None and current<=30, rsi_series=series)
