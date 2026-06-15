import hashlib
from pathlib import Path
from stock_risk_mcp.setup_evidence_scoring import build_technical_evidence
from stock_risk_mcp.technical_evidence_fixture import load_technical_fixture
from stock_risk_mcp.technical_evidence_models import TechnicalEvidenceResult

def run_technical_evidence(fixture_file, output_file=None):
    path=Path(fixture_file);fixture=load_technical_fixture(path)
    result=TechnicalEvidenceResult(fixture_checksum=hashlib.sha256(path.read_bytes()).hexdigest(),as_of_timestamp=fixture.as_of_timestamp,evidence=[build_technical_evidence(item) for item in fixture.series])
    if output_file:Path(output_file).write_text(result.model_dump_json(indent=2),encoding="utf-8")
    return result

def load_technical_evidence_result(path):
    try:return TechnicalEvidenceResult.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:raise ValueError(f"invalid technical evidence result: {exc}") from exc
