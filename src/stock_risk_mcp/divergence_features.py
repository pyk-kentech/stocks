from stock_risk_mcp.technical_evidence_models import DivergenceFeatures
def _swings(values,low):
    return [i for i in range(1,len(values)-1) if values[i]<values[i-1] and values[i]<values[i+1]] if low else [i for i in range(1,len(values)-1) if values[i]>values[i-1] and values[i]>values[i+1]]
def calculate_divergence_features(closes,rsi):
    closes=closes[-20:];rsi=rsi[-20:]; lows=_swings(closes,True);highs=_swings(closes,False);reasons=[]
    bull=False;bear=False
    if len(lows)>=2 and rsi[lows[-2]] is not None and rsi[lows[-1]] is not None:bull=closes[lows[-1]]<closes[lows[-2]] and rsi[lows[-1]]>rsi[lows[-2]]
    else:reasons.append("INSUFFICIENT_BULLISH_DIVERGENCE_EVIDENCE")
    if len(highs)>=2 and rsi[highs[-2]] is not None and rsi[highs[-1]] is not None:bear=closes[highs[-1]]>closes[highs[-2]] and rsi[highs[-1]]<rsi[highs[-2]]
    else:reasons.append("INSUFFICIENT_BEARISH_DIVERGENCE_EVIDENCE")
    return DivergenceFeatures(bullish_rsi_divergence=bull,bearish_rsi_divergence=bear,reasons=reasons)
