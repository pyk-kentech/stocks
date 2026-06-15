import statistics
from stock_risk_mcp.technical_evidence_models import VolumeFeatures
def calculate_volume_features(points):
    latest=points[-1] if points else None
    if latest is None:return VolumeFeatures()
    dollar=latest.close*latest.volume
    if len(points)<21:return VolumeFeatures(dollar_volume=dollar)
    prior=points[-21:-1];av=statistics.fmean(p.volume for p in prior);adv=statistics.fmean(p.close*p.volume for p in prior)
    vr=latest.volume/av if av else None;dr=dollar/adv if adv else None; available=[x for x in (vr,dr) if x is not None]
    return VolumeFeatures(volume_ratio=vr,dollar_volume=dollar,dollar_volume_ratio=dr,
        volume_spike_confirmation=any(x>=1.5 for x in available),volume_dry_up_warning=len(available)==2 and all(x<.7 for x in available))
