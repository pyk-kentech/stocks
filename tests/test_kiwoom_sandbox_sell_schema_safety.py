from pathlib import Path


def test_sell_schema_and_dry_run_modules_have_no_network_secret_account_or_strategy_dependency():
    root = Path(__file__).resolve().parents[1] / "src" / "stock_risk_mcp"
    modules = (
        root / "kiwoom_sandbox_sell_schema.py",
        root / "kiwoom_sandbox_sell_schema_verifier.py",
        root / "kiwoom_sandbox_sell_dry_run.py",
    )
    forbidden = (
        "requests", "httpx", "urllib", "load_kiwoom_credentials", "token_provider",
        "authorization_header", "account_read", "strategy", "transport",
    )
    for module in modules:
        text = module.read_text(encoding="utf-8").lower()
        assert all(item not in text for item in forbidden)
