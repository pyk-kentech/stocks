from __future__ import annotations

from stock_risk_mcp.adapters.base import CompanyRiskAdapter
from stock_risk_mcp.models import CompanyRisk, DilutionRisk


class MockCompanyRiskAdapter(CompanyRiskAdapter):
    def get_company_risk(self, ticker: str) -> CompanyRisk:
        symbol = ticker.upper()
        if symbol == "BAD":
            return CompanyRisk(
                ticker=symbol,
                nasdaq_noncompliant=True,
                dilution_risk=DilutionRisk.MEDIUM,
            )
        if symbol == "DILUTE":
            return CompanyRisk(
                ticker=symbol,
                dilution_risk=DilutionRisk.HIGH,
                recent_offering_days=20,
                has_warrants=True,
            )
        if symbol == "SAFE":
            return CompanyRisk(ticker=symbol, dilution_risk=DilutionRisk.LOW)
        if symbol == "WATCH":
            return CompanyRisk(ticker=symbol, dilution_risk=DilutionRisk.MEDIUM)
        if symbol == "UNKNOWN":
            return CompanyRisk(ticker=symbol, dilution_risk=DilutionRisk.UNKNOWN)
        return CompanyRisk(ticker=symbol, dilution_risk=DilutionRisk.LOW)
