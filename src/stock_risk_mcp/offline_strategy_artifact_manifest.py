from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.offline_strategy_models import OfflineStrategyArtifactManifest, OfflineStrategyReadinessStatus


def build_offline_strategy_artifact_manifest(dataset_id: str, store_root: str | None = None) -> OfflineStrategyArtifactManifest:
    base = Path(store_root) if store_root else Path("local_data/offline_strategy")
    relative_paths = [
        str(Path("reports") / f"{dataset_id.lower()}_training_plan.json"),
        str(Path("reports") / f"{dataset_id.lower()}_promotion_gate.json"),
    ]
    del base
    return OfflineStrategyArtifactManifest(
        manifest_id=f"{dataset_id}-OFFLINE-STRATEGY-ARTIFACT-MANIFEST",
        dataset_id=dataset_id,
        relative_paths=relative_paths,
        readiness_status=OfflineStrategyReadinessStatus.ARTIFACT_READY,
    )
