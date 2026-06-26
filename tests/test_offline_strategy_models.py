from stock_risk_mcp.offline_strategy_models import OfflineStrategyPipelineInput


def offline_strategy_rows_payload() -> list[dict[str, object]]:
    rows = []
    for index in range(20):
        day = index + 1
        close_price = 70000 + index * 300
        rows.append(
            {
                "row_id": f"offline-strategy-row-{index+1}",
                "dataset_id": "offline-strategy-test",
                "instrument_id": "005930",
                "provider_symbol": "005930",
                "interval": "1D",
                "api_id": "KA10081",
                "observed_at": f"2026-06-{day:02d}T15:30:00+09:00",
                "available_at": f"2026-06-{day:02d}T15:35:00+09:00",
                "open_price": close_price - 100,
                "high_price": close_price + 200,
                "low_price": close_price - 200,
                "close_price": close_price,
                "volume": 1_000_000 + index * 10_000,
                "adjusted": True,
                "adjustment_policy": "UPD_STKPC_TP_1",
                "source_ref": "offline_strategy_fixture.json",
            }
        )
    return rows


def test_offline_strategy_pipeline_input_accepts_direct_rows() -> None:
    payload = {
        "pipeline_id": "offline-strategy-test",
        "dataset_id": "offline-strategy-test",
        "ohlcv_rows": offline_strategy_rows_payload(),
    }
    validated = OfflineStrategyPipelineInput.model_validate(payload)
    assert validated.dataset_id == "OFFLINE-STRATEGY-TEST"
    assert len(validated.ohlcv_rows) == 20
