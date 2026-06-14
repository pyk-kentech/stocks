from pathlib import Path

from stock_risk_mcp.kiwoom_mock_execution_transport import KIWOOM_MOCK_EXECUTION_ENDPOINTS


def test_kiwoom_mock_execution_endpoints_and_modules_are_local_only() -> None:
    assert set(KIWOOM_MOCK_EXECUTION_ENDPOINTS.values()) == {
        "/kiwoom-mock/order/submit", "/kiwoom-mock/order/cancel", "/kiwoom-mock/order/status",
    }
    root = Path(__file__).resolve().parents[1]
    modules = list((root / "src" / "stock_risk_mcp").glob("kiwoom_mock_execution*.py"))
    forbidden_imports = ("requests", "httpx", "urllib", "pykiwoom", "win32com")
    for module in modules:
        text = module.read_text(encoding="utf-8").lower()
        assert all(f"import {name}" not in text for name in forbidden_imports)
        assert all(f"from {name}" not in text for name in forbidden_imports)
        assert "os.environ" not in text
        assert "getenv(" not in text
        assert "api_key_kiwoom" not in text
    assert "kiwoom_mock_execution" not in (
        root / "src" / "stock_risk_mcp" / "strategy_optimizer.py"
    ).read_text(encoding="utf-8")
