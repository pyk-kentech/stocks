from __future__ import annotations

from stock_risk_mcp.models import EvaluationReason, Evidence, ReasonType, Severity
from stock_risk_mcp.provenance import evidence_for_reason_code
from stock_risk_mcp.reason_codes import DEFAULT_SEVERITY_BY_TYPE


def make_reason(
    ticker: str,
    reason_type: ReasonType,
    reason_code: str,
    message: str,
    severity: Severity | None = None,
    evidence: Evidence | None = None,
) -> EvaluationReason:
    return EvaluationReason(
        ticker=ticker,
        reason_type=reason_type,
        reason_code=reason_code,
        message=message,
        severity=severity or DEFAULT_SEVERITY_BY_TYPE[reason_type],
        evidence=evidence or evidence_for_reason_code(reason_code),
    )
