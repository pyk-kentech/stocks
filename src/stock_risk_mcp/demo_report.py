from __future__ import annotations

import json
from pathlib import Path


DEMO_DISCLAIMER = (
    "This result is for deterministic local system smoke/release validation only. "
    "It is not investment advice and does not execute orders."
)


def demo_result_payload(result) -> dict:
    return {**result.model_dump(mode="json"), "disclaimer": DEMO_DISCLAIMER}


def write_demo_summary(result, output_file: str | Path) -> Path:
    path = Path(output_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(demo_result_payload(result), ensure_ascii=False, indent=2), encoding="utf-8")
    return path
