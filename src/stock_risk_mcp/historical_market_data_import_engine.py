from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from stock_risk_mcp.historical_market_data_models import (
    HistoricalChartImportFile,
    HistoricalChartRawResponse,
    HistoricalMarketDataPipelineInput,
    HistoricalMarketDataProvider,
    HistoricalMarketDataSourceKind,
)


def _load_json_file(file: HistoricalChartImportFile) -> dict[str, object]:
    lowered = file.file_path.strip().lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError("manual response import must be local only")
    path = Path(file.file_path)
    if path.suffix.lower() != ".json":
        raise ValueError("manual response import supports .json only")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("manual response import root must be an object")
    return loaded


def _payload_summary(payload: dict[str, object]) -> dict[str, object]:
    summary: dict[str, object] = {
        "return_code": payload.get("return_code", 0),
        "has_next_key": bool(payload.get("next_key") or payload.get("next-key") or payload.get("nextKey")),
    }
    for key, value in payload.items():
        if isinstance(value, list):
            summary["row_count"] = len(value)
            break
    return summary


def import_historical_chart_responses(pipeline_input: HistoricalMarketDataPipelineInput) -> list[HistoricalChartRawResponse]:
    imported = list(pipeline_input.mocked_responses)
    now = datetime.now().astimezone()
    for file in pipeline_input.manual_response_files:
        payload = _load_json_file(file)
        imported.append(
            HistoricalChartRawResponse(
                response_id=f"{file.import_id}-RESPONSE",
                request_id=file.request_id,
                api_id=file.api_id,
                provider=HistoricalMarketDataProvider.LOCAL_FIXTURE,
                provider_symbol=file.provider_symbol,
                canonical_instrument_id=file.canonical_instrument_id,
                imported_at=now,
                available_at=file.available_at,
                source_kind=HistoricalMarketDataSourceKind.MANUAL_IMPORT_JSON,
                source_ref=file.file_path,
                cont_yn=str(payload.get("cont_yn") or payload.get("cont-yn") or payload.get("contYn") or "N").upper(),
                next_key=str(payload.get("next_key") or payload.get("next-key") or payload.get("nextKey") or "").upper(),
                payload_summary=_payload_summary(payload),
                raw_payload_redacted=True,
                raw_payload=payload,
            )
        )
    return imported
