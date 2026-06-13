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
                self.adjust(item, result, index, record, columns)
                normalized.append(item)
            except Exception as error:
                row_error(result, index, error)
        return write_normalized_output(result, normalized, output_dir, kwargs.get("output_name"))

    def adjust(self, item, result, index, raw_record=None, columns=None):
        pass


class GenericNewsCSVNormalizer(_SignalNormalizer):
    name = "generic-news-csv"
    normalizer_type = NormalizerType.NEWS_SIGNAL
    fields = (
        "ticker", "observed_at", "headline", "title", "source_name", "summary", "url",
        "event_type", "sentiment", "severity", "materiality",
    )

    def adjust(self, item, result, index, raw_record=None, columns=None):
        item["title"] = text(item.get("headline")) or text(item.get("title"))
        item.pop("headline", None)
        if not text(item.get("title")) or not text(item.get("summary")):
            result.warnings.append(f"row {index}: title or summary is missing")
        sentiment = upper(item.get("sentiment"), "NEUTRAL")
        item["sentiment"] = sentiment if sentiment in {"POSITIVE", "NEGATIVE", "NEUTRAL"} else "NEUTRAL"
        item["event_type"] = upper(item.get("event_type"), "UNKNOWN")
        item["materiality"] = upper(item.get("materiality"), "UNKNOWN")
        if "headline" in (columns or {}) and "source_name" in (columns or {}):
            raw_severity = upper(item.get("severity"), "LOW")
            item["severity"] = "LOW" if raw_severity == "INFO" else raw_severity if raw_severity in {"LOW", "MEDIUM", "HIGH", "CRITICAL"} else "LOW"
            item["score_delta"] = _news_provider_score(item["sentiment"], item["severity"])
            item["raw_payload_json"] = dict(raw_record or {})


class GenericDilutionCSVNormalizer(_SignalNormalizer):
    name = "generic-dilution-csv"
    normalizer_type = NormalizerType.DILUTION_SIGNAL
    fields = (
        "ticker", "observed_at", "event_type", "dilution_risk", "severity",
        "source_name", "details", "filing_date", "filing_type", "title", "summary",
        "url", "shares_before", "shares_after", "offering_amount_usd", "accession_number",
    )
    required = ("ticker", "observed_at", "event_type")

    def adjust(self, item, result, index, raw_record=None, columns=None):
        item["event_type"] = upper(item["event_type"])
        if "dilution_risk" in (columns or {}) and "source_name" in (columns or {}):
            risk = upper(item.get("dilution_risk"), "UNKNOWN")
            severity, score_delta = _dilution_provider_mapping(risk)
            item["dilution_risk"] = risk
            item["severity"] = severity
            item["score_delta"] = score_delta
            item["sentiment"] = "NEUTRAL" if risk == "NONE" else "NEGATIVE"
            item["title"] = text(item.get("title")) or f"Dilution risk: {item['event_type'].replace('_', ' ').title()}"
            item["raw_payload_json"] = dict(raw_record or {})
            return
        item["severity"] = upper(item.get("severity"), "HIGH")


class GenericFlowCSVNormalizer(_SignalNormalizer):
    name = "generic-flow-csv"
    normalizer_type = NormalizerType.FLOW_SIGNAL
    fields = (
        "ticker", "observed_at", "foreign_net_buy", "institution_net_buy",
        "foreign_ownership_change", "flow_window_days", "source_name", "title",
        "summary", "url", "foreign_net_buy_amount", "institution_net_buy_amount",
        "retail_net_buy_amount", "foreign_net_buy_shares", "institution_net_buy_shares",
        "retail_net_buy_shares", "currency", "market",
    )

    def adjust(self, item, result, index, raw_record=None, columns=None):
        rich_fields = {
            "foreign_net_buy_amount", "institution_net_buy_amount",
            "foreign_net_buy_shares", "institution_net_buy_shares",
        }
        if "source_name" in (columns or {}) and rich_fields.intersection(columns or {}):
            amount_basis = bool({"foreign_net_buy_amount", "institution_net_buy_amount"}.intersection(columns or {}))
            basis = "AMOUNT" if amount_basis else "SHARES"
            foreign_key = "foreign_net_buy_amount" if amount_basis else "foreign_net_buy_shares"
            institution_key = "institution_net_buy_amount" if amount_basis else "institution_net_buy_shares"
            foreign = _optional_float(item.get(foreign_key)) or 0.0
            institution = _optional_float(item.get(institution_key)) or 0.0
            sentiment, severity, score_delta = _flow_provider_mapping(foreign, institution)
            for key in (
                "foreign_net_buy_amount", "institution_net_buy_amount", "retail_net_buy_amount",
                "foreign_net_buy_shares", "institution_net_buy_shares", "retail_net_buy_shares",
            ):
                item[key] = _optional_float(item.get(key))
            item["sentiment"] = sentiment
            item["severity"] = severity
            item["score_delta"] = score_delta
            item["flow_value_basis"] = basis
            item["provider_record_mode"] = "RICH_FLOW_PROVIDER"
            item["title"] = text(item.get("title")) or f"Foreign and institution flow: {sentiment.title()}"
            item["raw_payload_json"] = dict(raw_record or {})
            return
        for key in ("foreign_net_buy", "institution_net_buy", "foreign_ownership_change"):
            item[key] = float(item[key] or 0)
        item["flow_window_days"] = int(item["flow_window_days"] or 0)


def _news_provider_score(sentiment: str, severity: str) -> int:
    if sentiment == "POSITIVE":
        return {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 3}[severity]
    if sentiment == "NEGATIVE":
        return {"LOW": -1, "MEDIUM": -3, "HIGH": -5, "CRITICAL": -10}[severity]
    return 0


def _dilution_provider_mapping(risk: str) -> tuple[str, int]:
    return {
        "NONE": ("LOW", 0),
        "LOW": ("LOW", -1),
        "MEDIUM": ("MEDIUM", -3),
        "HIGH": ("HIGH", -7),
        "CRITICAL": ("CRITICAL", -10),
        "UNKNOWN": ("HIGH", -7),
    }.get(upper(risk, "UNKNOWN"), ("HIGH", -7))


def _flow_provider_mapping(foreign: float, institution: float) -> tuple[str, str, int]:
    if foreign > 0 and institution > 0:
        return "POSITIVE", "LOW", 2
    if foreign < 0 and institution < 0:
        return "NEGATIVE", "MEDIUM", -3
    if (foreign > 0 and institution == 0) or (institution > 0 and foreign == 0):
        return "POSITIVE", "LOW", 1
    if (foreign < 0 and institution == 0) or (institution < 0 and foreign == 0):
        return "NEGATIVE", "LOW", -1
    return "NEUTRAL", "LOW", 0


def _optional_float(value):
    return float(value) if value not in (None, "") else None
