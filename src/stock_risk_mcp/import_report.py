from stock_risk_mcp.import_run import ImportRun


def import_run_report(run: ImportRun) -> dict[str, object]:
    return run.model_dump(mode="json")
