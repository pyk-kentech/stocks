from __future__ import annotations

from datetime import date

from stock_risk_mcp.normalize_run import NormalizerType
from stock_risk_mcp.normalizer_templates import (
    after_cutoff, mapped, parse_date, row_error, start_normalization, text, upper, write_normalized_output,
)


class _SignalNormalizer:
    fields: tuple[str, ...] = ()
    required: tuple[str, ...] = ("ticker", "observed_at")

    def normalize(self, input_path, output_dir, as_of_date: date | None = None, **kwargs):
        result, records = start_normalization(self.name, self.normalizer_type, input_path)
        if records is None:
            return result
        columns = kwargs.get("columns", {})
        normalized = []
        for index, record in enumerate(records, 1):
            try:
                observed = mapped(record, columns, "observed_at", True)
                if after_cutoff(observed, as_of_date):
                    result.skipped_count += 1
                    continue
                item = {}
                for field in self.fields:
                    value = mapped(record, columns, field, field in self.required)
                    item[field] = value
                item["ticker"] = upper(item["ticker"])
                item["observed_at"] = str(observed)
                self.adjust(item, result, index)
                normalized.append(item)
            except Exception as error:
                row_error(result, index, error)
        return write_normalized_output(result, normalized, output_dir, kwargs.get("output_name"))

    def adjust(self, item, result, index):
        pass


class GenericNewsCSVNormalizer(_SignalNormalizer):
    name = "generic-news-csv"
    normalizer_type = NormalizerType.NEWS_SIGNAL
    fields = ("ticker", "observed_at", "title", "summary", "event_type", "sentiment", "materiality")

    def adjust(self, item, result, index):
        if not text(item.get("title")) or not text(item.get("summary")):
            result.warnings.append(f"row {index}: title or summary is missing")
        sentiment = upper(item.get("sentiment"), "NEUTRAL")
        item["sentiment"] = sentiment if sentiment in {"POSITIVE", "NEGATIVE", "NEUTRAL"} else "NEUTRAL"
        item["event_type"] = upper(item.get("event_type"), "UNKNOWN")
        item["materiality"] = upper(item.get("materiality"), "UNKNOWN")


class GenericDilutionCSVNormalizer(_SignalNormalizer):
    name = "generic-dilution-csv"
    normalizer_type = NormalizerType.DILUTION_SIGNAL
    fields = ("ticker", "observed_at", "event_type", "severity", "details")
    required = ("ticker", "observed_at", "event_type")

    def adjust(self, item, result, index):
        item["event_type"] = upper(item["event_type"])
        item["severity"] = upper(item.get("severity"), "HIGH")


class GenericFlowCSVNormalizer(_SignalNormalizer):
    name = "generic-flow-csv"
    normalizer_type = NormalizerType.FLOW_SIGNAL
    fields = (
        "ticker", "observed_at", "foreign_net_buy", "institution_net_buy",
        "foreign_ownership_change", "flow_window_days",
    )

    def adjust(self, item, result, index):
        for key in ("foreign_net_buy", "institution_net_buy", "foreign_ownership_change"):
            item[key] = float(item[key] or 0)
        item["flow_window_days"] = int(item["flow_window_days"] or 0)
