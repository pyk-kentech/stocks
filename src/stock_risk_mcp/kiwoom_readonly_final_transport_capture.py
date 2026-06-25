from __future__ import annotations

import json
from hashlib import sha1
from pathlib import Path

from stock_risk_mcp.kiwoom_readonly_final_transport_guard import (
    validate_kiwoom_readonly_final_transport_metadata_safety,
)
from stock_risk_mcp.kiwoom_readonly_final_transport_models import (
    KiwoomReadonlyFinalCaptureRecord,
    KiwoomReadonlyFinalCaptureStatus,
    KiwoomReadonlyFinalCapturedFile,
    KiwoomReadonlyFinalRequest,
)


def sanitize_kiwoom_readonly_capture_filename(api_id: str, provider_symbol: str | None, captured_at: str) -> str:
    symbol = (provider_symbol or "NOSYMBOL").replace("/", "_").replace("\\", "_").replace(" ", "_")
    stamp = captured_at.replace(":", "").replace("-", "").replace("+", "_")
    digest = sha1(f"{api_id}:{symbol}:{captured_at}".encode("utf-8")).hexdigest()[:8]
    return f"{api_id.lower()}_{symbol.lower()}_{stamp}_{digest}.json"


def write_kiwoom_readonly_final_capture(
    request: KiwoomReadonlyFinalRequest,
    capture_record: KiwoomReadonlyFinalCaptureRecord,
    *,
    response_body: dict[str, object],
) -> KiwoomReadonlyFinalCaptureRecord:
    if capture_record.status != KiwoomReadonlyFinalCaptureStatus.CAPTURE_READY:
        return capture_record
    capture_dir = Path(request.capture_policy.capture_dir)
    capture_dir.mkdir(parents=True, exist_ok=True)
    if ".." in capture_dir.as_posix().split("/"):
        return capture_record.model_copy(
            update={
                "status": KiwoomReadonlyFinalCaptureStatus.CAPTURE_FAILED,
                "findings": capture_record.findings + ["capture path traversal is blocked"],
            }
        )
    validate_kiwoom_readonly_final_transport_metadata_safety(
        {"source_path": str(capture_dir), "operator_context": request.operator_context},
        context="kiwoom readonly final capture",
    )
    filename = sanitize_kiwoom_readonly_capture_filename(
        request.api_id,
        request.provider_symbol,
        capture_record.captured_at.isoformat() if capture_record.captured_at else "unknown",
    )
    file_path = capture_dir / filename
    file_path.write_text(json.dumps(response_body, ensure_ascii=False, indent=2), encoding="utf-8")
    captured_file = KiwoomReadonlyFinalCapturedFile(
        file_path=str(file_path),
        file_name=file_path.name,
        file_size=file_path.stat().st_size,
        source_ref=file_path.name,
    )
    return capture_record.model_copy(
        update={
            "status": KiwoomReadonlyFinalCaptureStatus.CAPTURE_WRITTEN,
            "captured_files": capture_record.captured_files + [captured_file],
            "source_ref": file_path.name,
        }
    )
