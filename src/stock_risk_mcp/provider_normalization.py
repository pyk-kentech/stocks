from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import yaml

from stock_risk_mcp.data_import import run_unified_import
from stock_risk_mcp.normalize_run import NormalizeRun, NormalizeRunStatus, NormalizeSourceResult, NormalizerType
from stock_risk_mcp.normalizer_registry import default_normalizer_registry


IMPORT_ARGUMENTS = {
    NormalizerType.PRICE_HISTORY: "price_history_file",
    NormalizerType.NEWS_SIGNAL: "news_signal_file",
    NormalizerType.DILUTION_SIGNAL: "dilution_signal_file",
    NormalizerType.FLOW_SIGNAL: "flow_signal_file",
    NormalizerType.COMPLIANCE: "nasdaq_noncompliant_file",
    NormalizerType.FX_RATE: "fx_rate_file",
}


def load_normalizer_config(path: str | Path) -> list[dict]:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    payload = yaml.safe_load(text) if file_path.suffix.lower() in {".yaml", ".yml"} else json.loads(text)
    sources = payload.get("sources", []) if isinstance(payload, dict) else payload
    if not isinstance(sources, list):
        raise ValueError("Normalizer config must contain a sources list")
    return sources


def normalize_sources(
    sources: list[dict],
    output_dir: str | Path,
    as_of_date: date | None = None,
    *,
    repository=None,
    save: bool = False,
    import_outputs: bool = False,
):
    registry = default_normalizer_registry()
    results = []
    for source in sources:
        name = str(source.get("normalizer", ""))
        input_file = str(source.get("input_file", ""))
        try:
            normalizer = registry.get_normalizer(name)
            result = normalizer.normalize(
                input_file, output_dir, as_of_date,
                columns=source.get("columns", {}), output_name=source.get("output_name"),
            )
        except Exception as error:
            result = NormalizeSourceResult(
                normalizer_name=name or "unknown", normalizer_type=NormalizerType.UNKNOWN,
                input_path=input_file, error_count=1, errors=[str(error)],
            )
        results.append(result)
    outputs = [item for item in results if item.output_path]
    if not sources:
        status, notes = NormalizeRunStatus.NO_INPUT, ["No normalization sources were specified."]
    elif not outputs:
        status, notes = NormalizeRunStatus.FAILED, []
    elif any(item.error_count for item in results):
        status, notes = NormalizeRunStatus.PARTIAL, []
    else:
        status, notes = NormalizeRunStatus.COMPLETED, []
    run = NormalizeRun(
        as_of_date=as_of_date, status=status, source_results=results, notes=notes, completed_at=datetime.now(),
    )
    if save:
        if repository is None:
            raise ValueError("repository is required when save=True")
        repository.save_normalize_run(run)
    import_run = None
    if import_outputs:
        if repository is None:
            raise ValueError("repository is required when import_outputs=True")
        kwargs = {}
        for item in outputs:
            argument = IMPORT_ARGUMENTS.get(item.normalizer_type)
            if argument:
                kwargs.setdefault(argument, []).append(item.output_path)
        import_run = run_unified_import(
            repository, as_of_date=as_of_date,
            empty_input_note="no normalized output files available for import", **kwargs,
        )
    return run, import_run
