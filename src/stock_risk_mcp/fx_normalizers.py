from __future__ import annotations

from datetime import date

from stock_risk_mcp.normalize_run import NormalizerType
from stock_risk_mcp.normalizer_templates import (
    after_cutoff, mapped, parse_date, row_error, start_normalization, text, upper, write_normalized_output,
)


class GenericFXCSVNormalizer:
    name = "generic-fx-csv"
    normalizer_type = NormalizerType.FX_RATE

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
                normalized.append({
                    "base_currency": upper(mapped(record, columns, "base_currency", True)),
                    "quote_currency": upper(mapped(record, columns, "quote_currency", True)),
                    "date": parse_date(day).isoformat(),
                    "rate": float(mapped(record, columns, "rate", True)),
                    "source_name": text(mapped(record, columns, "source_name"), "unknown"),
                })
            except Exception as error:
                row_error(result, index, error)
        return write_normalized_output(result, normalized, output_dir, kwargs.get("output_name"))
