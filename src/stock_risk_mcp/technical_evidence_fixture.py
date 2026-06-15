import json
from pathlib import Path
from stock_risk_mcp.technical_evidence_models import TechnicalFixture

def load_technical_fixture(path: str | Path) -> TechnicalFixture:
    try:
        return TechnicalFixture.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
    except Exception as exc:
        raise ValueError(f"invalid technical evidence fixture: {exc}") from exc
