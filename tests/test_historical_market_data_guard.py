import pytest

from stock_risk_mcp.historical_market_data_guard import validate_real_capture_opt_in, validate_safe_local_root
from stock_risk_mcp.historical_market_data_models import HistoricalMarketDataMode, HistoricalMarketDataOptIn


def test_validate_safe_local_root_accepts_tmp(tmp_path) -> None:
    resolved = validate_safe_local_root(str(tmp_path / "historical_market_data"))
    assert resolved == (tmp_path / "historical_market_data").resolve()


def test_validate_safe_local_root_rejects_non_safe_root() -> None:
    with pytest.raises(ValueError):
        validate_safe_local_root("/home/yoonkeun/unsafe-output")


def test_validate_real_capture_opt_in_blocks_missing_flags() -> None:
    reasons = validate_real_capture_opt_in(
        HistoricalMarketDataMode.REAL_OPT_IN_BOUNDARY,
        HistoricalMarketDataOptIn(),
    )
    assert "ALLOW_REAL_CHART_CAPTURE_MISSING" in reasons
