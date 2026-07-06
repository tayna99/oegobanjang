# Workforce RAG Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the workforce-agent RAG/Vector DB checklist by removing unsafe vector records, connecting runtime retrieval to Chroma, adding production embedding options, and expanding Evidence Events.

**Architecture:** Keep RAG as evidence/material retrieval only. Candidate/company state remains in CSV/DB and rules. Workforce runtime retrieves official/template materials from the two Chroma collections, then produces deterministic readiness outputs that require human approval.

**Tech Stack:** FastAPI backend modules, local Chroma, deterministic offline embedding with optional OpenAI embeddings, pytest, JSONL raw/processed data pipeline.

---

### Task 1: Remove Unsafe Records From Workforce Vector Collections

**Files:**
- Modify: `scripts/ingest_rag_docs.py`
- Test: `backend/tests/test_workforce_vector_index.py`

- [x] Add a failing test proving `doc_type=case` and `evidence_grade=D/F` are excluded from `workforce_official` and `workforce_templates`.
- [x] Update `build_workforce_collection_records` to include only `A/B` official records and `E` internal template/checklist records.
- [x] Regenerate processed chunks and Chroma records.

### Task 2: Connect Runtime Workforce Agent To Chroma Retrieval

**Files:**
- Modify: `scripts/index_workforce_chroma.py`
- Modify: `backend/app/agent_runtime/agents/hiring_agent.py`
- Test: `backend/tests/test_hiring_readiness_result.py`

- [x] Add tests proving `run_hiring_agent` includes retrieved official/template materials in output citations.
- [x] Add a small runtime retrieval adapter around `query_workforce_collection`.
- [x] Log `rag_retrieved`, `approval_requested`, and `final_response_generated`.

### Task 3: Add Optional OpenAI Embedding Mode

**Files:**
- Modify: `scripts/index_workforce_chroma.py`
- Test: `backend/tests/test_workforce_vector_index.py`

- [x] Add tests proving default embedding mode is deterministic.
- [x] Add `--embedding-provider deterministic|openai` and `--embedding-model`.
- [x] Require `OPENAI_API_KEY` only when `--embedding-provider openai`.

### Task 4: Preserve Work24 Fallback Boundary

**Files:**
- Modify: `docs/RAG_STRATEGY.md`

- [x] Document that Work24 uses the exact detail URL plus manifest fallback because server-side fetch returns a rendered shell.
- [x] Keep browser-rendered extraction as follow-up, not as default unsafe crawler behavior.

### Task 5: Verify

- [x] Run focused workforce RAG tests.
- [x] Run ingest with retrieval gate.
- [x] Rebuild local Chroma collections.
- [x] Run all backend tests.
