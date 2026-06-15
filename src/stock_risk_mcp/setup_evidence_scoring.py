from stock_risk_mcp.atr_features import calculate_atr_features
from stock_risk_mcp.divergence_features import calculate_divergence_features
from stock_risk_mcp.hma_features import calculate_hma_features
from stock_risk_mcp.ma_trend_features import calculate_ma_features
from stock_risk_mcp.macd_features import calculate_macd_features
from stock_risk_mcp.rsi_features import calculate_rsi_features
from stock_risk_mcp.technical_evidence_models import TechnicalEvidence, TechnicalGrade, TechnicalSeries, TechnicalSetupType
from stock_risk_mcp.volume_features import calculate_volume_features

def build_technical_evidence(series: TechnicalSeries) -> TechnicalEvidence:
    points=series.points;macd=calculate_macd_features(points);rsi=calculate_rsi_features(points);ma=calculate_ma_features(points);hma=calculate_hma_features(points);atr=calculate_atr_features(points);volume=calculate_volume_features(points)
    divergence=calculate_divergence_features([p.close for p in points],rsi.rsi_series)
    trend=(15 if ma.ma_alignment_20_50_200=="BULLISH" else 8 if ma.ma_alignment_20_50_200=="MIXED" else 0)+(10 if hma.hma100_trend_state=="BULLISH" else 5 if hma.hma100_trend_state=="FLAT" else 0)+(5 if ma.price_above_ma20 else 0)
    momentum=min(30,(15 if macd.macd_golden_cross else 0)+(12 if macd.macd_bullish_reacceleration else 0)+(8 if (rsi.rsi_level or 0)>=50 else 0)+(5 if rsi.rsi_50_reclaim else 0)+(5 if divergence.bullish_rsi_divergence else 0))
    vol=min(20,(15 if volume.volume_spike_confirmation else 5 if volume.volume_ratio is not None else 0)+(5 if (volume.dollar_volume_ratio or 0)>=1 else 0))
    risk=20-(10 if (atr.stop_distance_pct or 0)>8 else 0)-(5 if divergence.bearish_rsi_divergence else 0)
    if atr.excessive_risk:risk=0
    scores={"trend":trend,"momentum":momentum,"volume":vol,"risk":max(0,risk)};total=min(100,sum(scores.values()))
    recent=macd.histogram_series[-10:];pullback=len(recent)>=3 and any(x>0 for x in recent[:-2]) and recent[-2]<max(recent[:-2]) and macd.macd_bullish_reacceleration and ((rsi.rsi_level or 0)>=50 or rsi.rsi_50_reclaim) and volume.volume_spike_confirmation
    cross=(macd.macd_golden_cross or macd.macd_bullish_reacceleration) and ((rsi.rsi_level or 0)>=50 or rsi.rsi_50_reclaim) and volume.volume_spike_confirmation and ma.ma_alignment_20_50_200!="BEARISH" and hma.hma100_trend_state!="BEARISH"
    setup=TechnicalSetupType.ROSS_PULLBACK_REACCELERATION if pullback else TechnicalSetupType.ROSS_MOMENTUM_CROSS if cross else TechnicalSetupType.TECHNICAL_NO_TRADE
    hard=len(points)<20 or atr.excessive_risk or (ma.ma_alignment_20_50_200=="BEARISH" and hma.hma100_trend_state=="BEARISH")
    if hard:setup=TechnicalSetupType.TECHNICAL_NO_TRADE
    grade=TechnicalGrade.NO_TRADE if hard or total<40 else TechnicalGrade.A if total>=80 else TechnicalGrade.B if total>=60 else TechnicalGrade.C
    if len(points)<200 and grade==TechnicalGrade.A:grade=TechnicalGrade.B
    if len(points)<50 and grade in (TechnicalGrade.A,TechnicalGrade.B):grade=TechnicalGrade.C
    reasons=["ADVISORY_TECHNICAL_EVIDENCE_ONLY"];warnings=list(divergence.reasons)
    if len(points)<200:warnings.append("LIMITED_LOOKBACK")
    return TechnicalEvidence(ticker=series.ticker,evidence_timestamp=points[-1].timestamp,point_count=len(points),macd=macd,rsi=rsi,ma=ma,hma=hma,atr=atr,volume=volume,divergence=divergence,setup_type=setup,grade=grade,total_score=total,component_scores=scores,reasons=reasons,warnings=warnings)
