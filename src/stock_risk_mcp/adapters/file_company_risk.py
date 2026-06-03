from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.adapters.base import CompanyRiskAdapter
from stock_risk_mcp.adapters.file_utils import find_record_by_ticker, load_records
from stock_risk_mcp.adapters.nasdaq_noncompliant_file import NasdaqNoncompliantFileAdapter
from stock_risk_mcp.models import CompanyRisk


class FileCompanyRiskAdapter(CompanyRiskAdapter):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.records = load_records(self.path)

    def get_company_risk(self, ticker: str) -> CompanyRisk:
        return CompanyRisk.model_validate(find_record_by_ticker(self.records, ticker))


class FileCompanyRiskWithComplianceAdapter(CompanyRiskAdapter):
    def __init__(
        self,
        base_company_risk_adapter: CompanyRiskAdapter,
        compliance_adapter: NasdaqNoncompliantFileAdapter | None,
    ) -> None:
        self.base_company_risk_adapter = base_company_risk_adapter
        self.compliance_adapter = compliance_adapter

    def get_company_risk(self, ticker: str) -> CompanyRisk:
        company = self.base_company_risk_adapter.get_company_risk(ticker)
        if self.compliance_adapter is None:
            return company

        status = self.compliance_adapter.is_noncompliant(ticker)
        if not status.nasdaq_noncompliant:
            return company
        return company.model_copy(
            update={
                "nasdaq_noncompliant": True,
                "nasdaq_noncompliance_evidence": status.evidence,
            }
        )
