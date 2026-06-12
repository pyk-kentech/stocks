# Signal Enrichment Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich saved and in-memory Candidate Scanner results with cutoff-safe local signals.

**Architecture:** Normalize each local signal source into a shared `TickerSignal`, persist it in SQLite, merge DB and file records with file precedence, and apply conservative candidate score and decision adjustments after the existing scanner pipeline.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite, argparse, pytest

---

### Task 1: Signal Models And Scoring
- [ ] Write failing tests for models, severity scoring, and Toss absolute clamp.
- [ ] Implement `signals.py` and `signal_scoring.py`.
- [ ] Run targeted tests.

### Task 2: Local Signal File Parsers
- [ ] Write failing cutoff and normalization tests for news, dilution, Toss, and flow files.
- [ ] Implement four focused file parser modules.
- [ ] Run targeted tests.

### Task 3: Persistence And Dedupe
- [ ] Write failing repository round-trip and duplicate-storage tests.
- [ ] Add migration-safe `ticker_signals` schema and repository methods.
- [ ] Run targeted tests.

### Task 4: Enrichment And Scanner Integration
- [ ] Write failing tests for DB/file merge, file precedence, ignore DB, cutoff, and decision rules.
- [ ] Implement `signal_enrichment.py` and connect it to `scan_pipeline.py`.
- [ ] Run scanner and enrichment tests.

### Task 5: CLI, Documentation, Verification
- [ ] Write failing CLI tests for ingest, list, and signal-aware scan commands.
- [ ] Implement CLI options and count output.
- [ ] Update README and WORK_SUMMARY.
- [ ] Run full verification and commit.
