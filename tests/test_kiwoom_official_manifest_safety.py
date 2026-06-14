from pathlib import Path

from stock_risk_mcp.kiwoom_mock_execution_transport import KIWOOM_MOCK_EXECUTION_ENDPOINTS
from stock_risk_mcp.kiwoom_official_manifest import load_kiwoom_official_manifest
from stock_risk_mcp.kiwoom_readonly_allowlist import KiwoomReadOnlyAllowlist


def test_official_manifest_is_data_only_and_does_not_modify_runtime_allowlists() -> None:
    official_paths = {item.path for item in load_kiwoom_official_manifest().endpoints}
    readonly_paths = {item.path for item in KiwoomReadOnlyAllowlist().list_endpoints()}
    assert official_paths.isdisjoint(readonly_paths)
    assert official_paths.isdisjoint(KIWOOM_MOCK_EXECUTION_ENDPOINTS.values())


def test_official_manifest_modules_have_no_transport_secret_or_runtime_integration() -> None:
    root = Path(__file__).resolve().parents[1]
    modules = list((root / "src" / "stock_risk_mcp").glob("kiwoom_official*.py"))
    forbidden_imports = ("requests", "httpx", "urllib", "pykiwoom", "win32com")
    for module in modules:
        text = module.read_text(encoding="utf-8").lower()
        assert all(f"import {name}" not in text for name in forbidden_imports)
        assert all(f"from {name}" not in text for name in forbidden_imports)
        assert "os.environ" not in text
        assert "getenv(" not in text
        assert "api_key_kiwoom" not in text
    for name in ("kiwoom_rest_client.py", "kiwoom_mock_execution_adapter.py", "strategy_optimizer.py"):
        assert "kiwoom_official_manifest" not in (
            root / "src" / "stock_risk_mcp" / name
        ).read_text(encoding="utf-8")
