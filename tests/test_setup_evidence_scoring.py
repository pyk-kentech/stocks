from stock_risk_mcp.setup_evidence_scoring import build_technical_evidence
from stock_risk_mcp.technical_evidence_models import TechnicalGrade, TechnicalSeries
from tests.test_technical_evidence_fixture import payload


def series(count):
    value=payload(20)["series"][0]
    points=[]
    for i in range(count):
        close=100+i
        points.append({"timestamp":f"2026-01-01T{i//3600:02d}:{(i//60)%60:02d}:{i%60:02d}+00:00","open":close,"high":close+1,"low":close-1,"close":close,"volume":2000 if i==count-1 else 1000})
    return TechnicalSeries.model_validate({"ticker":"ABC","points":points})


def test_scoring_is_advisory_deterministic_and_grade_capped():
    complete=build_technical_evidence(series(220))
    repeat=build_technical_evidence(series(220))
    limited=build_technical_evidence(series(60))
    sparse=build_technical_evidence(series(30))
    insufficient=build_technical_evidence(series(10))
    assert complete.total_score==repeat.total_score
    assert complete.grade in {TechnicalGrade.A,TechnicalGrade.B,TechnicalGrade.C,TechnicalGrade.NO_TRADE}
    assert limited.grade != TechnicalGrade.A
    assert sparse.grade in {TechnicalGrade.C,TechnicalGrade.NO_TRADE}
    assert insufficient.grade == TechnicalGrade.NO_TRADE
    assert insufficient.setup_type.value == "TECHNICAL_NO_TRADE"
    assert set(complete.component_scores)=={"trend","momentum","volume","risk"}
