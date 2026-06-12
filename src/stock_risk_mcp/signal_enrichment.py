from __future__ import annotations

from datetime import date

from pydantic import Field

from stock_risk_mcp.candidate_universe import CandidateDecision, CandidateScanResult
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.signals import (
    SignalDirection,
    SignalEnrichmentResult,
    SignalSeverity,
    TickerSignal,
    observed_date,
    signal_dedupe_key,
)


class SignalMergeResult(StrictModel):
    signals: list[TickerSignal] = Field(default_factory=list)
    db_signal_count: int
    file_signal_count: int
    merged_signal_count: int
    deduped_signal_count: int


def merge_signal_sources(
    db_signals: list[TickerSignal],
    file_signals: list[TickerSignal],
    as_of_date: date,
) -> SignalMergeResult:
    db = [signal for signal in db_signals if observed_date(signal.observed_at) <= as_of_date]
    files = [signal for signal in file_signals if observed_date(signal.observed_at) <= as_of_date]
    by_key = {signal_dedupe_key(signal): signal for signal in db}
    by_key.update({signal_dedupe_key(signal): signal for signal in files})
    return SignalMergeResult(
        signals=list(by_key.values()),
        db_signal_count=len(db),
        file_signal_count=len(files),
        merged_signal_count=len(db) + len(files),
        deduped_signal_count=len(by_key),
    )


class SignalEnricher:
    def enrich_ticker(self, ticker: str, as_of_date: date, signals: list[TickerSignal]) -> SignalEnrichmentResult:
        selected = [
            signal for signal in signals
            if signal.ticker == ticker.strip().upper() and observed_date(signal.observed_at) <= as_of_date
        ]
        critical = any(_negative(signal, SignalSeverity.CRITICAL) for signal in selected)
        high = any(_negative(signal, SignalSeverity.HIGH) for signal in selected)
        delta = sum(signal.score_delta for signal in selected)
        warnings = [warning for signal in selected for warning in signal.warnings]
        return SignalEnrichmentResult(
            ticker=ticker,
            as_of_date=as_of_date,
            signals=selected,
            total_score_delta=delta,
            has_critical_negative=critical,
            has_high_negative=high,
            summary=f"{len(selected)} signals adjusted candidate score by {delta}.",
            warnings=warnings,
        )

    def enrich_scan_results(
        self,
        scan_results: list[CandidateScanResult],
        as_of_date: date,
        signals: list[TickerSignal],
    ) -> list[CandidateScanResult]:
        if not signals:
            return scan_results
        return [self._enrich_result(result, self.enrich_ticker(result.ticker, as_of_date, signals)) for result in scan_results]

    def _enrich_result(
        self,
        result: CandidateScanResult,
        enrichment: SignalEnrichmentResult,
    ) -> CandidateScanResult:
        if not enrichment.signals:
            return result
        decision = result.decision
        if enrichment.has_critical_negative:
            decision = CandidateDecision.EXCLUDE
        elif enrichment.has_high_negative and decision == CandidateDecision.INCLUDE:
            decision = CandidateDecision.WATCH
        signal_reasons = [reason for signal in enrichment.signals for reason in signal.reasons]
        metadata = dict(result.metadata)
        metadata["signal_enrichment"] = enrichment.model_dump(mode="json")
        return result.model_copy(update={
            "score": max(0, min(100, result.score + enrichment.total_score_delta)),
            "decision": decision,
            "reasons": [*result.reasons, *signal_reasons],
            "warnings": [*result.warnings, *enrichment.warnings],
            "metadata": metadata,
        })


def _negative(signal: TickerSignal, severity: SignalSeverity) -> bool:
    return signal.direction == SignalDirection.NEGATIVE and signal.severity == severity
