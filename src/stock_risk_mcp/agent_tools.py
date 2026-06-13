def read_only_tool_manifest() -> list[dict[str, object]]:
    return [
        {"name": name, "read_only": True}
        for name in (
            "get_pipeline_run", "list_alerts", "get_analysis_report", "get_candidate_scan_results",
            "get_basket_summary", "get_policy_evaluation_suite", "get_agent_context", "get_agent_brief",
        )
    ]
