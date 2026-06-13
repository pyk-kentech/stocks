from __future__ import annotations

from datetime import date

from stock_risk_mcp.normalize_run import NormalizerType
from stock_risk_mcp.normalizer_templates import (
    after_cutoff, mapped, parse_date, row_error, start_normalization, write_normalized_output,
)


class GenericPriceCSVNormalizer:
    name = "generic-price-csv"
    normalizer_type = NormalizerType.PRICE_HISTORY

    def normalize(self, input_path, output_dir, as_of_date: date | None = None, **kwargs):
        result, records = start_normalization(self.name, self.normalizer_type, input_path)
        if records is None:
            return result
        columns = kwargs.get("columns", {})
        normalized = []
        for index, record in enumerate(records, 1):
            try:
                day = mapped(record, columns, "date", True)
                if after_cutoff(day, as_of_date):
                    result.skipped_count += 1
                    continue
                close = float(mapped(record, columns, "close", True))
                volume = float(mapped(record, columns, "volume", True))
                values = {}
                for key in ("open", "high", "low"):
                    raw = mapped(record, columns, key)
                    if raw in (None, ""):
                        result.warnings.append(f"row {index}: {key} missing; close was used")
                        raw = close
                    values[key] = float(raw)
                normalized.append({
                    "ticker": str(mapped(record, columns, "ticker", True)).strip().upper(),
                    "date": parse_date(day).isoformat(), **values, "close": close, "volume": volume,
                })
            except Exception as error:
                row_error(result, index, error)
        return write_normalized_output(result, normalized, output_dir, kwargs.get("output_name"))
