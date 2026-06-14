from stock_risk_mcp.kiwoom_readonly_adapter import KiwoomRestReadOnlyAdapter
from stock_risk_mcp.kiwoom_readonly_models import KiwoomEnvironment


def test_kiwoom_readonly_adapter_normalizes_all_fake_outputs() -> None:
    adapter = KiwoomRestReadOnlyAdapter()

    assert adapter.health_check()["status"] == "CONNECTED"
    assert len(adapter.list_readonly_endpoints()) == 7
    assert adapter.get_stock_info("005930")["data"].ticker == "005930"
    assert adapter.get_quote("005930")["data"].price == 70000
    assert adapter.get_rankings("volume", "KOSPI")["data"][0].rank == 1
    assert adapter.get_flow(ticker="005930")["data"][0].foreign_net_buy_amount == 1000
    assert adapter.get_chart_bars("005930", "1m", 1)["data"][0].close == 70000
    assert adapter.list_condition_searches()["data"][0].condition_id == "C1"
    assert adapter.run_condition_search("C1")["data"][0].ticker == "005930"


def test_kiwoom_prod_environment_is_disabled() -> None:
    adapter = KiwoomRestReadOnlyAdapter(environment=KiwoomEnvironment.PROD_DISABLED)
    assert adapter.health_check()["status"] == "DISABLED"
    assert adapter.get_quote("005930")["status"] == "DISABLED"
