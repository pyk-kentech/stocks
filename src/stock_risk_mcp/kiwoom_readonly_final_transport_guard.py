from __future__ import annotations


def validate_kiwoom_readonly_final_transport_metadata_safety(metadata: dict[str, object], *, context: str) -> None:
    source_path = str(metadata.get("source_path") or "").strip()
    if not source_path:
        raise ValueError(f"{context} source_path is required")
    lowered = source_path.lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError(f"{context} source_path must remain local-only")
    if lowered.endswith(".parquet"):
        raise ValueError(f"{context} parquet remains unsupported")
    if ".." in lowered.replace("\\", "/").split("/"):
        raise ValueError(f"{context} path traversal is blocked")
    operator_context = str(metadata.get("operator_context") or "").strip()
    if not operator_context:
        raise ValueError(f"{context} operator_context is required")
