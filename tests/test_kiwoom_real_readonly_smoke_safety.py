from pathlib import Path


def test_manual_smoke_is_not_wired_into_automatic_smoke_or_tests():
    root = Path(__file__).resolve().parents[1]
    system_smoke = (root / "src" / "stock_risk_mcp" / "system_smoke.py").read_text(encoding="utf-8").lower()
    assert "kiwoom_real_readonly_smoke" not in system_smoke

    for path in (root / "tests").glob("test_kiwoom_real_readonly_smoke*.py"):
        if path.name == "test_kiwoom_real_readonly_smoke_safety.py":
            continue
        text = path.read_text(encoding="utf-8").lower()
        assert "stdlibkiwoomhttpclient" not in text
        assert "mockapi.kiwoom.com/api/" not in text


def test_manual_smoke_source_has_no_secret_directory_discovery_or_order_runtime():
    root = Path(__file__).resolve().parents[1] / "src" / "stock_risk_mcp"
    text = (root / "kiwoom_real_readonly_smoke.py").read_text(encoding="utf-8").lower()
    for forbidden in (
        "api_key_kiwoom", "stock\\\\api", "stock/api", "rglob(", "os.walk",
        "glob(", "order_submit", "kt10000", "kt00001", "ka10171", "/websocket",
    ):
        assert forbidden not in text
