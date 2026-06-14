from pathlib import Path


def test_real_readonly_http_import_is_isolated_to_transport():
    root = Path(__file__).resolve().parents[1] / "src" / "stock_risk_mcp"
    modules = list(root.glob("kiwoom_real_*.py"))
    for module in modules:
        text = module.read_text(encoding="utf-8").lower()
        if module.name != "kiwoom_real_readonly_transport.py":
            assert "from urllib" not in text
            assert "import urllib" not in text
        assert "api_key_kiwoom" not in text
        assert "os.environ" not in text
        assert "getenv(" not in text
        assert "order_submit" not in text
        assert "account_read" not in text or module.name == "kiwoom_real_readonly_transport.py"
