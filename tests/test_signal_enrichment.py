from datetime import date, datetime

from stock_risk_mcp.candidate_universe import CandidateDecision, CandidateScanResult
from stock_risk_mcp.signal_enrichment import SignalEnricher, merge_signal_sources
from stock_risk_mcp.signals import SignalDirection, SignalSeverity, SignalType, TickerSignal


def test_merge_dedupes_with_file_precedence_and_ignores_future() -> None:
    as_of = date(2026, 1, 2)
    db = [_signal("AAA", 5, source="same"), _signal("FUT", 10, observed="2026-01-03")]
    file = [_signal("AAA", 10, source="same")]

    merged = merge_signal_sources(db, file, as_of)

    assert merged.db_signal_count == 1
    assert merged.file_signal_count == 1
    assert merged.merged_signal_count == 2
    assert merged.deduped_signal_count == 1
    assert merged.signals[0].score_delta == 10


def test_enricher_applies_decision_rules_without_promoting_excluded() -> None:
    results = [
        _candidate("CRIT", CandidateDecision.INCLUDE, 80),
        _candidate("HIGH", CandidateDecision.INCLUDE, 80),
        _candidate("OUT", CandidateDecision.EXCLUDE, 30),
    ]
    signals = [
        _signal("CRIT", -100, SignalSeverity.CRITICAL, SignalDirection.NEGATIVE),
        _signal("HIGH", -15, SignalSeverity.HIGH, SignalDirection.NEGATIVE),
        _signal("OUT", 10, SignalSeverity.HIGH, SignalDirection.POSITIVE),
    ]

    enriched = SignalEnricher().enrich_scan_results(results, date(2026, 1, 2), signals)

    assert enriched[0].decision == CandidateDecision.EXCLUDE
    assert enriched[1].decision == CandidateDecision.WATCH
    assert enriched[2].decision == CandidateDecision.EXCLUDE
    assert enriched[2].score == 40
    assert enriched[0].metadata["signal_enrichment"]["has_critical_negative"] is True


def _candidate(ticker, decision, score):
    return CandidateScanResult(scan_run_id="run", ticker=ticker, as_of_date=date(2026, 1, 2), decision=decision, score=score)


def _signal(ticker, delta, severity=SignalSeverity.MEDIUM, direction=SignalDirection.POSITIVE, source="source", observed="2026-01-01"):
    return TickerSignal(
        ticker=ticker, signal_type=SignalType.NEWS, as_of_date=date(2026, 1, 2),
        observed_at=datetime.fromisoformat(observed), direction=direction, severity=severity,
        score_delta=delta, source_name=source, title="same", raw_event_type="EVENT",
    )
