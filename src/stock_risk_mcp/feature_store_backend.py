from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from stock_risk_mcp.feature_store_guard import validate_feature_store_root
from stock_risk_mcp.feature_store_models import (
    FeatureStoreBackend,
    FeatureStoreBackendCapabilityReport,
    FeatureStoreBackendCapabilityRow,
    FeatureStoreBackendStatus,
    FeatureStoreDatasetProfile,
    FeatureStoreFormat,
    FeatureStoreMaterializationResult,
    FeatureStorePipelineInput,
    FeatureStoreRootPolicy,
)


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def build_feature_store_backend_capability_report(
    pipeline_input: FeatureStorePipelineInput,
    *,
    repo_root: Path,
) -> FeatureStoreBackendCapabilityReport:
    safe, policy = validate_feature_store_root(pipeline_input.store_root, repo_root=repo_root)
    root_policy = FeatureStoreRootPolicy(policy)
    rows: list[FeatureStoreBackendCapabilityRow] = [
        FeatureStoreBackendCapabilityRow(
            backend=FeatureStoreBackend.IN_MEMORY,
            status=FeatureStoreBackendStatus.AVAILABLE,
            allowed_formats=[FeatureStoreFormat.JSON],
            root_policy=root_policy,
            dataset_profile_compatible=True,
            notes="manifest-first in-memory mode is always available",
        ),
        FeatureStoreBackendCapabilityRow(
            backend=FeatureStoreBackend.JSON,
            status=FeatureStoreBackendStatus.AVAILABLE if safe else FeatureStoreBackendStatus.REJECTED,
            allowed_formats=[FeatureStoreFormat.JSON, FeatureStoreFormat.JSONL],
            root_policy=root_policy,
            dataset_profile_compatible=True,
            notes="local json materialization available under safe roots only",
        ),
    ]
    parquet_ok = _has_module("pyarrow")
    rows.append(
        FeatureStoreBackendCapabilityRow(
            backend=FeatureStoreBackend.PARQUET,
            status=FeatureStoreBackendStatus.AVAILABLE if (safe and parquet_ok) else FeatureStoreBackendStatus.MISSING_DEPENDENCY if safe else FeatureStoreBackendStatus.REJECTED,
            missing_modules=[] if parquet_ok else ["PYARROW"],
            allowed_formats=[FeatureStoreFormat.PARQUET],
            root_policy=root_policy,
            dataset_profile_compatible=pipeline_input.dataset_profile != FeatureStoreDatasetProfile.FULL_INTRADAY_PROFILE,
            notes="parquet is optional and must not be the source of truth",
        )
    )
    duckdb_ok = _has_module("duckdb")
    rows.append(
        FeatureStoreBackendCapabilityRow(
            backend=FeatureStoreBackend.DUCKDB,
            status=FeatureStoreBackendStatus.AVAILABLE if (safe and duckdb_ok) else FeatureStoreBackendStatus.MISSING_DEPENDENCY if safe else FeatureStoreBackendStatus.REJECTED,
            missing_modules=[] if duckdb_ok else ["DUCKDB"],
            allowed_formats=[FeatureStoreFormat.DUCKDB_TABLE],
            root_policy=root_policy,
            dataset_profile_compatible=pipeline_input.dataset_profile != FeatureStoreDatasetProfile.FULL_INTRADAY_PROFILE,
            notes="duckdb is optional and used only for safe local materialization",
        )
    )
    polars_ok = _has_module("polars")
    rows.append(
        FeatureStoreBackendCapabilityRow(
            backend=FeatureStoreBackend.POLARS,
            status=FeatureStoreBackendStatus.AVAILABLE if (safe and polars_ok) else FeatureStoreBackendStatus.MISSING_DEPENDENCY if safe else FeatureStoreBackendStatus.REJECTED,
            missing_modules=[] if polars_ok else ["POLARS"],
            allowed_formats=[FeatureStoreFormat.POLARS_FRAME],
            root_policy=root_policy,
            dataset_profile_compatible=pipeline_input.dataset_profile != FeatureStoreDatasetProfile.FULL_INTRADAY_PROFILE,
            notes="polars is optional and supports bounded local materialization only",
        )
    )
    return FeatureStoreBackendCapabilityReport(
        report_id=f"{pipeline_input.dataset_id}-BACKEND-CAPABILITY-REPORT",
        dataset_profile=pipeline_input.dataset_profile,
        rows=rows,
    )


def materialize_feature_store_manifest(
    pipeline_input: FeatureStorePipelineInput,
    training_manifest,
    training_rows,
    *,
    repo_root: Path,
    capability_report: FeatureStoreBackendCapabilityReport,
) -> FeatureStoreMaterializationResult:
    safe, policy = validate_feature_store_root(pipeline_input.store_root, repo_root=repo_root)
    root_policy = FeatureStoreRootPolicy(policy)
    requested = pipeline_input.requested_backends or [FeatureStoreBackend.IN_MEMORY]
    if not safe:
        return FeatureStoreMaterializationResult(
            result_id=f"{pipeline_input.dataset_id}-MATERIALIZATION-RESULT",
            dataset_id=pipeline_input.dataset_id,
            requested_backends=requested,
            selected_backend=FeatureStoreBackend.IN_MEMORY,
            status=FeatureStoreBackendStatus.REJECTED,
            materialized_paths=[],
            row_count_written=0,
            root_policy=root_policy,
            degradation_reasons=["unsafe materialization root rejected"],
        )

    root = (repo_root / pipeline_input.store_root) if not Path(pipeline_input.store_root).is_absolute() else Path(pipeline_input.store_root)
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / f"{pipeline_input.dataset_id.lower()}_training_manifest.json"
    rows_path = root / f"{pipeline_input.dataset_id.lower()}_training_rows.jsonl"
    manifest_path.write_text(training_manifest.model_dump_json(indent=2), encoding="utf-8")
    rows_path.write_text(
        "\n".join(json.dumps(row.model_dump(mode="json"), ensure_ascii=True) for row in training_rows) + ("\n" if training_rows else ""),
        encoding="utf-8",
    )
    status = FeatureStoreBackendStatus.AVAILABLE
    selected = FeatureStoreBackend.JSON
    reasons: list[str] = []
    if FeatureStoreBackend.JSON not in requested and FeatureStoreBackend.IN_MEMORY in requested:
        selected = FeatureStoreBackend.IN_MEMORY
    else:
        for backend in requested:
            row = next((item for item in capability_report.rows if item.backend == backend), None)
            if row and row.status == FeatureStoreBackendStatus.AVAILABLE:
                selected = backend
                break
        else:
            status = FeatureStoreBackendStatus.DEPENDENCY_GAP
            selected = FeatureStoreBackend.JSON
            reasons.append("optional backend dependencies unavailable; json manifest still produced")
    return FeatureStoreMaterializationResult(
        result_id=f"{pipeline_input.dataset_id}-MATERIALIZATION-RESULT",
        dataset_id=pipeline_input.dataset_id,
        requested_backends=requested,
        selected_backend=selected,
        status=status,
        materialized_paths=[str(manifest_path), str(rows_path)],
        row_count_written=len(training_rows),
        root_policy=root_policy,
        degradation_reasons=reasons,
    )
