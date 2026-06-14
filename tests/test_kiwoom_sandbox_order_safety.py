from pathlib import Path


def test_sandbox_order_is_not_wired_to_strategy_or_system_smoke():
    root = Path(__file__).resolve().parents[1]
    for name in ("strategy_optimizer.py", "system_smoke.py"):
        assert "kiwoom_sandbox_order" not in (root / "src" / "stock_risk_mcp" / name).read_text(encoding="utf-8")


def test_sandbox_tests_do_not_use_real_http_transport_or_secret_discovery():
    root = Path(__file__).resolve().parents[1]
    for path in (root / "tests").glob("test_kiwoom_sandbox_order*.py"):
        text = path.read_text(encoding="utf-8").lower()
        if path.name != "test_kiwoom_sandbox_order_safety.py":
            assert "realkiwoomsandboxordertransport" not in text
    service = (root / "src" / "stock_risk_mcp" / "kiwoom_sandbox_order_service.py").read_text(encoding="utf-8").lower()
    for forbidden in ("api_key_kiwoom", "os.walk", "rglob(", "glob(", "kt00001", "ka10001", "/websocket"):
        assert forbidden not in service
