from pathlib import Path


def test_evidence_modules_have_no_network_credentials_account_read_strategy_or_secret_search():
    root = Path(__file__).resolve().parents[1] / "src" / "stock_risk_mcp"
    modules = (
        root / "kiwoom_official_sell_schema_evidence.py",
        root / "kiwoom_official_sell_schema_evidence_service.py",
    )
    forbidden = (
        "requests", "httpx", "urllib", "load_kiwoom_credentials", "token_provider",
        "account_read", "strategy", "rglob(", "glob(", "os.walk", "api_key_kiwoom",
    )
    for module in modules:
        text = module.read_text(encoding="utf-8").lower()
        assert all(item not in text for item in forbidden)
