from pathlib import Path


def test_domestic_replay_core_has_no_forbidden_imports_or_artifact_creation():
    root = Path("/home/yoonkeun/stocks/src/stock_risk_mcp")
    for name in [
        "domestic_replay_models.py",
        "domestic_replay_fixture.py",
        "domestic_replay_engine.py",
        "domestic_replay_service.py",
    ]:
        content = (root / name).read_text(encoding="utf-8").lower()
        for forbidden in [
            "orderintent",
            "broker submit",
            "websocket",
            "transformers",
            "ollama",
            "llama.cpp",
        ]:
            assert forbidden not in content
