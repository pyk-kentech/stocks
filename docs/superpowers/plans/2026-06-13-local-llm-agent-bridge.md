# Local LLM Agent Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only deterministic agent bridge with opt-in loopback-only local LLM invocation.

**Architecture:** Typed contexts, prompts, and briefs wrap stored research evidence. A guarded local client defaults to DRY_RUN, validates loopback endpoints before transport, and persists only on explicit request.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite, argparse, urllib, pytest

---

### Task 1: Models, Guardrails, And Persistence

- [ ] Write failing model, endpoint validation, and repository round-trip tests.
- [ ] Implement agent/local-LLM models, fixed guardrails, schema, and repository methods.
- [ ] Run focused tests.

### Task 2: Context, Prompt, Brief, Tools, And MCP Bridge

- [ ] Write failing deterministic report/pipeline context, prompt, brief, read-only manifest, and bridge tests.
- [ ] Implement the read-only conversion and lookup surfaces.
- [ ] Run focused tests.

### Task 3: Local Client And CLI

- [ ] Write failing DRY_RUN, blocked endpoint, failed local call, CLI save, and list command tests.
- [ ] Implement injectable local HTTP transport and agent CLI commands.
- [ ] Run focused and full tests.

### Task 4: Documentation And Verification

- [ ] Update README and WORK_SUMMARY.
- [ ] Run `pytest -q`, `python -m compileall -q src`, and `git diff --check`.
- [ ] Commit verified changes.
