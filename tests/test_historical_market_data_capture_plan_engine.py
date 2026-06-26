from stock_risk_mcp.historical_market_data_capture_plan_engine import build_historical_chart_capture_plan
from stock_risk_mcp.historical_market_data_models import HistoricalMarketDataPipelineInput
from tests.test_historical_market_data_models import historical_market_data_payload, write_manual_daily_payload


def test_historical_market_data_capture_plan_blocks_real_boundary_without_opt_in(tmp_path) -> None:
    manual_file = tmp_path / "manual_daily.json"
    write_manual_daily_payload(manual_file)
    payload = historical_market_data_payload(
        store_root=str(tmp_path / "normalized"),
        raw_lake_root=str(tmp_path / "raw_lake"),
        manual_payload_path=str(manual_file),
    )
    payload["mode"] = "REAL_OPT_IN_BOUNDARY"
    fixture = HistoricalMarketDataPipelineInput.model_validate(payload)

    _, plan = build_historical_chart_capture_plan(fixture)

    assert plan.readiness_status.value == "BLOCKED"
    assert plan.tasks[0].execution_decision.value == "BLOCKED"
