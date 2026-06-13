from stock_risk_mcp.agent_tools import read_only_tool_manifest
from stock_risk_mcp.report_context import basket_context


class ReadOnlyMCPBridge:
    def __init__(self, repository) -> None:
        self.repository = repository

    def get_pipeline_run(self, pipeline_run_id: str) -> dict:
        return self.repository.get_pipeline_run(pipeline_run_id).model_dump(mode="json")

    def list_alerts(self, pipeline_run_id: str | None = None) -> list[dict]:
        return [item.model_dump(mode="json") for item in self.repository.list_pipeline_alerts(pipeline_run_id)]

    def get_analysis_report(self, report_id: str) -> dict:
        return self.repository.get_analysis_report(report_id).model_dump(mode="json")

    def get_candidate_scan_results(self, scan_run_id: str) -> list[dict]:
        return [item.model_dump(mode="json") for item in self.repository.list_candidate_scan_results(scan_run_id)]

    def get_basket_summary(self, basket_id: str) -> dict:
        return basket_context(self.repository, basket_id)

    def get_policy_evaluation_suite(self, suite_id: str) -> dict:
        return self.repository.get_policy_evaluation_suite(suite_id).model_dump(mode="json")

    def get_agent_context(self, context_id: str) -> dict:
        return self.repository.get_agent_context(context_id).model_dump(mode="json")

    def get_agent_brief(self, brief_id: str) -> dict:
        return self.repository.get_agent_brief(brief_id).model_dump(mode="json")

    def agent_tools(self) -> list[dict[str, object]]:
        return read_only_tool_manifest()
