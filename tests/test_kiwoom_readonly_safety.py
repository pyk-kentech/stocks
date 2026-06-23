from pathlib import Path

from stock_risk_mcp.kiwoom_readonly_allowlist import FORBIDDEN_TERMS, KiwoomReadOnlyAllowlist


def test_kiwoom_allowlist_is_internal_readonly_and_has_no_forbidden_terms() -> None:
    endpoints = KiwoomReadOnlyAllowlist().list_endpoints()
    assert len(endpoints) == 7
    for endpoint in endpoints:
        text = f"{endpoint.api_id} {endpoint.path} {endpoint.description}".lower()
        assert endpoint.api_id.startswith("RO_")
        assert endpoint.path.startswith("/readonly/")
        assert all(term not in text for term in FORBIDDEN_TERMS)


def test_kiwoom_modules_have_no_network_sdk_secret_or_execution_integration() -> None:
    root = Path(__file__).resolve().parents[1]
    modules = [
        path for path in (root / "src" / "stock_risk_mcp").glob("kiwoom_*.py")
        if not path.name.startswith("kiwoom_real_")
    ]
    forbidden_imports = ("urllib", "requests", "httpx", "pykiwoom", "win32com")
    allowed_network_import_modules = {"kiwoom_mock_oauth_execution_client.py"}
    allowed_env_modules = {"kiwoom_mock_oauth_execution_engine.py"}
    for module in modules:
        text = module.read_text(encoding="utf-8").lower()
        if module.name in allowed_network_import_modules:
            assert all(f"import {item}" not in text for item in forbidden_imports if item != "urllib")
            assert all(f"from {item}" not in text for item in forbidden_imports if item != "urllib")
        else:
            assert all(f"import {item}" not in text for item in forbidden_imports)
            assert all(f"from {item}" not in text for item in forbidden_imports)
        assert "api_key_kiwoom" not in text
        if module.name not in allowed_env_modules:
            assert "os.environ" not in text
            assert "getenv(" not in text
    for name in ("strategy_optimizer.py", "execution_gate.py", "broker_adapter_service.py"):
        assert "kiwoom_readonly" not in (root / "src" / "stock_risk_mcp" / name).read_text(encoding="utf-8")


def test_gitignore_contains_local_broker_secret_patterns() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / ".gitignore").read_text(encoding="utf-8")
    for pattern in ("api_key_kiwoom/", "*.secret", "*.secrets", "*.key", "*.pem", ".env", "!.env.example"):
        assert pattern in text
